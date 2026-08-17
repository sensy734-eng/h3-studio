# -*- coding: utf-8 -*-
"""H3 Studio 基准测试驱动:4 模式 x 3 时长 + 步数对照,带性能遥测与质量检测

用法: python bench_driver.py(需 ComfyUI 已运行于 http://127.0.0.1:8188)
仓库布局: 仓库根/benchmark/  +  仓库根/ComfyUI/ComfyUI-master/
可用环境变量 COMFY_ROOT 覆盖 ComfyUI 源码目录。
"""
import json, os, subprocess, sys, time, threading, csv, io

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'http://127.0.0.1:8188'

def _find_repo_root(start):
    d = os.path.dirname(os.path.abspath(start))
    for _ in range(4):
        if os.path.isdir(os.path.join(d, 'benchmark')) and os.path.isdir(os.path.join(d, 'scripts')):
            return d
        d = os.path.dirname(d)
    return d

REPO_ROOT = _find_repo_root(__file__)
COMFY_ROOT = os.environ.get('COMFY_ROOT') or os.path.join(REPO_ROOT, 'ComfyUI', 'ComfyUI-master')
BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(COMFY_ROOT, 'output')
LOG = os.path.join(REPO_ROOT, 'comfyui.log')
os.makedirs(BENCH_DIR, exist_ok=True)
os.makedirs(os.path.join(BENCH_DIR, 'telemetry'), exist_ok=True)
os.makedirs(os.path.join(BENCH_DIR, 'frames'), exist_ok=True)

RESULT_FILE = os.path.join(BENCH_DIR, 'results.json')
results = []
if os.path.exists(RESULT_FILE):
    results = json.load(open(RESULT_FILE, encoding='utf-8'))

FIRST_IMG = 'i2v_first_frame.png'
LAST_IMG = 'test_last_frame.png'
PROMPT_T2V = ("A cinematic, realistic medium shot of a young woman in her late twenties with natural skin texture, "
    "sharp eyes and loose brown hair, standing in a sunlit city street at golden hour, gentle breeze moving her hair, "
    "she turns her head slowly toward the camera and smiles softly. Slow push-in camera, shallow depth of field, filmic 35mm look. "
    "Sound: soft street ambience, distant traffic, light wind, no music.")
PROMPT_REF = ("Keep the person's appearance and clothing exactly as in <Picture 1>. She turns her head slowly toward the camera, "
    "hair moving in the breeze, a soft smile forming, slow push-in, shallow depth of field, filmic 35mm. "
    "Sound: soft street ambience, light wind, no music.")

def api_post(path, payload):
    import urllib.request
    body = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def api_get(path):
    import urllib.request
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read())

