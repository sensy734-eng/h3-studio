# -*- coding: utf-8 -*-
"""Turbo LoRA 实测:5s·864×480 对比 turbo 4/6/8 步 vs 普通 8/20 步"""
import json, os, subprocess, sys, time, threading, csv, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'
BENCH = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(BENCH, 'turbo_results.json')
results = json.load(open(RESULT, encoding='utf-8')) if os.path.exists(RESULT) else []

PROMPT = ('A cinematic, realistic medium shot of a young woman in her late twenties with natural skin texture, '
          'sharp eyes and loose brown hair, standing in a sunlit city street at golden hour, gentle breeze moving her hair, '
          'she turns her head slowly toward the camera and smiles softly. Slow push-in camera, shallow depth of field, filmic 35mm look. '
          'Sound: soft street ambience, distant traffic, light wind, no music.')

def post(p, d):
    import urllib.request
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    import urllib.request
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def base_common(prefix):
    return {
     '1':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
     '2':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_audio_vae_fp32.safetensors'}},
     '3':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
     '4':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_fl2va_pruned_int8_convrot.safetensors','weight_dtype':'default'}},
     '6':{'class_type':'MiniMaxH3AudioConditioningT8','inputs':{'prompt':PROMPT,'width':864,'height':480,'length':124,'task_type':'T2VA','audio_mode':'native','audio_denoise_strength':1.0,'add_source_as_reference':False,'prompt_primary_audio_ordinal':0,'strict_prompt_tags':True,'ref_image_size':'match','reference_video_policy':'official_2_to_15s','clip':['3',0],'video_vae':['1',0],'audio_vae':['2',0]}},
     '11':{'class_type':'MiniMaxH3AVDecodeT8','inputs':{'av_latent':['10',0],'video_vae':['1',0],'audio_vae':['2',0]}},
     '12':{'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':prefix,'format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['11',0],'audio':['11',1]}},
    }

def build_std(steps, seed, prefix):
    """普通双时钟(工作台现行)"""
    n = base_common(prefix)
    n.update({
     '7':{'class_type':'MiniMaxH3DualClockSamplerT8','inputs':{'steps':steps,'shift_video':12.0,'shift_audio':3.0,'model':['4',0],'av_latent':['6',1]}},
     '8':{'class_type':'RandomNoise','inputs':{'noise_seed':seed}},
     '9':{'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['6',0]}},
     '10':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['8',0],'guider':['9',0],'sampler':['7',1],'sigmas':['7',2],'latent_image':['6',1]}},
    })
    return n

def build_turbo(steps, seed, prefix, low_vram=False):
    """官方 turbo 方案:TurboLoRA + TurboSampler + BasicScheduler(simple)"""
    n = base_common(prefix)
    n.update({
     '7':{'class_type':'MiniMaxH3TurboLoRA','inputs':{'model':['4',0],'lora_name':'minimax_h3_turbo_v4_step600_ema.safetensors','strength':1.0,'low_vram':low_vram}},
     '8':{'class_type':'RandomNoise','inputs':{'noise_seed':seed}},
     '9':{'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['6',0]}},
     '14':{'class_type':'MiniMaxH3TurboSampler','inputs':{}},
     '15':{'class_type':'BasicScheduler','inputs':{'model':['7',0],'scheduler':'simple','steps':steps,'denoise':1.0}},
     '10':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['8',0],'guider':['9',0],'sampler':['14',0],'sigmas':['15',0],'latent_image':['6',1]}},
    })
    return n

class Tel:
    def __init__(self):
        self.stop = threading.Event(); self.rows = []; self.t0 = time.time()
    def run(self):
        while not self.stop.is_set():
            row = {'t': round(time.time()-self.t0,1)}
            try:
                o = subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used,power.draw,temperature.gpu','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=5).stdout.strip().split(',')
                row['gpu']=float(o[0]); row['vram']=float(o[1]); row['power']=float(o[2]); row['temp']=float(o[3])
            except Exception: pass
            self.rows.append(row); self.stop.wait(1.0)
    def stats(self):
        g=[r['gpu'] for r in self.rows if 'gpu' in r]; v=[r['vram'] for r in self.rows if 'vram' in r]
        t=[r['temp'] for r in self.rows if 'temp' in r]
        return {'gpu_mean':round(sum(g)/len(g),1) if g else None,'vram_max':max(v) if v else None,
                'temp_max':max(t) if t else None,'samples':len(self.rows)}

def run(key, nodes):
    if any(r.get('key')==key for r in results): print(f'[skip] {key}'); return
    tel = Tel(); th = threading.Thread(target=tel.run, daemon=True); th.start()
    t0 = time.time()
    try:
        resp = post('/prompt', {'prompt':nodes,'client_id':'turbo-'+key})
        if resp.get('node_errors'):
            raise RuntimeError(json.dumps(resp['node_errors'])[:400])
        pid = resp['prompt_id']
        fname = None
        for _ in range(400):
            time.sleep(3)
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error':
                    msgs = [m for m in st.get('messages',[]) if m[0]=='execution_error']
                    raise RuntimeError(json.dumps(msgs)[:400])
                if st.get('completed'):
                    for o in h[pid]['outputs'].values():
                        for g in o.get('gifs',[]):
                            if str(g.get('format','')).startswith('video/'): fname = g['filename']
                    break
        tel.stop.set(); th.join(timeout=8)
        if not fname: raise RuntimeError('no video output')
        wall = round(time.time()-t0,1)
        rec = {'key':key,'wall_s':wall,'telemetry':tel.stats(),'output':fname}
        results.append(rec)
        tmp = RESULT+'.tmp'; json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, RESULT)
        print(f'[done] {key}: {wall}s vram={rec["telemetry"].get("vram_max")}MB gpu={rec["telemetry"].get("gpu_mean")}% temp={rec["telemetry"].get("temp_max")}')
    except Exception as e:
        tel.stop.set(); th.join(timeout=8)
        print(f'[FAIL] {key}: {e}')
        results.append({'key':key,'error':str(e)})
        tmp = RESULT+'.tmp'; json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, RESULT)

print('=== Turbo LoRA 实测(5s·864×480·124帧) ===')
run('STD_8steps',  build_std(8,  81001, 'TB_STD_s8'))
run('STD_20steps', build_std(20, 81002, 'TB_STD_s20'))
run('TURBO_4steps',  build_turbo(4,  81003, 'TB_T4'))
run('TURBO_6steps',  build_turbo(6,  81004, 'TB_T6'))
run('TURBO_8steps',  build_turbo(8,  81005, 'TB_T8'))
print('=== 全部完成 ===')
