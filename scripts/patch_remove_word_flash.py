#!/usr/bin/env python3
"""One-shot patch: Remove dead word_flash imports from US pipelines.
word_flash.py was deleted in the July 7 cleanup but both US pipeline
scripts still imported from it, causing ModuleNotFoundError crashes.
The imports were dead code (word flash overlays removed in v5.5/v2.7).
"""
import re

# --- Fix female_pipeline.py ---
fp = "video_pipeline/female_pipeline.py"
with open(fp) as f:
    content = f.read()

# Remove the dead import line
content = content.replace(
    "from video_pipeline.word_flash import pick_power_word, WORD_FLASH_STOPWORDS, POWER_WORDS\n",
    ""
)

with open(fp, "w") as f:
    f.write(content)

print(f"[female_pipeline.py] Removed word_flash import")
assert "word_flash" not in content, "word_flash still present in female!"
print("[female_pipeline.py] VERIFIED - no word_flash references")

# --- Fix male_pipeline_patch.py ---
mp = "video_pipeline/male_pipeline_patch.py"
with open(mp) as f:
    content = f.read()

# Remove the 3 import lines
content = content.replace(
    "from video_pipeline.word_flash import pick_power_word as fixed_pick_power_word\n",
    ""
)
content = content.replace(
    "from video_pipeline.word_flash import WORD_FLASH_STOPWORDS as FIXED_STOPWORDS\n",
    ""
)
content = content.replace(
    "from video_pipeline.word_flash import POWER_WORDS as FIXED_POWER_WORDS\n",
    ""
)

# Remove the 3 monkey-patch lines
content = content.replace(
    "pipeline.pick_power_word = fixed_pick_power_word\n",
    ""
)
content = content.replace(
    "pipeline.WORD_FLASH_STOPWORDS = FIXED_STOPWORDS\n",
    ""
)
content = content.replace(
    "pipeline.POWER_WORDS = FIXED_POWER_WORDS\n",
    ""
)

with open(mp, "w") as f:
    f.write(content)

print(f"[male_pipeline_patch.py] Removed word_flash imports + monkey-patches")
assert "word_flash" not in content, "word_flash still present in male!"
assert "fixed_pick_power_word" not in content, "monkey-patch still present!"
print("[male_pipeline_patch.py] VERIFIED - no word_flash references")

print("\nPatch complete! Both US pipelines fixed.")
