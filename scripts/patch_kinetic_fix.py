#!/usr/bin/env python3
"""One-shot: Fix kinetic video - replace FFmpeg drawtext with Pillow renderer."""
import re

NEW_FUNCTIONS = '''
def wrap_text_for_video(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_kinetic_video(audio_path, line_timestamps, output_path, audio_duration):
    from PIL import Image, ImageDraw, ImageFont
    FPS = 24
    total_frames = int((audio_duration + 0.5) * FPS)
    font_bold = None
    font_light = None
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            font_bold = ImageFont.truetype(p, 40)
            break
        except:
            continue
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try:
            font_light = ImageFont.truetype(p, 26)
            break
        except:
            continue
    if not font_bold:
        font_bold = ImageFont.load_default()
    if not font_light:
        font_light = ImageFont.load_default()
    max_text_width = int(WIDTH * 0.85)
    wrapped_blocks = []
    for lt in line_timestamps:
        wrapped = wrap_text_for_video(lt["text"], font_bold, max_text_width)
        wrapped_blocks.append({"lines": wrapped, "start": lt["start"], "end": lt.get("end", audio_duration)})
    line_h = 52
    gap = 24
    total_lines_count = sum(len(b["lines"]) for b in wrapped_blocks)
    total_height = total_lines_count * line_h + (len(wrapped_blocks) - 1) * gap
    base_y = (HEIGHT // 2) - (total_height // 2)
    bg = Image.new("RGB", (WIDTH, HEIGHT))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        ease = ratio * ratio * (3 - 2 * ratio)
        r = int(12 + (6 - 12) * ease)
        g = int(16 + (6 - 16) * ease)
        bv = int(32 + (12 - 32) * ease)
        bg_draw.line([(0, y), (WIDTH, y)], fill=(r, g, bv))
    print(f"  Rendering {total_frames} frames at {FPS}fps...")
    cmd = ["ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "pipe:0", "-i", audio_path, "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest", output_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for fn in range(total_frames):
        t = fn / FPS
        frame = bg.copy()
        draw = ImageDraw.Draw(frame)
        cy = base_y
        for block in wrapped_blocks:
            at = block["start"]
            if t < at:
                ar = 0.0
            elif t < at + 0.4:
                ar = (t - at) / 0.4
            else:
                ar = 1.0
            if ar <= 0:
                cy += len(block["lines"]) * line_h + gap
                continue
            active = True
            for o in wrapped_blocks:
                if o["start"] > block["start"] and t >= o["start"]:
                    active = False
                    break
            if active:
                brt = int(255 * ar)
                col = (brt, brt, brt)
            else:
                brt = int(120 * ar)
                col = (brt, brt, min(brt + 15, 255))
            for line in block["lines"]:
                bbox = font_bold.getbbox(line)
                tw = bbox[2] - bbox[0]
                x = (WIDTH - tw) // 2
                sb = int(40 * ar)
                draw.text((x + 2, cy + 2), line, font=font_bold, fill=(sb, sb, sb))
                draw.text((x, cy), line, font=font_bold, fill=col)
                cy += line_h
            cy += gap
        wt = "MindCore AI"
        wb = font_light.getbbox(wt)
        ww = wb[2] - wb[0]
        draw.text(((WIDTH - ww) // 2, HEIGHT - 100), wt, font=font_light, fill=(136, 136, 170))
        proc.stdin.write(frame.tobytes())
        if fn % (FPS * 2) == 0:
            print(f"    Frame {fn}/{total_frames} ({t:.1f}s)")
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()
        print(f"  FFmpeg error: {stderr[-500:]}")
        raise RuntimeError("FFmpeg encoding failed")
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Video created ({size_mb:.1f} MB, {audio_duration:.1f}s)")
'''

with open("video_pipeline/kinetic_text_pipeline.py") as f:
    content = f.read()

# Remove escape_ffmpeg_text
content = re.sub(r'def escape_ffmpeg_text\(text\):.*?return.*?\n\n', '', content, flags=re.DOTALL)

# Replace create_kinetic_video
start = content.find("def create_kinetic_video(")
end = content.find("\ndef get_scheduled_time(")
if start > 0 and end > 0:
    content = content[:start] + NEW_FUNCTIONS + "\n" + content[end:]
    print("Replaced with Pillow frame-by-frame renderer + word wrap")
else:
    print("ERROR: function boundaries not found")

with open("video_pipeline/kinetic_text_pipeline.py", "w") as f:
    f.write(content)
print("Done!")