def build_prompt(mode, length, steps, seed, prefix):
    w, h = 864, 480
    prompt = PROMPT_REF if mode in ('I2VA', 'FL2VA', 'Ref2VA') else PROMPT_T2V
    unet = ('minimax_h3_ref2va_pruned_int8_convrot.safetensors' if mode == 'Ref2VA'
            else 'minimax_h3_fl2va_pruned_int8_convrot.safetensors')
    nodes = {
        '1':  {'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
        '2':  {'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_audio_vae_fp32.safetensors'}},
        '3':  {'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
        '4':  {'class_type':'UNETLoader','inputs':{'unet_name':unet,'weight_dtype':'default'}},
        '6':  {'class_type':'MiniMaxH3AudioConditioningT8','inputs':{'prompt':prompt,'width':w,'height':h,'length':length,
                'task_type':mode,'audio_mode':'native','audio_denoise_strength':1.0,'add_source_as_reference':False,
                'prompt_primary_audio_ordinal':0,'strict_prompt_tags':True,'ref_image_size':'match',
                'reference_video_policy':'official_2_to_15s','clip':['3',0],'video_vae':['1',0],'audio_vae':['2',0]}},
        '7':  {'class_type':'MiniMaxH3DualClockSamplerT8','inputs':{'steps':steps,'shift_video':12.0,'shift_audio':3.0,'model':['4',0],'av_latent':['6',1]}},
        '8':  {'class_type':'RandomNoise','inputs':{'noise_seed':seed}},
        '9':  {'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['6',0]}},
        '10': {'class_type':'SamplerCustomAdvanced','inputs':{'noise':['8',0],'guider':['9',0],'sampler':['7',1],'sigmas':['7',2],'latent_image':['6',1]}},
        '11': {'class_type':'MiniMaxH3AVDecodeT8','inputs':{'av_latent':['10',0],'video_vae':['1',0],'audio_vae':['2',0]}},
        '12': {'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':prefix,'format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['11',0],'audio':['11',1]}}
    }
    if mode == 'I2VA':
        nodes['13'] = {'class_type':'LoadImage','inputs':{'image':FIRST_IMG}}
        nodes['6']['inputs']['first_frame'] = ['13',0]
    elif mode == 'FL2VA':
        nodes['13'] = {'class_type':'LoadImage','inputs':{'image':FIRST_IMG}}
        nodes['14'] = {'class_type':'LoadImage','inputs':{'image':LAST_IMG}}
        nodes['6']['inputs']['first_frame'] = ['13',0]
        nodes['6']['inputs']['last_frame'] = ['14',0]
    elif mode == 'Ref2VA':
        nodes['13'] = {'class_type':'LoadImage','inputs':{'image':FIRST_IMG}}
        nodes['6']['inputs']['ref_images.ref_image_0'] = ['13',0]
    return nodes

class Telemetry:
    def __init__(self, comfy_pid):
        self.comfy_pid = comfy_pid
        self.stop = threading.Event()
        self.rows = []
        self.t0 = time.time()
    def run(self):
        while not self.stop.is_set():
            row = {'t': round(time.time() - self.t0, 1)}
            try:
                out = subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu',
                                      '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
                parts = out.stdout.strip().split(',')
                row['gpu_util'] = float(parts[0].strip()); row['vram_mb'] = float(parts[1].strip())
                row['power_w'] = float(parts[2].strip()); row['temp_c'] = float(parts[3].strip())
            except Exception:
                row['gpu_util'] = row['vram_mb'] = row['power_w'] = row['temp_c'] = None
            try:
                import psutil
                p = psutil.Process(self.comfy_pid)
                row['ram_mb'] = round(p.memory_info().rss / 1048576, 1)
                row['sys_ram_used_pct'] = round(psutil.virtual_memory().percent, 1)
            except Exception:
                row['ram_mb'] = row['sys_ram_used_pct'] = None
            self.rows.append(row)
            self.stop.wait(1.0)
    def stats(self):
        if not self.rows: return {}
        g = [r['gpu_util'] for r in self.rows if r.get('gpu_util') is not None]
        v = [r['vram_mb'] for r in self.rows if r.get('vram_mb') is not None]
        p = [r['power_w'] for r in self.rows if r.get('power_w') is not None]
        t = [r['temp_c'] for r in self.rows if r.get('temp_c') is not None]
        ram = [r['ram_mb'] for r in self.rows if r.get('ram_mb') is not None]
        return {
            'gpu_util_mean': round(sum(g)/len(g),1) if g else None,
            'gpu_util_max': max(g) if g else None,
            'vram_max_mb': max(v) if v else None,
            'vram_mean_mb': round(sum(v)/len(v),1) if v else None,
            'power_max_w': max(p) if p else None,
            'power_mean_w': round(sum(p)/len(p),1) if p else None,
            'temp_max_c': max(t) if t else None,
            'ram_max_mb': max(ram) if ram else None,
            'samples': len(self.rows),
        }

def find_comfy_pid():
    import psutil
    for p in psutil.process_iter(['pid','cmdline']):
        try:
            cl = ' '.join(p.info['cmdline'] or [])
            if 'main.py' in cl and 'ComfyUI' in cl:
                return p.info['pid']
        except Exception: pass
    return None

def ffprobe(path, sel):
    r = subprocess.run(['ffprobe','-v','error','-select_streams',sel,'-show_entries',
        'stream=codec_name,width,height,r_frame_rate,sample_rate,channels','-show_entries','format=duration,size,bit_rate',
        '-of','json',path], capture_output=True, text=True)
    try: return json.loads(r.stdout)
    except Exception: return {}

def frame_stats(frames_dir, video, prefix):
    """抽 3 帧算亮度/运动(PSNR),返回 dict"""
    out = {}
    for tag, ts in (('f0', 0.2), ('f1', None), ('f2', 5.0)):
        pass
    return out

def run_bench(run):
    key = f"{run['mode']}_{run['len']}f_{run['steps']}step"
    prefix = f"Bench_{run['mode']}_{run['len']}f_{run['steps']}s"
    # 已完成的跳过
    if any(r.get('key') == key for r in results):
        print(f"[skip] {key} 已存在"); return
    print(f"[run] {key} 开始 {time.strftime('%H:%M:%S')}")
    t_wall0 = time.time()
    # 遥测
    pid = find_comfy_pid()
    tel = Telemetry(pid)
    th = threading.Thread(target=tel.run, daemon=True); th.start()
    try:
        prompt = build_prompt(run['mode'], run['len'], run['steps'], 20260815, prefix)
        resp = api_post('/prompt', {'prompt': prompt, 'client_id': 'bench-' + key})
        if resp.get('node_errors'):
            raise RuntimeError('节点错误: ' + json.dumps(resp['node_errors'])[:300])
        pid2 = resp['prompt_id']
        # 轮询完成
        for _ in range(900):
            try:
                h = api_get('/history/' + pid2)
                if pid2 in h:
                    st = h[pid2]['status']
                    if st.get('status_str') == 'error':
                        raise RuntimeError('任务错误: ' + json.dumps(st.get('messages', []))[:300])
                    if st.get('completed'):
                        break
            except Exception:
                pass
            time.sleep(3)
        tel.stop.set(); th.join(timeout=10)
        wall = round(time.time() - t_wall0, 1)
        # 服务端耗时
        server_time = None
        try:
            tail = subprocess.run(['powershell','-Command',
                f"Select-String -Path '{LOG}' -Pattern 'Prompt executed' | Select-Object -Last 1"], capture_output=True, text=True, timeout=20)
            import re
            m = re.search(r'([\d.]+) seconds', tail.stdout)
            if m: server_time = float(m.group(1))
        except Exception: pass
        # 找输出文件
        outfile = None
        for f in os.listdir(OUT_DIR):
            if f.startswith(prefix + '_') and f.endswith('.mp4'):
                outfile = os.path.join(OUT_DIR, f)
        if not outfile:
            raise RuntimeError('未找到输出文件 prefix=' + prefix)
        # 质量检测
        q = {}
        fp = ffprobe(outfile, 'v:0')
        fa = ffprobe(outfile, 'a:0')
        fmt = fp.get('format', {})
        vs = (fp.get('streams') or [{}])[0]
        as_ = (fa.get('streams') or [{}])[0]
        q['size_kb'] = round(os.path.getsize(outfile)/1024, 1)
        q['duration'] = round(float(fmt.get('duration', 0)), 3)
        q['bitrate_kbps'] = round(int(fmt.get('bit_rate', 0))/1000, 1)
        q['video_codec'] = vs.get('codec_name'); q['width'] = vs.get('width'); q['height'] = vs.get('height')
        q['fps'] = vs.get('r_frame_rate')
        q['audio_codec'] = as_.get('codec_name'); q['audio_sr'] = as_.get('sample_rate'); q['audio_ch'] = as_.get('channels')
        # 响度
        vd = subprocess.run(['ffmpeg','-i',outfile,'-af','volumedetect','-f','null','NUL'], capture_output=True, text=True)
        import re
        mm = re.search(r'mean_volume: ([\-\d.]+) dB', vd.stderr)
        mx = re.search(r'max_volume: ([\-\d.]+) dB', vd.stderr)
        q['audio_mean_db'] = float(mm.group(1)) if mm else None
        q['audio_max_db'] = float(mx.group(1)) if mx else None
        # 帧统计:亮度均值/标准差 + 首尾 PSNR(运动量)
        fdir = os.path.join(BENCH_DIR, 'frames', key)
        os.makedirs(fdir, exist_ok=True)
        subprocess.run(['ffmpeg','-y','-v','error','-ss','0.2','-i',outfile,'-frames:v','1',os.path.join(fdir,'f0.png')])
        subprocess.run(['ffmpeg','-y','-v','error','-ss',str(max(0.0, float(fmt.get('duration',5))-0.3)),'-i',outfile,'-frames:v','1',os.path.join(fdir,'f1.png')])
        import PIL.Image
        from PIL import Image as PImage
        import numpy as np
        def lum(p):
            im = PImage.open(p).convert('L').resize((216,120))
            a = np.asarray(im, dtype=np.float32)
            return round(float(a.mean()),1), round(float(a.std()),1)
        q['lum0'], q['std0'] = lum(os.path.join(fdir,'f0.png'))
        q['lum1'], q['std1'] = lum(os.path.join(fdir,'f1.png'))
        ps = subprocess.run(['ffmpeg','-v','info','-i',os.path.join(fdir,'f0.png'),'-i',os.path.join(fdir,'f1.png'),
                             '-lavfi','psnr','-f','null','-'], capture_output=True, text=True)
        pm = re.search(r'average:([\d.]+)', ps.stderr)
        q['motion_psnr'] = float(pm.group(1)) if pm else None
        rec = {'key': key, 'mode': run['mode'], 'len': run['len'], 'steps': run['steps'],
               'wall_s': wall, 'server_s': server_time, 'telemetry': tel.stats(), 'quality': q, 'output': outfile}
        results.append(rec)
        json.dump(results, open(RESULT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        with open(os.path.join(BENCH_DIR, 'telemetry', key + '.csv'), 'w', newline='', encoding='utf-8') as cf:
            w = csv.DictWriter(cf, fieldnames=list(tel.rows[0].keys()) if tel.rows else ['t'])
            w.writeheader(); w.writerows(tel.rows)
        print(f"[done] {key} wall={wall}s server={server_time}s vram_max={rec['telemetry'].get('vram_max_mb')}MB "
              f"gpu_max={rec['telemetry'].get('gpu_util_max')}% size={q['size_kb']}KB psnr={q.get('motion_psnr')}")
    except Exception as e:
        tel.stop.set(); th.join(timeout=10)
        print(f"[FAIL] {key}: {e}")
        results.append({'key': key, 'mode': run['mode'], 'len': run['len'], 'steps': run['steps'], 'error': str(e)})
        json.dump(results, open(RESULT_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

MATRIX = []
for mode in ('T2VA', 'I2VA', 'FL2VA', 'Ref2VA'):
    for ln in (124, 243, 362):
        MATRIX.append({'mode': mode, 'len': ln, 'steps': 8})
MATRIX.append({'mode': 'T2VA', 'len': 124, 'steps': 20})
MATRIX.append({'mode': 'T2VA', 'len': 362, 'steps': 20})

print('=== 基准矩阵:', len(MATRIX), '轮 ===')
for r in MATRIX:
    run_bench(r)
print('=== 全部完成 ===')
