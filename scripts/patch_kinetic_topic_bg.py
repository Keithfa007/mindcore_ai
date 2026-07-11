#!/usr/bin/env python3
"""
Patch: Replace generic category backgrounds with topic-specific imagery.
Instead of random categories, Claude generates a prompt that directly
illustrates the video topic using symbolic/metaphorical imagery.
"""

filepath = "video_pipeline/kinetic_text_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

old_section = '''BG_VISUAL_CATEGORIES = [
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

new_section = '''def generate_bg_prompt(client, topic):
    question = topic.get("question", topic.get("topic", "mental health"))
    print(f"  BG topic: {question}")
    try: return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=100, messages=[{"role":"user","content":f"""Create an image prompt for a cinematic TikTok background that DIRECTLY illustrates this topic:

TOPIC: "{question}"

RULES:
- The image must visually represent the SPECIFIC emotion or concept in the topic
- Use symbolic or metaphorical imagery: broken objects, empty spaces, silhouettes from behind, hands, shadows, mirrors, clocks, chains, open doors, abandoned places, storms, paths
- Silhouettes and figures seen from behind or far away are OK and encouraged
- NO close-up faces, NO readable text, NO logos
- Moody, cinematic lighting. Dark enough for white text overlay but NOT pitch black
- High visual impact. This must stop someone scrolling on TikTok.
- Max 40 words

EXAMPLES:
- "anger in recovery" -> "silhouette of man punching wall in dark hallway, plaster dust in shaft of light, moody blue and amber tones, cinematic"
- "feeling invisible" -> "transparent ghostly figure standing in crowded subway station, motion blur of people walking through them, cold blue tones"
- "anxiety at 2am" -> "person sitting on edge of bed in dark room, blue phone glow on face seen from behind, moonlight through window, insomnia"
- "carrying everything alone" -> "single person carrying enormous bundle on back walking up endless staircase, dramatic overhead light, exhaustion"

Return ONLY the prompt."""}]).content[0].text.strip()
    except: return "lone silhouette standing at end of long dark corridor, single shaft of warm light ahead, moody cinematic atmosphere, emotional"'''

assert old_section in content, "Target section not found in kinetic pipeline"
content = content.replace(old_section, new_section)

with open(filepath, "w") as f:
    f.write(content)

assert "BG_VISUAL_CATEGORIES" not in content, "Old categories still present"
assert "symbolic or metaphorical imagery" in content, "New prompt not found"
assert "BG topic:" in content, "Topic print not found"
print("Patch applied!")
print("- Removed 10 generic visual categories")
print("- Background prompt now generates topic-specific imagery")
print("- Uses symbolic/metaphorical visuals (silhouettes, broken objects, empty spaces)")
print("- Examples guide Claude toward high-impact TikTok imagery")
