# -*- coding: utf-8 -*-
"""Qwen-Image-Edit 2511 GGUF 接入探测:I2I + T2I 最小工作流验证"""
import json, sys, time, urllib.request
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'
SRC = 'clothes_ref.png'

def post(p, d):
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
def get(p):
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def base_nodes(with_lora=True, lora_strength=0.8):
    n = {
     '1':{'class_type':'UnetLoaderGGUF','inputs':{'unet_name':'qwen-image-edit-2511-Q4_K_M.gguf','weight_dtype':'default'}},
     '2':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen_2.5_vl_7b_fp8_scaled.safetensors','type':'qwen_image','device':'default'}},
     '3':{'class_type':'VAELoader','inputs':{'vae_name':'qwen_image_vae.safetensors'}},
     '5':{'class_type':'ModelSamplingAuraFlow','inputs':{'model':['1',0],'shift':3.1}},
     '6':{'class_type':'CFGNorm','inputs':{'model':['5',0],'strength':1.0}},
    }
    if with_lora:
        n['4'] = {'class_type':'LoraLoaderModelOnly','inputs':{'lora_name':'Qwen-Image-Lightning-8steps-V1.1-bf16.safetensors','strength_model':lora_strength,'model':['1',0]}}
        n['5']['inputs']['model'] = ['4',0]
    return n

def build_i2i(prompt, seed, steps=8, cfg=1.0, denoise=0.8, with_lora=True):
    n = base_nodes(with_lora)
    n.update({
     '7':{'class_type':'TextEncodeQwenImageEditPlus','inputs':{'clip':['2',0],'prompt':prompt,'vae':['3',0],'image1':['8',0]}},
     '8':{'class_type':'LoadImage','inputs':{'image':SRC}},
     '9':{'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['2',0]}},
     '10':{'class_type':'VAEEncode','inputs':{'pixels':['8',0],'vae':['3',0]}},
     '11':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':cfg,'sampler_name':'euler','scheduler':'simple','denoise':denoise,'model':['6',0],'positive':['7',0],'negative':['9',0],'latent_image':['10',0]}},
     '12':{'class_type':'VAEDecode','inputs':{'samples':['11',0],'vae':['3',0]}},
     '13':{'class_type':'SaveImage','inputs':{'images':['12',0],'filename_prefix':'QWEN_I2I'}},
    })
    return n

def build_t2i(prompt, seed, w=1024, h=1024, steps=8, cfg=1.0, with_lora=True):
    n = base_nodes(with_lora)
    n.update({
     '7':{'class_type':'CLIPTextEncode','inputs':{'text':prompt,'clip':['2',0]}},
     '9':{'class_type':'CLIPTextEncode','inputs':{'text':'','clip':['2',0]}},
     '14':{'class_type':'EmptySD3LatentImage','inputs':{'width':w,'height':h,'batch_size':1}},
     '11':{'class_type':'KSampler','inputs':{'seed':seed,'steps':steps,'cfg':cfg,'sampler_name':'euler','scheduler':'simple','denoise':1.0,'model':['6',0],'positive':['7',0],'negative':['9',0],'latent_image':['14',0]}},
     '12':{'class_type':'VAEDecode','inputs':{'samples':['11',0],'vae':['3',0]}},
     '13':{'class_type':'SaveImage','inputs':{'images':['12',0],'filename_prefix':'QWEN_T2I'}},
    })
    return n

def run(key, nodes, max_wait=600):
    t0 = time.time()
    resp = post('/prompt', {'prompt':nodes,'client_id':'qwen-'+key})
    if resp.get('node_errors'):
        print(f'[FAIL] {key} 节点校验: {json.dumps(resp["node_errors"])[:400]}'); return
    pid = resp['prompt_id']
    print(f'[RUN] {key} 已提交,等待(首次加载模型可能需数分钟)…')
    for _ in range(max_wait):
        time.sleep(5)
        try:
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error':
                    msgs = st.get('messages', [])
                    err = [m for m in msgs if m[0]=='execution_error']
                    print(f'[FAIL] {key} 执行错误: {json.dumps(err)[:500]}'); return
                if st.get('completed'):
                    imgs = []
                    for o in h[pid]['outputs'].values():
                        for im in o.get('images',[]): imgs.append(im['filename'])
                    print(f'[OK] {key} 完成: {imgs} 耗时 {round(time.time()-t0)}s')
                    return
        except Exception: pass
    print(f'[FAIL] {key} 超时({max_wait*5}s)')

PROMPT = 'The same woman from the source image, now standing in a cyberpunk night city with neon purple and cyan lights, wet street reflections. Keep her face, hairstyle and clothing exactly. Highly detailed, cinematic.'

print('========== 探测 1:I2I(带 Lightning LoRA,8步 cfg1 dn0.8)==========')
run('i2i_lora', build_i2i(PROMPT, 91001))
print('========== 探测 2:I2I 稳态复测(模型已驻留)==========')
run('i2i_steady', build_i2i(PROMPT, 91002))
print('========== 探测 3:T2I 改造(edit 模型文生图,8步 cfg1)==========')
run('t2i_lora', build_t2i('A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, shallow depth of field, filmic 35mm look, highly detailed.', 92001))
print('========== 探测 4:T2I 标准参数(20步 cfg4,无 LoRA)==========')
run('t2i_std', build_t2i('A cinematic portrait of a young woman with natural skin texture and loose brown hair, standing in a sunlit city street at golden hour, shallow depth of field, filmic 35mm look, highly detailed.', 92002, steps=20, cfg=4.0, with_lora=False))
