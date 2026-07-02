#!/usr/bin/env python3
"""One-shot: Fix BrokenPipeError in kinetic video - redirect FFmpeg stderr."""

with open("video_pipeline/kinetic_text_pipeline.py") as f:
    content = f.read()

# Fix: change stderr=subprocess.PIPE to stderr logging to avoid deadlock
old = '    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)'
new = '''    import tempfile as _tf
    stderr_log = os.path.join(_tf.gettempdir(), "ffmpeg_kinetic.log")
    stderr_file = open(stderr_log, "w")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=stderr_file)'''

if old in content:
    content = content.replace(old, new)
    print("Fixed: subprocess stderr redirect")
else:
    print("ERROR: Could not find Popen line")

# Also fix the error reading part
old_err = '''    if proc.returncode != 0:
        stderr = proc.stderr.read().decode()
        print(f"  FFmpeg error: {stderr[-500:]}")
        raise RuntimeError("FFmpeg encoding failed")'''
new_err = '''    stderr_file.close()
    if proc.returncode != 0:
        with open(stderr_log) as ef:
            stderr = ef.read()
        print(f"  FFmpeg error: {stderr[-500:]}")
        raise RuntimeError("FFmpeg encoding failed")'''

if old_err in content:
    content = content.replace(old_err, new_err)
    print("Fixed: error reading from log file")
else:
    print("ERROR: Could not find error handling block")

with open("video_pipeline/kinetic_text_pipeline.py", "w") as f:
    f.write(content)
print("Done!")
