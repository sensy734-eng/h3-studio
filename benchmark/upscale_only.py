# -*- coding: utf-8 -*-
"""放大链路验证(复用已生成的 UP_960x544 视频):4xUltrasharp 放大"""
import json, os, sys, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BASE = 'http://127.0.0.1:8188'
VFILE = 'up_src.mp4'

def post(p, d):
    import urllib.request
    req = urllib.request.Request(BASE+p, data=json.dumps(d).encode(), headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
def get(p):
    import urllib.request
    with urllib.request.urlopen(BASE+p, timeout=30) as r: return json.loads(r.read())

up = {
 '1':{'class_type':'VHS_LoadVideo','inputs':{'video':VFILE,'force_rate':0,'custom_width':0,'custom_height':0,'frame_load_cap':0,'skip_first_frames':0,'select_every_nth':1}},
 '2':{'class_type':'UpscaleModelLoader','inputs':{'model_name':'4xUltrasharp.pth'}},
 '3':{'class_type':'ImageUpscaleWithModel','inputs':{'upscale_model':['2',0],'image':['1',0]}},
 '4':{'class_type':'VHS_VideoCombine','inputs':{'frame_rate':24,'loop_count':0,'filename_prefix':'UP_4x','format':'video/h264-mp4','pix_fmt':'yuv420p','crf':19,'save_metadata':True,'trim_to_audio':False,'pingpong':False,'save_output':True,'images':['3',0],'audio':['1',2]}},
}
print('=== 4xUltrasharp 放大(960×544 → 3840×2176,124帧) ===')
t0 = time.time()
resp = post('/prompt', {'prompt':up,'client_id':'up-2b'})
if resp.get('node_errors'):
    print('节点错误:', json.dumps(resp['node_errors'])[:500]); sys.exit(1)
pid = resp['prompt_id']
for _ in range(600):
    time.sleep(5)
    try:
        h = get('/history/'+pid)
        if pid in h:
            st = h[pid]['status']
            if st.get('status_str')=='error':
                msgs=[m for m in st.get('messages',[]) if m[0]=='execution_error']
                print('执行错误:', json.dumps(msgs)[:500]); sys.exit(1)
            if st.get('completed'):
                outfile = None
                for o in h[pid]['outputs'].values():
                    for g in o.get('gifs',[]):
                        if str(g.get('format','')).startswith('video/'): outfile = g['filename']
                print(f'放大完成: {outfile} 耗时 {round(time.time()-t0)}s')
                sys.exit(0)
    except Exception: pass
print('超时')
