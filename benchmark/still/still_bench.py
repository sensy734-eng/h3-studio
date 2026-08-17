# -*- coding: utf-8 -*-
"""H3 Still(文生图/图生图)参数矩阵基准:帧数档位 x 步数 x 参考强度 + 遥测

用法: python still_bench.py(需 ComfyUI 已运行于 http://127.0.0.1:8188)
仓库布局: 仓库根/benchmark/still/  +  仓库根/ComfyUI/ComfyUI-master/
可用环境变量 COMFY_ROOT 覆盖 ComfyUI 源码目录。
"""
import json, os, subprocess, sys, time, threading, csv, re
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
BENCH = os.path.dirname(os.path.abspath(__file__))
os.makedirs(BENCH, exist_ok=True)
os.makedirs(os.path.join(BENCH, 'telemetry'), exist_ok=True)
os.makedirs(os.path.join(BENCH, 'out'), exist_ok=True)
RESULT = os.path.join(BENCH, 'results.json')
results = json.load(open(RESULT, encoding='utf-8')) if os.path.exists(RESULT) else []

SRC = 'clothes_ref.png'
PROMPT_T2I = 'A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, gentle breeze, shallow depth of field, filmic 35mm look, highly detailed.'
PROMPT_I2I = 'Convert the scene of <Picture 1> into a cyberpunk night city: neon purple and cyan lights, wet street with colorful reflections, futuristic signs. Keep the woman face, hairstyle, pose and clothing exactly as in <Picture 1>. Cinematic, highly detailed.'

def post(p, d):
    import urllib.request
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    import urllib.request
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def build_t2i(prompt, length, steps, seed, prefix, w, h):
    return {
     '1':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
     '2':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_audio_vae_fp32.safetensors'}},
     '3':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
     '4':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_fl2va_pruned_int8_convrot.safetensors','weight_dtype':'default'}},
     '6':{'class_type':'MiniMaxH3AudioConditioningT8','inputs':{'prompt':prompt,'width':w,'height':h,'length':length,'task_type':'T2VA','audio_mode':'native','audio_denoise_strength':1.0,'add_source_as_reference':False,'prompt_primary_audio_ordinal':0,'strict_prompt_tags':True,'ref_image_size':'match','reference_video_policy':'official_2_to_15s','clip':['3',0],'video_vae':['1',0],'audio_vae':['2',0]}},
     '7':{'class_type':'MiniMaxH3DualClockSamplerT8','inputs':{'steps':steps,'shift_video':12.0,'shift_audio':3.0,'model':['4',0],'av_latent':['6',1]}},
     '8':{'class_type':'RandomNoise','inputs':{'noise_seed':seed}},
     '9':{'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['6',0]}},
     '10':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['8',0],'guider':['9',0],'sampler':['7',1],'sigmas':['7',2],'latent_image':['6',1]}},
     '19':{'class_type':'MiniMaxH3StillDecodeT8','inputs':{'av_latent':['10',0],'video_vae':['1',0],'frame_selection':'first','frame_index':0}},
     '20':{'class_type':'SaveImage','inputs':{'images':['19',0],'filename_prefix':prefix}},
    }

def build_i2i(prompt, target_mode, steps, seed, prefix, strength, canvas_w=None, canvas_h=None):
    n = {
     '1':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
     '3':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
     '4':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_ref2va_pruned_int8_convrot.safetensors','weight_dtype':'default'}},
     '13':{'class_type':'LoadImage','inputs':{'image':SRC}},
     '14':{'class_type':'MiniMaxH3StillConditioningT8','inputs':{'prompt':prompt,'canvas_mode':'from_edit_image','width':canvas_w or 1344,'height':canvas_h or 768,'target_mode':target_mode,'reference_strength':strength,'audio_target':'generate_and_discard','strict_prompt_tags':True,'ref_image_size':'match','clip':['3',0],'video_vae':['1',0],'edit_image':['13',0]}},
     '15':{'class_type':'RandomNoise','inputs':{'noise_seed':seed}},
     '16':{'class_type':'BasicGuider','inputs':{'model':['4',0],'conditioning':['14',0]}},
     '17':{'class_type':'MiniMaxH3DualClockSamplerT8','inputs':{'steps':steps,'shift_video':12.0,'shift_audio':3.0,'model':['4',0],'av_latent':['14',1]}},
     '18':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['15',0],'guider':['16',0],'sampler':['17',1],'sigmas':['17',2],'latent_image':['14',1]}},
     '19':{'class_type':'MiniMaxH3StillDecodeT8','inputs':{'av_latent':['18',0],'video_vae':['1',0],'frame_selection':'first','frame_index':0}},
     '20':{'class_type':'SaveImage','inputs':{'images':['19',0],'filename_prefix':prefix}},
    }
    return n

