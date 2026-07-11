#!/usr/bin/env python3
"""
Patch: Add subtle background music to kinetic text videos.
Picks a random track from video_pipeline/music/ and mixes it
behind the TTS voiceover at 12% volume with fade in/out.
"""

filepath = "video_pipeline/kinetic_text_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Add music selection function before create_kinetic_video
music_func = '''def pick_background_music():
    music_dir = PIPELINE_DIR / "music"
    tracks = [f for f in music_dir.glob("*.mp3") if f.stat().st_size > 10000]
    if not tracks:
        print("  No music tracks found")
        return None
    track = random.choice(tracks)
    print(f"  BG music: {track.name}")
    return str(track)

'''

# Insert before create_kinetic_video
assert "def create_kinetic_video(" in content, "create_kinetic_video not found"
content = content.replace(
    "def create_kinetic_video(",
    music_func + "def create_kinetic_video("
)

# 2. Replace the FFmpeg encoding command to include music mixing
old_ffmpeg = '''    print("  Encoding..."); cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(fd,"frame_%05d.png"),"-i",audio_path,"-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True); shutil.rmtree(fd,ignore_errors=True)'''

new_ffmpeg = '''    music_path = pick_background_music()
    print("  Encoding...")
    if music_path:
        fade_out_start = max(0, audio_duration - 2)
        cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(fd,"frame_%05d.png"),"-i",audio_path,"-i",music_path,
            "-filter_complex",f"[2:a]volume=0.12,afade=t=in:d=2,afade=t=out:st={fade_out_start:.1f}:d=2[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map","0:v","-map","[aout]","-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    else:
        cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(fd,"frame_%05d.png"),"-i",audio_path,"-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True); shutil.rmtree(fd,ignore_errors=True)'''

assert old_ffmpeg in content, "FFmpeg command not found"
content = content.replace(old_ffmpeg, new_ffmpeg)

with open(filepath, "w") as f:
    f.write(content)

assert "pick_background_music" in content, "Music function not added"
assert "volume=0.12" in content, "Volume mix not found"
assert "afade=t=in" in content, "Fade not found"
print("Patch applied!")
print("- Picks random track from video_pipeline/music/")
print("- Mixed at 12% volume (barely audible, won't overpower voiceover)")
print("- 2-second fade in at start")
print("- 2-second fade out before end")
print("- Falls back to no music if tracks missing")
