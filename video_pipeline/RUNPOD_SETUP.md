# RunPod Serverless Setup -- MindCore AI

## Overview
This deploys Wan 2.1 T2V 1.3B as a serverless API endpoint on RunPod.
Your pipeline calls it like any API -- no pods to manage.

## Step 1: Build Docker Image

```bash
cd video_pipeline
docker build -f Dockerfile.runpod -t mindcore-wan21:latest .
```

## Step 2: Push to Docker Hub

```bash
docker tag mindcore-wan21:latest YOUR_DOCKERHUB/mindcore-wan21:latest
docker push YOUR_DOCKERHUB/mindcore-wan21:latest
```

## Step 3: Create RunPod Serverless Endpoint

1. Go to https://www.runpod.io/console/serverless
2. Click **New Endpoint**
3. Template: **Custom** 
4. Docker Image: `YOUR_DOCKERHUB/mindcore-wan21:latest`
5. GPU: **RTX 3090** (24GB VRAM, cheapest option)
6. Min Workers: **0** (scales to zero when idle)
7. Max Workers: **1** (prevents runaway costs)
8. Idle Timeout: **60 seconds**
9. Execution Timeout: **600 seconds**
10. Click **Create**

## Step 4: Get Your Credentials

From the endpoint page, note:
- **Endpoint ID** (e.g., `abc123xyz`)
- **API Key** from RunPod Settings > API Keys

## Step 5: Add GitHub Secrets

- `RUNPOD_API_KEY` -- your RunPod API key
- `RUNPOD_ENDPOINT_ID` -- from step 4

## Step 6: Switch Pipeline

In your pipeline code, replace:
```python
from video_pipeline.pexels_clips import fetch_pexels_clip_for_scene
```
with:
```python
from video_pipeline.runpod_clips import fetch_drone_journey_clips
```

## API Usage

```python
# Single clip
from video_pipeline.runpod_clips import fetch_runpod_clip
fetch_runpod_clip("drone shot of ocean at sunset", 0, "output.mp4")

# Full drone journey (5 clips, one location)
from video_pipeline.runpod_clips import fetch_drone_journey_clips
clips = fetch_drone_journey_clips("ocean", "/tmp/clips")
```

## Themes Available
- ocean -- coastal drone journey from dawn to sunset
- mountain -- alpine peaks, valleys, clouds
- forest -- canopy, rivers, waterfalls
- desert -- dunes, canyons, starry skies
- coast -- beaches, cliffs, lighthouses

## Cost
- ~$0.03 per clip (5 min generation on RTX 3090)
- ~$0.15 per full video (5 clips)
- $0 when idle (scales to zero)
