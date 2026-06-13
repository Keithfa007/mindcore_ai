#!/usr/bin/env python3
"""
MindCore AI -- RunPod Serverless Handler v1.5
=============================================
v1.5: Real-ESRGAN upscaling restored with torchvision shim fix.
v1.4: Upscaling disabled (torchvision compat).
v1.3: Real-ESRGAN 4K upscaling.
v1.2: Loads model from baked-in Docker image path.
v1.1: Lazy imports, error handling.
"""
import os, sys, base64, subprocess

MODEL_CACHE = "/app/models" if os.path.exists("/app/models") else "/workspace/.cache/huggingface"
os.environ["HF_HOME"] = MODEL_CACHE
os.environ["TMPDIR"] = "/workspace/tmp"
os.makedirs("/workspace/tmp", exist_ok=True)

import runpod

pipe = None
upsampler_cache = {}


def load_model():
    global pipe
    import torch
    from diffusers import AutoModel, WanPipeline

    print(f"Loading Wan 2.1 T2V 1.3B from {MODEL_CACHE}...")
    sys.stdout.flush()

    vae = AutoModel.from_pretrained(
        "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        subfolder="vae",
        torch_dtype=torch.float32,
        cache_dir=MODEL_CACHE,
    )
    pipe = WanPipeline.from_pretrained(
        "Wan-AI/Wan2.1-T2V-1.3B-Diffusers",
        vae=vae,
        torch_dtype=torch.bfloat16,
        cache_dir=MODEL_CACHE,
    )
    pipe.enable_model_cpu_offload()
    print("Wan 2.1 model loaded.")
    sys.stdout.flush()


def load_upscaler(scale=2):
    global upsampler_cache
    if scale in upsampler_cache:
        return upsampler_cache[scale]

    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    print(f"Loading Real-ESRGAN x{scale} upscaler...")
    sys.stdout.flush()

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
    model_path = f"/app/realesrgan_models/RealESRGAN_x{scale}plus.pth"

    upsampler = RealESRGANer(
        scale=scale, model_path=model_path, model=model,
        tile=256, tile_pad=10, pre_pad=0, half=True,
    )
    upsampler_cache[scale] = upsampler
    print(f"Real-ESRGAN x{scale} loaded.")
    sys.stdout.flush()
    return upsampler


def upscale_video(input_path, output_path, scale=2):
    import cv2
    upsampler = load_upscaler(scale)

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Upscaling {total} frames at {scale}x...")
    sys.stdout.flush()

    frames_out = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        output, _ = upsampler.enhance(frame, outscale=scale)
        frames_out.append(output)
        idx += 1
        if idx % 20 == 0:
            print(f"  Upscaled {idx}/{total} frames")
            sys.stdout.flush()
    cap.release()

    if not frames_out:
        return input_path

    h, w = frames_out[0].shape[:2]
    temp_raw = "/workspace/tmp/upscaled_raw.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(temp_raw, fourcc, fps, (w, h))
    for f in frames_out:
        writer.write(f)
    writer.release()

    subprocess.run([
        "ffmpeg", "-y", "-i", temp_raw,
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p", output_path
    ], capture_output=True, check=True)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"  Upscaled: {size_kb:.0f} KB ({w}x{h})")
    sys.stdout.flush()
    return output_path


def handler(event):
    global pipe

    try:
        if pipe is None:
            load_model()

        from diffusers.utils import export_to_video

        inp = event.get("input", {})
        prompt = inp.get("prompt", "Cinematic aerial drone shot of ocean waves at sunset")
        num_frames = inp.get("num_frames", 81)
        height = inp.get("height", 832)
        width = inp.get("width", 480)
        guidance = inp.get("guidance_scale", 7.5)
        fps = inp.get("fps", 16)
        upscale = inp.get("upscale", 2)

        print(f"Generating: {prompt[:80]}...")
        sys.stdout.flush()

        import torch
        output = pipe(
            prompt=prompt,
            num_frames=num_frames,
            guidance_scale=guidance,
            height=height,
            width=width,
        ).frames[0]

        raw_path = "/workspace/tmp/output_raw.mp4"
        export_to_video(output, raw_path, fps=fps)
        raw_kb = os.path.getsize(raw_path) / 1024
        print(f"Generated: {raw_kb:.0f} KB ({width}x{height})")
        sys.stdout.flush()

        if upscale and upscale > 1:
            final_path = "/workspace/tmp/output_upscaled.mp4"
            upscale_video(raw_path, final_path, scale=upscale)
        else:
            final_path = raw_path

        with open(final_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()

        size_kb = os.path.getsize(final_path) / 1024
        print(f"Done: {size_kb:.0f} KB")
        sys.stdout.flush()

        return {"video_base64": video_b64, "size_kb": round(size_kb)}

    except Exception as e:
        print(f"Handler error: {e}")
        import traceback; traceback.print_exc()
        sys.stdout.flush()
        return {"error": str(e)}


print(f"MindCore AI RunPod Handler v1.5 (Real-ESRGAN upscaling) starting...")
sys.stdout.flush()
runpod.serverless.start({"handler": handler})
