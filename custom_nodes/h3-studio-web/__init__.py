"""
H3 Studio - MiniMax H3 简洁出片面板 + 多镜头拼接服务
访问 http://127.0.0.1:8188/h3-studio
路由:
  GET  /h3-studio           出片面板页面
  GET  /h3-studio/{name}    静态资源
  POST /h3-studio/frame     抽取视频最后一帧 -> input 目录(用于下一镜头首帧衔接)
  POST /h3-studio/stitch    多镜头拼接(硬切 -c copy / 叠化 xfade+acrossfade)
"""
import pathlib, subprocess, uuid, datetime

try:
    from server import PromptServer
    from aiohttp import web

    ROOT = pathlib.Path(__file__).parent.resolve()
    COMFY_ROOT = ROOT.parent.parent  # .../ComfyUI/ComfyUI-master
    OUT_DIR = COMFY_ROOT / "output"
    INP_DIR = COMFY_ROOT / "input"

    @PromptServer.instance.routes.get("/h3-studio")
    async def h3_studio_index(request):
        return web.FileResponse(ROOT / "h3-studio.html")

    @PromptServer.instance.routes.get("/h3-studio/{name}")
    async def h3_studio_asset(request):
        name = request.match_info["name"]
        p = (ROOT / name).resolve()
        if p.parent != ROOT:
            return web.Response(status=403)
        if p.is_file():
            return web.FileResponse(p)
        return web.Response(status=404)

    @PromptServer.instance.routes.post("/h3-studio/frame")
    async def h3_extract_last_frame(request):
        """抽视频最后一帧存到 input 目录,返回文件名供 LoadImage 使用"""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "json body required"}, status=400)
        filename = (data.get("filename") or "").strip()
        src = (OUT_DIR / filename).resolve()
        if not (src.is_file() and src.parent == OUT_DIR.resolve()):
            return web.json_response({"error": f"not found: {filename}"}, status=404)
        name = f"chain_{uuid.uuid4().hex[:10]}.png"
        dst = INP_DIR / name
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-sseof", "-0.2", "-i", str(src),
             "-frames:v", "1", str(dst)],
            capture_output=True, text=True)
        if r.returncode != 0 or not dst.is_file():
            return web.json_response({"error": r.stderr[-500:]}, status=500)
        return web.json_response({"name": name})

    @PromptServer.instance.routes.post("/h3-studio/stitch")
    async def h3_stitch(request):
        """拼接多镜头。mode: cut(硬切,-c copy 无损) / fade(叠化 0.5s,重编码)"""
        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "json body required"}, status=400)
        files = data.get("files") or []
        mode = data.get("mode", "cut")
        prefix = (data.get("prefix") or "Short_Film").strip() or "Short_Film"
        if not files:
            return web.json_response({"error": "no files"}, status=400)
        srcs = []
        for f in files:
            p = (OUT_DIR / str(f)).resolve()
            if not (p.is_file() and p.parent == OUT_DIR.resolve()):
                return web.json_response({"error": f"not found: {f}"}, status=404)
            srcs.append(p)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"{prefix}_{stamp}.mp4"
        out_path = OUT_DIR / out_name

        if mode == "cut":
            list_file = OUT_DIR / f"concat_{uuid.uuid4().hex[:8]}.txt"
            list_file.write_text(
                "\n".join(f"file '{p.name}'" for p in srcs) + "\n", encoding="utf-8")
            try:
                r = subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
                     "-i", str(list_file), "-c", "copy", str(out_path)],
                    capture_output=True, text=True)
                if r.returncode != 0 or not out_path.is_file():
                    return web.json_response({"error": r.stderr[-500:]}, status=500)
            finally:
                list_file.unlink(missing_ok=True)
        else:
            # 叠化:两两迭代 xfade(视频 0.5s)+ acrossfade(音频 0.5s),支持任意数量
            cur = srcs[0]
            tmp = []
            try:
                for nxt in srcs[1:]:
                    t = OUT_DIR / f"tmp_{uuid.uuid4().hex[:8]}.mp4"
                    tmp.append(t)
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "csv=p=0", str(cur)],
                        capture_output=True, text=True)
                    try:
                        dur = float(probe.stdout.strip())
                    except Exception:
                        dur = 5.0
                    offset = max(0.1, dur - 0.5)
                    fc = (
                        f"[0:v][1:v]xfade=transition=fade:duration=0.5:offset={offset:.3f}[v];"
                        f"[0:a][1:a]acrossfade=d=0.5[a]"
                    )
                    r = subprocess.run(
                        ["ffmpeg", "-y", "-v", "error", "-i", str(cur), "-i", str(nxt),
                         "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                         "-c:v", "libx264", "-crf", "19", "-preset", "medium",
                         "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p",
                         str(t)],
                        capture_output=True, text=True)
                    if r.returncode != 0 or not t.is_file():
                        return web.json_response({"error": r.stderr[-600:]}, status=500)
                    cur = t
                r = subprocess.run(
                    ["ffmpeg", "-y", "-v", "error", "-i", str(cur), "-c", "copy", str(out_path)],
                    capture_output=True, text=True)
                if r.returncode != 0 or not out_path.is_file():
                    return web.json_response({"error": r.stderr[-500:]}, status=500)
            finally:
                for t in tmp:
                    t.unlink(missing_ok=True)
        return web.json_response({"filename": out_name})

    print("[h3-studio] 路由已挂载(页面 + 抽帧 + 拼接): http://127.0.0.1:8188/h3-studio")
except Exception as e:  # 挂载失败不阻塞 ComfyUI 启动
    print(f"[h3-studio] 挂载失败(可忽略): {e}")

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
