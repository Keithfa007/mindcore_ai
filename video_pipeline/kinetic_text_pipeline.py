#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v4.1
===============================================
SERP-enriched cinematic word-by-word karaoke.
Supports GENDER env var: "male" (default) or "female".

v4.1: Gender support — switches voice, persona, keywords file, SERP seeds.
  - male: loads niche_keywords.json (male personas + seeds)
  - female: loads niche_keywords_female.json (female personas + seeds)
v4.0: SERP research, dynamic backgrounds, SEO captions, topic history.
v3.1: Word-by-word karaoke, Montserrat font, Ken Burns AI background.
"""

import os, sys, json, random, subprocess, tempfile, datetime, time, math
from pathlib import Path
from anthropic import Anthropic
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_USER    = os.environ.get("UPLOAD_POST_USER", "MindCoreAI")
FAL_KEY             = os.environ.get("FAL_KEY", "")
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
GENDER              = os.environ.get("GENDER", "male").lower()
MALE_VOICE_ID       = "jfIS2w2yJi0grJZPyEsk"
FEMALE_VOICE_ID     = "uIZsnBL0YK1S5j69bAih"
ELEVENLABS_VOICE_ID = FEMALE_VOICE_ID if GENDER == "female" else MALE_VOICE_ID
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"
SERP_API_URL        = "https://serpapi.com/search"
ANTHROPIC_MODEL     = "claude-sonnet-4-6"
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
POST_HOUR_UTC       = int(os.environ.get("POST_HOUR_UTC", "15"))

OUTPUT_DIR = Path("video_pipeline/output_kinetic")
PIPELINE_DIR = Path("video_pipeline")
KEYWORDS_PATH = PIPELINE_DIR / ("niche_keywords_female.json" if GENDER == "female" else "niche_keywords.json")
KINETIC_HISTORY_PATH = PIPELINE_DIR / "kinetic_topic_history.json"
WIDTH = 1080
HEIGHT = 1920
TOPIC_HISTORY_SIZE = 8
