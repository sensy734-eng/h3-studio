# -*- coding: utf-8 -*-
"""图片模型基准:NoobAI-XL(SDXL) + Krea-2-Turbo NVFP4 — 参数矩阵 + 遥测

用法:
    python img_bench.py
要求本机已运行 ComfyUI(http://127.0.0.1:8188)且已部署对应模型。
仓库布局: 仓库根/benchmark/img/  +  仓库根/ComfyUI/ComfyUI-master/
可用环境变量 COMFY_ROOT 覆盖 ComfyUI 源码目录。
"""
import json, os, subprocess, sys, time, threading, csv
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'

def _find_repo_root(start):
    """从脚本位置向上找包含 benchmark/ + scripts/ 的仓库根目录"""
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
RESULT = os.path.join(BENCH, 'results.json')
results = json.load(open(RESULT, encoding='utf-8')) if os.path.exists(RESULT) else []

PROMPT = 'A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, gentle breeze, shallow depth of field, filmic 35mm look, highly detailed.'
SRC = 'clothes_ref.png'

def post(p, d):
    import urllib.request
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    import urllib.request
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def build_noobai(w, h, steps, cfg, seed, prefix, denoise=None, sampler='euler_ancestral', sched='karras'):
    n = {
     '1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'NoobAI-XL-v1.0.safetensors'}},
     '4':{'class_type':'CLIPTextEncode','inputs':{'text':PROMPT,'clip':['1',1]}},
     '6':{'class_type':'EmptyLatentImage','inputs':{'width':w,'height':h,'batch_size':1}},
     '7':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':cfg,'sampler_name':sampler,'scheduler':sched,'denoise':denoise or 1.0,'model':['1',0],'positive':['4',0],'negative':['5',0],'latent_image':['6',0]}},
     '8':{'class_type':'VAEDecode','inputs':{'samples':['7',0],'vae':['1',2]}},
     '9':{'class_type':'SaveImage','inputs':{'images':['8',0],'filename_prefix':prefix}},
    }
    # 空负面提示词
    n['5'] = {'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['1',1]}}
    if denoise is not None:
        n['13'] = {'class_type':'LoadImage','inputs':{'image':SRC}}
        n['6'] = {'class_type':'VAEEncode','inputs':{'pixels':['13',0],'vae':['1',2]}}
        n['7']['inputs']['latent_image'] = ['6',0]
    return n

def build_krea(w, h, steps, cfg, seed, prefix, denoise=None, sampler='er_sde', sched='simple', lora=0):
    n = {
     '1':{'class_type':'UNETLoader','inputs':{'unet_name':'krea2_turbo_nvfp4.safetensors','weight_dtype':'default'}},
     '2':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_4b_fp8_scaled.safetensors','type':'krea2','device':'default'}},
     '3':{'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
     '4':{'class_type':'CLIPTextEncode','inputs':{'text':PROMPT,'clip':['2',0]}},
     '5':{'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['2',0]}},
     '6':{'class_type':'EmptyLatentImage','inputs':{'width':w,'height':h,'batch_size':1}},
     '7':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':cfg,'sampler_name':sampler,'scheduler':sched,'denoise':denoise or 1.0,'model':['1',0],'positive':['4',0],'negative':['5',0],'latent_image':['6',0]}},
     '8':{'class_type':'VAEDecode','inputs':{'samples':['7',0],'vae':['3',0]}},
     '9':{'class_type':'SaveImage','inputs':{'images':['8',0],'filename_prefix':prefix}},
    }
    if lora > 0:
        n['10'] = {'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'krea2_style_reference.safetensors','strength_model':lora,'model':['1',0]}}
        n['7']['inputs']['model'] = ['10',0]
    if denoise is not None:
        n['13'] = {'class_type':'LoadImage','inputs':{'image':SRC}}
        n['6'] = {'class_type':'VAEEncode','inputs':{'pixels':['13',0],'vae':['3',0]}}
        n['7']['inputs']['latent_image'] = ['6',0]
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
        p=[r['power'] for r in self.rows if 'power' in r]; t=[r['temp'] for r in self.rows if 'temp' in r]
        return {'gpu_mean':round(sum(g)/len(g),1) if g else None,'gpu_max':max(g) if g else None,
                'vram_max':max(v) if v else None,'power_mean':round(sum(p)/len(p),1) if p else None,
                'temp_max':max(t) if t else None,'samples':len(self.rows)}

def run(key, nodes, src_for_sim=None):
    if any(r.get('key')==key and not r.get('error') for r in results): print(f'[skip] {key}'); return
    tel = Tel(); th = threading.Thread(target=tel.run, daemon=True); th.start()
    t0 = time.time()
    try:
        resp = post('/prompt', {'prompt':nodes,'client_id':'img-'+key})
        if resp.get('node_errors'):
            raise RuntimeError(json.dumps(resp['node_errors'])[:400])
        pid = resp['prompt_id']
        fname = None
        for _ in range(150):
            time.sleep(2)
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
        import numpy as np
        from PIL import Image
        im = Image.open(out_path)
        a = np.asarray(im.convert('L').resize((200,120)), dtype=np.float32)
        q = {'size_kb': round(os.path.getsize(out_path)/1024,1), 'w': im.width, 'h': im.height,
             'lum_mean': round(float(a.mean()),1), 'lum_std': round(float(a.std()),1)}
        if src_for_sim:
            s = np.asarray(Image.open(src_for_sim).convert('RGB').resize((200,120)), np.float32)
            o = np.asarray(im.convert('RGB').resize((200,120)), np.float32)
            mse = float(np.mean((s-o)**2))
            q['sim_psnr'] = round(10*np.log10(255**2/(mse+1e-9)),2)
        rec = {'key':key,'wall_s':wall,'telemetry':tel.stats(),'quality':q,'output':fname}
        results.append(rec)
        tmp = RESULT+'.tmp'; json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, RESULT)
        with open(os.path.join(BENCH,'telemetry',key+'.csv'),'w',newline='',encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(tel.rows[0].keys()) if tel.rows else ['t']); w.writeheader(); w.writerows(tel.rows)
        print(f'[done] {key}: {wall}s vram={rec["telemetry"].get("vram_max")}MB gpu={rec["telemetry"].get("gpu_mean")}% sim={q.get("sim_psnr")} {q["w"]}x{q["h"]} {q["size_kb"]}KB')
    except Exception as e:
        tel.stop.set(); th.join(timeout=8)
        print(f'[FAIL] {key}: {e}')
        results.append({'key':key,'error':str(e)})
        tmp = RESULT+'.tmp'; json.dump(results, open(tmp,'w',encoding='utf-8'), ensure_ascii=False, indent=1); os.replace(tmp, RESULT)

SRC_PATH = os.path.join(COMFY_ROOT, 'input', SRC)
# NoobAI-XL(SDXL)
run('NOOBAI_1024_s20_cfg5', build_noobai(1024,1024,20,5,51001,'IMG_NB_s20'))
run('NOOBAI_1024_s30_cfg5', build_noobai(1024,1024,30,5,51002,'IMG_NB_s30'))
run('NOOBAI_1024_s20_cfg7', build_noobai(1024,1024,20,7,51003,'IMG_NB_cfg7'))
run('NOOBAI_832x1216_s25', build_noobai(832,1216,25,5,51004,'IMG_NB_vert'))
run('NOOBAI_I2I_s20_dn075', build_noobai(1024,1024,20,5,51005,'IMG_NB_i2i', denoise=0.75), SRC_PATH)
# Krea-2 Turbo NVFP4
run('KREA_1024_s8_cfg1', build_krea(1024,1024,8,1,52001,'IMG_KR_s8'))
run('KREA_1024_s4_cfg1', build_krea(1024,1024,4,1,52002,'IMG_KR_s4'))
run('KREA_1024_s12_cfg1', build_krea(1024,1024,12,1,52003,'IMG_KR_s12'))
run('KREA_1024_s8_lora09', build_krea(1024,1024,8,1,52005,'IMG_KR_lora', lora=0.9))
run('KREA_I2I_s8_dn07', build_krea(1024,1024,8,1,52004,'IMG_KR_i2i', denoise=0.7), SRC_PATH)
print('=== 全部完成 ===')
