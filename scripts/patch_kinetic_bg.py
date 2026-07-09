#!/usr/bin/env python3
"""
Patch: Add visual diversity to kinetic text backgrounds.
Replaces the single hardcoded background style with 10 distinct visual categories
that rotate randomly, ensuring the TikTok grid looks varied.
"""

filepath = "video_pipeline/kinetic_text_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

# Replace the generate_bg_prompt function
old_func = '''def generate_bg_prompt(client, topic):
    question = topic.get("question", topic.get("topic", "mental health"))
    try: return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=100, messages=[{"role":"user","content":f"Short image prompt for a cinematic TikTok background.\\n\\nTOPIC: \\"{question}\\"\\n\\nBeautiful, well-lit, scenic. Think golden hour sunsets, twilight skies, ocean horizons, mountain vistas, city lights at dusk, rain on windows with warm interior light. Visible detail and colour. NOT pitch black. NO people, NO text, NO faces. Max 40 words.\\n\\nReturn ONLY the prompt."}]).content[0].text.strip()
    except: return "golden hour sunset over calm ocean, warm orange and pink sky, soft light reflecting on water, cinematic, no people, no text"'''

new_func = '''BG_VISUAL_CATEGORIES = [
    {
        "style": "golden_hour",
        "direction": "Golden hour landscapes. Warm sunset skies, amber light, long shadows, glowing horizons. Rich oranges, pinks, and golds.",
        "fallback": "golden hour sunset over calm ocean, warm orange and pink sky, soft light reflecting on water, cinematic, no people, no text"
    },
    {
        "style": "urban_night",
        "direction": "Urban night scenes. City rooftops, neon reflections on wet streets, distant skyline lights, empty bridges at night. Cool blues, purples, warm streetlight accents.",
        "fallback": "empty city street at night, neon signs reflecting on wet pavement, cool blue and purple tones, cinematic, no people, no text"
    },
    {
        "style": "nature_closeup",
        "direction": "Nature close-ups and textures. Dewdrops on leaves, moss on stone, flowing water over rocks, frost on branches. Rich greens, earthy tones, sharp detail.",
        "fallback": "macro dewdrops on green leaves, morning light filtering through, rich natural detail, earthy tones, cinematic, no people, no text"
    },
    {
        "style": "ocean_water",
        "direction": "Ocean and water scenes. Waves crashing on rocky shores, misty coastlines, underwater light, calm lake reflections. Deep blues, teals, white foam.",
        "fallback": "waves crashing on dark rocky coastline, misty ocean spray, deep blue and teal water, moody cinematic, no people, no text"
    },
    {
        "style": "minimalist_light",
        "direction": "Minimalist light and shadow. Sunlight through blinds, geometric shadows on walls, light beams through fog, single window light. Clean, simple, high contrast.",
        "fallback": "shaft of warm sunlight through window blinds casting geometric shadows on white wall, minimal, cinematic, no people, no text"
    },
    {
        "style": "forest_woods",
        "direction": "Forest and woodland scenes. Tall trees with light filtering through canopy, misty forest paths, autumn leaves, mossy old growth. Greens, browns, dappled light.",
        "fallback": "misty forest path with tall trees, morning light filtering through green canopy, dappled shadows, cinematic, no people, no text"
    },
    {
        "style": "mountain_sky",
        "direction": "Mountain and sky landscapes. Dramatic peaks, rolling clouds, starry skies, alpine meadows, vast open spaces. Epic scale, deep perspective.",
        "fallback": "dramatic mountain peaks above rolling clouds, vast alpine landscape, deep blue sky, epic cinematic scale, no people, no text"
    },
    {
        "style": "rain_cozy",
        "direction": "Rain and cozy interiors. Rain on windows with warm light inside, steamy coffee shop windows, puddle reflections, thunderstorm skies. Warm amber interiors against cool blue rain.",
        "fallback": "rain drops on window glass with warm amber light inside, blurred city lights beyond, cozy and cinematic, no people, no text"
    },
    {
        "style": "desert_arid",
        "direction": "Desert and arid landscapes. Sand dunes at dawn, cracked earth, red rock canyons, sparse vegetation, heat haze. Warm terracotta, burnt orange, dusty gold.",
        "fallback": "sand dunes at dawn with long shadows, warm terracotta and gold tones, vast empty desert landscape, cinematic, no people, no text"
    },
    {
        "style": "twilight_blue",
        "direction": "Twilight blue hour scenes. Deep blue sky just after sunset, silhouetted trees, early stars, calm water reflecting last light. Cool blues, soft purples, peaceful.",
        "fallback": "blue hour twilight sky over silhouetted trees, deep blue and soft purple tones, first stars appearing, peaceful cinematic, no people, no text"
    }
]

def generate_bg_prompt(client, topic):
    question = topic.get("question", topic.get("topic", "mental health"))
    style = random.choice(BG_VISUAL_CATEGORIES)
    print(f"  BG style: {style['style']}")
    try: return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=100, messages=[{"role":"user","content":f"Short image prompt for a cinematic TikTok background.\\n\\nTOPIC: \\"{question}\\"\\nVISUAL STYLE: {style['direction']}\\n\\nBeautiful, well-lit, visible detail and colour. NOT pitch black. NO people, NO text, NO faces. Max 40 words.\\n\\nReturn ONLY the prompt."}]).content[0].text.strip()
    except: return style["fallback"]'''

assert old_func in content, "Target function not found in kinetic pipeline"
content = content.replace(old_func, new_func)

with open(filepath, "w") as f:
    f.write(content)

assert "BG_VISUAL_CATEGORIES" in content, "BG_VISUAL_CATEGORIES not added"
assert "style['direction']" in content, "Style direction not in prompt"
assert 'BG style:' in content, "BG style print not added"
print("Patch applied successfully!")
print("10 visual categories added:")
for cat in ["golden_hour", "urban_night", "nature_closeup", "ocean_water", "minimalist_light",
            "forest_woods", "mountain_sky", "rain_cozy", "desert_arid", "twilight_blue"]:
    print(f"  - {cat}")
print("Each run picks a random category for visual diversity on the TikTok grid.")
