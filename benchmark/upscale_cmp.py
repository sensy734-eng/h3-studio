# -*- coding: utf-8 -*-
"""放大模型对比:同一源视频(960×544)依次用 3 个放大模型,记录耗时/分辨率/质量"""
import json, os, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'
SRC = r'D:\MiniMax-H3\ComfyUI\ComfyUI-master\output\UP_960x544_00001-audio.mp4'
OUT = r'D:\MiniMax-H3\ComfyUI\ComfyUI-master\output'
BENCH = r'D:\MiniMax-H3\benchmark'

MODELS = [
    {'name':'4xUltrasharp.pth', 'key':'ultrasharp'},
    {'name':'RealESRGAN_x4plus_anime_6B.pth', 'key':'realesrgan_anime'},
    {'name':'OmniSR_X2_DIV2K.safetensors', 'key':'omnisr_x2'},
]

def post(p, d):
    import urllib.request
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    import urllib.request
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

def build(model_name, prefix):
    return {
     '1':{'class_type':'VHS_LoadVideoPath','inputs':{'video':SRC,'force_rate':0,'custom_width':0,'custom_height':0,'frame_load_cap':0,'skip_first_frames':0,'select_every_nth':1}},
     '2':{'class_type':'UpscaleModelLoader','inputs':{'model_name':model_name}},
     '3':{'class_type':'ImageUpscaleWithModel','inputs':{'upscale_model':['2',0],'image':['1',0]}},
     '4':{'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':prefix,'format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['3',0],'audio':['1',2]}},
    }

results = []
for m in MODELS:
    print(f'=== 放大模型: {m["name"]} ===', flush=True)
    t0 = time.time()
    resp = post('/prompt', {'prompt':build(m['name'], 'UP_CMP_'+m['key']), 'client_id':'upcmp-'+m['key']})
    if resp.get('node_errors'):
        print('  节点错误:', json.dumps(resp['node_errors'])[:300]); continue
    pid = resp['prompt_id']
    fname = None
    for _ in range(600):
        time.sleep(5)
        try:
            h = get('/history/'+pid)
            if pid in h:
                st = h[pid]['status']
                if st.get('status_str')=='error':
                    msgs=[x for x in st.get('messages',[]) if x[0]=='execution_error']
                    print('  执行错误:', json.dumps(msgs)[:400]); break
                if st.get('completed'):
                    for o in h[pid]['outputs'].values():
                        for g in o.get('gifs',[]):
                            if str(g.get('format','')).startswith('video/'): fname = g['filename']
                    break
        except Exception: pass
    wall = round(time.time()-t0)
    if not fname:
        print('  失败'); continue
    # 分辨率与大小
    path = os.path.join(OUT, fname)
    probe = subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height','-of','csv=p=0',path],capture_output=True,text=True).stdout.strip()
    size_mb = round(os.path.getsize(path)/1048576, 1)
    # 抽帧清晰度
    import numpy as np
    from PIL import Image, ImageFilter
    frame_p = os.path.join(BENCH, 'frames_turbo', 'cmp_'+m['key']+'.png')
    subprocess.run(['ffmpeg','-y','-v','error','-ss','1.2','-i',path,'-frames:v','1',frame_p],capture_output=True)
    im = Image.open(frame_p).convert('L')
    lap = np.asarray(im.filter(ImageFilter.FIND_EDGES), dtype=np.float32)
    sharp = float(lap.var())
    rec = {'model':m['name'], 'wall_s':wall, 'resolution':probe, 'size_mb':size_mb, 'sharpness':sharp}
    results.append(rec)
    print(f'  完成: {fname} | {probe} | {wall}s | {size_mb}MB | 清晰度 {sharp:.1f}', flush=True)

json.dump(results, open(os.path.join(BENCH,'upscale_cmp.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('=== 对比完成 ===')
