# -*- coding: utf-8 -*-
"""0.5 档方案验证:960×544·Turbo6·5s 生成 → 4xUltrasharp 放大"""
import json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'

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

def wait_done(pid, label, max_wait):
    t0 = time.time()
    for _ in range(max_wait):
        time.sleep(5)
        try:
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error':
                    msgs=[m for m in st.get('messages',[]) if m[0]=='execution_error']
                    raise RuntimeError(f'{label} 执行错误: '+json.dumps(msgs)[:300])
                if st.get('completed'):
                    return round(time.time()-t0), h[pid]
        except RuntimeError: raise
        except Exception: pass
    raise RuntimeError(f'{label} 超时')

# ---------- 1. 生成:960×544 · Turbo6 · 124帧 ----------
gen = {
 '1':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_video_vae_fp16.safetensors'}},
 '2':{'class_type':'VAELoader','inputs':{'vae_name':'minimax_h3_audio_vae_fp32.safetensors'}},
 '3':{'class_type':'CLIPLoader','inputs':{'clip_name':'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors','type':'minimax','device':'default'}},
 '4':{'class_type':'UNETLoader','inputs':{'unet_name':'minimax_h3_fl2va_pruned_int8_convrot.safetensors','weight_dtype':'default'}},
 '6':{'class_type':'MiniMaxH3AudioConditioningT8','inputs':{'prompt':PROMPT,'width':960,'height':544,'length':124,'task_type':'T2VA','audio_mode':'native','audio_denoise_strength':1.0,'add_source_as_reference':False,'prompt_primary_audio_ordinal':0,'strict_prompt_tags':True,'ref_image_size':'match','reference_video_policy':'official_2_to_15s','clip':['3',0],'video_vae':['1',0],'audio_vae':['2',0]}},
 '7':{'class_type':'MiniMaxH3TurboLoRA','inputs':{'model':['4',0],'lora_name':'minimax_h3_turbo_v4_step600_ema.safetensors','strength':1.0,'low_vram':False}},
 '8':{'class_type':'RandomNoise','inputs':{'noise_seed':85001}},
 '9':{'class_type':'BasicGuider','inputs':{'model':['7',0],'conditioning':['6',0]}},
 '14':{'class_type':'MiniMaxH3TurboSampler','inputs':{}},
 '15':{'class_type':'BasicScheduler','inputs':{'model':['7',0],'scheduler':'simple','steps':6,'denoise':1.0}},
 '10':{'class_type':'SamplerCustomAdvanced','inputs':{'noise':['8',0],'guider':['9',0],'sampler':['14',0],'sigmas':['15',0],'latent_image':['6',1]}},
 '11':{'class_type':'MiniMaxH3AVDecodeT8','inputs':{'av_latent':['10',0],'video_vae':['1',0],'audio_vae':['2',0]}},
 '12':{'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':'UP_960x544','format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['11',0],'audio':['11',1]}},
}
print('=== 步骤1:960×544 · Turbo6 生成 ===')
resp = post('/prompt', {'prompt':gen,'client_id':'up-1'})
if resp.get('node_errors'):
    print('节点错误:', json.dumps(resp['node_errors'])[:400]); sys.exit(1)
secs, hist = wait_done(resp['prompt_id'], '生成', 240)
vfile = None
for o in hist[resp['prompt_id']]['outputs'].values():
    for g in o.get('gifs',[]):
        if str(g.get('format','')).startswith('video/'): vfile = g['filename']
print(f'生成完成: {vfile} 耗时 {secs}s')

# ---------- 2. 放大:VHS 读回 → 4xUltrasharp → 重组 ----------
up = {
 '1':{'class_type':'VHS_LoadVideo','inputs':{'video':vfile,'force_rate':0,'custom_width':0,'custom_height':0,'frame_load_cap':0,'skip_first_frames':0,'select_every_nth':1}},
 '2':{'class_type':'UpscaleModelLoader','inputs':{'model_name':'4xUltrasharp.pth'}},
 '3':{'class_type':'ImageUpscaleWithModel','inputs':{'upscale_model':['2',0],'image':['1',0]}},
 '4':{'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':'UP_4x','format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['3',0],'audio':['1',2]}},
}
print('=== 步骤2:4xUltrasharp 放大(960×544 → 3840×2176,124帧) ===')
resp = post('/prompt', {'prompt':up,'client_id':'up-2'})
if resp.get('node_errors'):
    print('节点错误:', json.dumps(resp['node_errors'])[:400]); sys.exit(1)
secs2, hist2 = wait_done(resp['prompt_id'], '放大', 600)
outfile = None
for o in hist2[resp['prompt_id']]['outputs'].values():
    for g in o.get('gifs',[]):
        if str(g.get('format','')).startswith('video/'): outfile = g['filename']
print(f'放大完成: {outfile} 耗时 {secs2}s')
print(f'=== 全链路: 生成 {secs}s + 放大 {secs2}s = {secs+secs2}s ===')