class Tel:
    def __init__(self):
        self.stop = threading.Event(); self.rows = []; self.t0 = time.time()
    def run(self):
        import psutil
        while not self.stop.is_set():
            row = {'t': round(time.time()-self.t0,1)}
            try:
                o = subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5).stdout.strip().split(',')
                row['gpu']=float(o[0]); row['vram']=float(o[1]); row['power']=float(o[2]); row['temp']=float(o[3])
            except Exception: pass
            try:
                for p in psutil.process_iter(['pid','cmdline']):
                    if 'main.py' in ' '.join(p.info['cmdline'] or []):
                        row['ram'] = round(p.memory_info().rss/1048576,1); break
            except Exception: pass
            self.rows.append(row); self.stop.wait(1.0)
    def stats(self):
        g=[r['gpu'] for r in self.rows if 'gpu' in r]; v=[r['vram'] for r in self.rows if 'vram' in r]
        p=[r['power'] for r in self.rows if 'power' in r]; t=[r['temp'] for r in self.rows if 'temp' in r]
        m=[r['ram'] for r in self.rows if 'ram' in r]
        return {'gpu_mean':round(sum(g)/len(g),1) if g else None,'gpu_max':max(g) if g else None,
                'vram_max':max(v) if v else None,'power_mean':round(sum(p)/len(p),1) if p else None,
                'temp_max':max(t) if t else None,'ram_max':max(m) if m else None,'samples':len(self.rows)}

def run(key, nodes, src_for_sim=None):
    if any(r.get('key')==key for r in results): print(f'[skip] {key}'); return
    tel = Tel(); th = threading.Thread(target=tel.run, daemon=True); th.start()
    t0 = time.time()
    try:
        resp = post('/prompt', {'prompt':nodes,'client_id':'still-'+key})
        if resp.get('node_errors'):
            raise RuntimeError(json.dumps(resp['node_errors'])[:300])
        pid = resp['prompt_id']
        fname = None
        for _ in range(200):
            time.sleep(3)
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error': raise RuntimeError('task error')
                if st.get('completed'):
                    for o in h[pid]['outputs'].values():
                        for im in o.get('images',[]): fname = im['filename']
                    break
        tel.stop.set(); th.join(timeout=8)
        if not fname: raise RuntimeError('no image output')
        wall = round(time.time()-t0,1)
        out_path = os.path.join(COMFY_ROOT, 'output', fname)
        q = {'size_kb': round(os.path.getsize(out_path)/1024,1)}
        # 亮度统计
        import numpy as np
        from PIL import Image
        a = np.asarray(Image.open(out_path).convert('L').resize((200,120)), dtype=np.float32)
        q['lum_mean'] = round(float(a.mean()),1); q['lum_std'] = round(float(a.std()),1)
        q['w'] = Image.open(out_path).width; q['h'] = Image.open(out_path).height
        # 图生图相似度(与源图比,统一缩放)
        if src_for_sim:
            s = Image.open(src_for_sim).convert('RGB').resize((200,120))
            o = Image.open(out_path).convert('RGB').resize((200,120))
            sn = np.asarray(s, np.float32); on = np.asarray(o, np.float32)
            mse = float(np.mean((sn-on)**2))
            q['sim_psnr'] = round(10*np.log10(255**2/(mse+1e-9)),2)
            q['sim_mse'] = round(mse,1)
        rec = {'key':key,'wall_s':wall,'telemetry':tel.stats(),'quality':q,'output':fname}
        results.append(rec)
        tmp = RESULT + '.tmp'
        json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(tmp, RESULT)
        with open(os.path.join(BENCH,'telemetry',key+'.csv'),'w',newline='',encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(tel.rows[0].keys()) if tel.rows else ['t']); w.writeheader(); w.writerows(tel.rows)
        print(f'[done] {key}: {wall}s vram={rec["telemetry"].get("vram_max")}MB sim={q.get("sim_psnr")} size={q["size_kb"]}KB')
    except Exception as e:
        tel.stop.set(); th.join(timeout=8)
        print(f'[FAIL] {key}: {e}')
        results.append({'key':key,'error':str(e)})
        tmp = RESULT + '.tmp'
        json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        os.replace(tmp, RESULT)

SRC_PATH = os.path.join(COMFY_ROOT, 'input', SRC)
# T2I 矩阵
run('T2I_22f_s8_1024', build_t2i(PROMPT_T2I, 22, 8, 41001, 'ST_T2I_22s8', 1024, 1024))
run('T2I_22f_s20_1024', build_t2i(PROMPT_T2I, 22, 20, 41002, 'ST_T2I_22s20', 1024, 1024))
run('T2I_5f_s8_1024', build_t2i(PROMPT_T2I, 5, 8, 41003, 'ST_T2I_5s8', 1024, 1024))
run('T2I_124f_s8_1024', build_t2i(PROMPT_T2I, 124, 8, 41004, 'ST_T2I_124s8', 1024, 1024))
# I2I 矩阵
run('I2I_1f_s8_str099', build_i2i(PROMPT_I2I, 'direct_1_frame', 8, 42001, 'ST_I2I_1f', 0.99), SRC_PATH)
run('I2I_22f_s8_str099', build_i2i(PROMPT_I2I, 'short_video_22_frames', 8, 42002, 'ST_I2I_22f099', 0.99), SRC_PATH)
run('I2I_22f_s8_str090', build_i2i(PROMPT_I2I, 'short_video_22_frames', 8, 42003, 'ST_I2I_22f090', 0.90), SRC_PATH)
run('I2I_22f_s8_str080', build_i2i(PROMPT_I2I, 'short_video_22_frames', 8, 42004, 'ST_I2I_22f080', 0.80), SRC_PATH)
run('I2I_22f_s20_str095', build_i2i(PROMPT_I2I, 'short_video_22_frames', 20, 42005, 'ST_I2I_22f20', 0.95), SRC_PATH)
print('=== 全部完成 ===')
