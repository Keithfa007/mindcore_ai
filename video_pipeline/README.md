# MindCore AI — Automated Video Pipeline

Automated short-form video pipeline for TikTok and Facebook.

## Stack
- **GitHub Actions** — scheduler and orchestrator
- **Anthropic API** — SEO-optimised script + video prompt + caption generation
- **Fish Audio API** — voiceover generation from script
- **WaveSpeed AI API** — AI background video generation
- **FFmpeg** — merges audio + video into final MP4

## Flow
```
GitHub Actions (Mon/Wed/Fri)
    → generate_script.py   (Anthropic API)
    → generate_voice.py    (Fish Audio API)
    → generate_video.py    (WaveSpeed AI API)
    → merge_video.py       (FFmpeg)
    → Upload finished MP4 as GitHub Release asset
```

## SEO Strategy
Scripts are generated using high-demand, low-competition keywords in the
men's mental health, recovery, and AI wellness niche:
- "AI mental health coach for men"
- "recovery support anxiety depression"
- "sobriety mental wellness app"
- "men's mental health tips"
- "anxiety relief for men"

## Folder Structure
```
video_pipeline/
├── README.md
├── requirements.txt
├── keywords.json
├── scripts/
│   ├── generate_script.py
│   ├── generate_voice.py
│   ├── generate_video.py
│   └── merge_video.py
├── prompts/
│   └── script_prompt.txt
└── .github/
    └── workflows/
        └── video_pipeline.yml
```

## Setup
1. Add the following secrets to GitHub repo settings:
   - `ANTHROPIC_API_KEY`
   - `FISH_AUDIO_API_KEY`
   - `WAVESPEED_API_KEY`
2. Push this folder to your repo
3. GitHub Actions will trigger Mon/Wed/Fri at 07:00 UTC

## Output
Finished MP4 is uploaded as a GitHub Release asset.
Download and post to TikTok and Facebook manually.
