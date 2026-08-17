# -*- coding: utf-8 -*-
"""页面工作流冒烟测试:模拟 h3-studio.html 的 buildStillNoobai/buildStillKrea 节点图
验证 T2I / I2I × NoobAI / Krea 四种组合均可成功出图(页面后端可用性证明)"""
import json, sys, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'
PROMPT = 'A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, shallow depth of field, filmic 35mm look.'
SRC = 'clothes_ref.png'

def post(p, d):
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def noobai(w, h, steps, cfg, seed, prefix, i2i=False, denoise=0.75):
    n = {
     '1':{'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'NoobAI-XL-v1.0.safetensors'}},
     '2':{'class_type':'CLIPTextEncode','inputs':{'text':PROMPT,'clip':['1',1]}},
     '3':{'class_type':'CLIPTextEncode','inputs':{'text':'worst quality, low quality, blurry, deformed, bad anatomy, watermark, text, jpeg artifacts','clip':['1',1]}},
     '4':{'class_type':'EmptyLatentImage','inputs':{'width':w,'height':h,'batch_size':1}},
     '5':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':cfg,'sampler_name':'euler_ancestral','scheduler':'karras','denoise':denoise if i2i else 1.0,'model':['1',0],'positive':['2',0],'negative':['3',0],'latent_image':['4',0]}},
     '6':{'class_type':'VAEDecode','inputs':{'samples':['5',0],'vae':['1',2]}},
     '7':{'class_type':'SaveImage','inputs':{'images':['6',0],'filename_prefix':prefix}},
    }
    if i2i:
        n['8'] = {'class_type':'LoadImage','inputs':{'image':SRC}}
        n['9'] = {'class_type':'VAEEncode','inputs':{'pixels':['8',0],'vae':['1',2]}}
        n['5']['inputs']['latent_image'] = ['9',0]
    return n

def krea(w, h, steps, seed, prefix, i2i=False, denoise=0.75, lora=0.9):
    n = {
     '1':{'class_type':'UNETLoader','inputs':{'unet_name':'krea2_turbo_nvfp4.safetensors','weight_dtype':'default'}},
     '2':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_4b_fp8_scaled.safetensors','type':'krea2','device':'default'}},
     '3':{'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
     '4':{'class_type':'CLIPTextEncode','inputs':{'text':PROMPT,'clip':['2',0]}},
     '5':{'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['2',0]}},
     '6':{'class_type':'EmptyLatentImage','inputs':{'width':w,'height':h,'batch_size':1}},
     '7':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':1.0,'sampler_name':'er_sde','scheduler':'simple','denoise':denoise if i2i else 1.0,'model':['1',0],'positive':['4',0],'negative':['5',0],'latent_image':['6',0]}},
     '8':{'class_type':'VAEDecode','inputs':{'samples':['7',0],'vae':['3',0]}},
     '9':{'class_type':'SaveImage','inputs':{'images':['8',0],'filename_prefix':prefix}},
    }
    if lora > 0:
        n['10'] = {'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'krea2_style_reference.safetensors','strength_model':lora,'model':['1',0]}}
        n['7']['inputs']['model'] = ['10',0]
    if i2i:
        n['11'] = {'class_type':'LoadImage','inputs':{'image':SRC}}
        n['12'] = {'class_type':'VAEEncode','inputs':{'pixels':['11',0],'vae':['3',0]}}
        n['7']['inputs']['latent_image'] = ['12',0]
    return n

def run(key, nodes):
    t0 = time.time()
    resp = post('/prompt', {'prompt':nodes,'client_id':'smoke-'+key})
    if resp.get('node_errors'):
        print(f'[FAIL] {key}: {json.dumps(resp["node_errors"])[:300]}'); return False
    pid = resp['prompt_id']
    for _ in range(120):
        time.sleep(2)
        try:
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error':
                    print(f'[FAIL] {key}: task error'); return False
                if st.get('completed'):
                    imgs = []
                    for o in h[pid]['outputs'].values():
                        for im in o.get('images',[]): imgs.append(im['filename'])
                    print(f'[OK]   {key}: {imgs} ({round(time.time()-t0)}s)')
                    return True
        except Exception: pass
    print(f'[FAIL] {key}: timeout'); return False

ok = True
ok &= run('NOOBAI_T2I_s8', noobai(1024,1024,8,5,71001,'Smoke_NB_T2I'))
ok &= run('NOOBAI_I2I_s8', noobai(1024,1024,8,5,71002,'Smoke_NB_I2I', i2i=True))
ok &= run('KREA_T2I_s8', krea(1024,1024,8,72001,'Smoke_KR_T2I'))
ok &= run('KREA_I2I_s8', krea(1024,1024,8,72002,'Smoke_KR_I2I', i2i=True))
print('=== 冒烟测试', '全部通过' if ok else '存在失败', '===')
