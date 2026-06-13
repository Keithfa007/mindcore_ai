"""
MindCore AI -- RunPod AI Video Clips v2.0
==========================================
v2.0: All 80 drone prompts rewritten for Wan 2.2 prompt framework.
      Structure: Opening Shot -> Camera Motion -> Reveal/Payoff.
      Explicit camera terms (dolly, crane, pan, orbital, tracking).
      Parallax depth cues, speed modifiers, aesthetic tags.
      Removed generic "4K"/"photorealistic" filler.
v1.9: Added ice_adventure theme.
v1.8: Added urban_night, fog_weather, architecture themes (15 total).
v1.7: Real-ESRGAN upscaling.
v1.6: PARALLEL clip generation.
v1.3: All prompts rewritten for strong continuous flying movement.
v1.1: 12 drone journey themes.

Replaces pexels_clips.py when RunPod Serverless is active.
"""

import os, base64, time, subprocess, requests
from pathlib import Path

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

CROSSFADE_DURATION = 0.8
CLIP_DURATION = 5.06
UPSCALE_FACTOR = 2

_used_prompts = set()

# ── Wan 2.2 Optimised DRONE_THEMES ──────────────────────────────────────
# Framework per prompt: Opening Shot -> Camera Motion -> Reveal/Payoff
# Rules: 80-120 words, explicit camera terms, parallax cues,
#        speed modifiers, aesthetic tags Wan 2.2 responds to.

DRONE_THEMES = {
    "ocean": [
        {"name": "approach", "prompt": "FPV drone races forward at extreme low altitude over dark blue ocean waves at dawn. Camera dollies forward relentlessly, spray misting up from the churning surface in the foreground while the distant horizon glows amber. Foreground motion blur from wave proximity. Continuous fluid forward motion. Volumetric golden light cuts through sea mist. Anamorphic lens flare. Teal-and-orange color grading, crushed shadows, cinematic grain."},
        {"name": "waves", "prompt": "Aerial tracking shot moving steadily forward above massive turquoise ocean waves rolling and breaking in slow cascading patterns. Camera maintains constant forward dolly over the water surface. White foam spirals spread outward in the mid-ground. Morning golden sunlight reflects off each wave crest. Deep cinematic contrast, crushed blacks, amber highlights. Smooth fluid motion at moderate pace."},
        {"name": "coast", "prompt": "Cinematic drone tracking shot moving laterally along dramatic volcanic coastline cliffs. Camera pans left to right steadily while enormous waves crash against foreground rocks sending white spray upward. A tiny distant fishing boat provides scale against the vast dark ocean background. Continuous steady lateral movement. Golden hour warm sidelight rakes across the cliff textures. Teal-and-orange grade, anamorphic bokeh on spray droplets."},
        {"name": "calm", "prompt": "Aerial drone glides forward steadily over perfectly still crystal clear tropical water. Camera dollies forward in smooth continuous motion. Turquoise and emerald green water reveals sandy bottom and coral shapes below through the transparent surface. Gentle ripples catch golden morning sunlight creating dancing caustics. Foreground water detail separates from distant pale horizon. Saturated tropical color palette, warm highlights."},
        {"name": "sunset", "prompt": "Cinematic drone races forward over open ocean directly toward a golden setting sun on the horizon. Camera dollies forward relentlessly along the reflection path stretching across the water surface ahead. Orange and pink sky fills the upper frame. Continuous forward motion with subtle altitude drift. Warm golden color grading, crushed shadows, amber and magenta highlights. Anamorphic lens flare from sun. Smooth fluid pace."},
    ],
    "mountain": [
        {"name": "valley", "prompt": "Cinematic drone flies forward through a deep mountain valley at dawn. Camera dollies through the narrow gap between towering dark peaks on both sides. Thick white mist rises around the lens in the foreground while first golden sunlight hits distant ridge tops. Continuous smooth forward tracking through the valley. Volumetric light rays cut through the fog. Teal-and-orange with enhanced contrast, cinematic grain, epic scale."},
        {"name": "ridgeline", "prompt": "FPV drone races forward along a dramatic mountain ridgeline at golden hour. Camera tracks fast along the narrow ridge with steep drops visible on both sides creating strong parallax depth. Snow-capped peaks fill the background horizon. Foreground motion blur from speed and proximity. Continuous forward motion with slight banking. Warm golden sidelight, crushed shadows, amber highlights. Adrenaline and scale."},
        {"name": "lake", "prompt": "Aerial drone glides forward steadily over a still alpine lake at dawn. Camera dollies forward across the mirror-like water surface reflecting snow-capped mountains and dark pine forest shoreline. Morning golden light touches the distant peaks while the foreground water remains in cool blue shadow. Continuous smooth forward motion. Natural color palette with enhanced blues, subtle warm highlights, cinematic vignetting."},
        {"name": "clouds", "prompt": "Cinematic drone rises vertically through a layer of white clouds. Camera cranes upward continuously, emerging above the cloud sea to reveal majestic snow-capped mountain peaks piercing through like islands. Golden sunrise paints the snow warm orange while cloud tops glow white. Smooth continuous vertical tracking shot. Dramatic scale shift from enclosed to infinite. Warm highlights with cool cloud shadows, volumetric light."},
        {"name": "summit", "prompt": "Aerial drone orbits slowly around a dramatic mountain summit at golden sunset. Camera performs a continuous wide orbital arc around the peak revealing 360 degrees of endless mountain ranges receding into atmospheric haze. Tiny climber silhouettes on the ridge provide human scale. Continuous smooth circular motion. Warm golden-pink light, teal shadows in valleys. Cinematic grain, anamorphic bokeh on distant peaks."},
    ],
    "forest": [
        {"name": "canopy", "prompt": "Cinematic drone glides forward low over an endless lush green forest canopy at golden hour. Camera dollies forward steadily over the textured treetops. Thick white morning mist rises between the trees in the mid-ground. Volumetric sunlight rays pierce the canopy creating god-ray beams in the foreground. Continuous smooth forward tracking. Rich saturated greens with warm dappled golden highlights. Cinematic grain, soft depth of field on distant tree line."},
        {"name": "river", "prompt": "Aerial drone tracks forward following a crystal clear winding river cutting through dense ancient forest below. Camera dollies forward along the river course maintaining it centered in frame. Sunlight sparkles on the water surface creating bright foreground highlights against dark green forest on both banks. Continuous forward motion following the curves. Rich emerald greens with enhanced water clarity and warm golden accents."},
        {"name": "waterfall", "prompt": "Cinematic drone rises slowly in front of a massive waterfall cascading down moss-covered cliff face. Camera cranes upward continuously from the churning pool base, mist and spray filling the foreground, steadily revealing the full towering scale of the falls above. A rainbow arcs through the spray in the mid-ground. Smooth continuous vertical tracking. Cool blues and whites with prismatic iridescent highlights in the mist."},
        {"name": "clearing", "prompt": "Aerial drone flies forward into a sunlit forest clearing filled with wildflowers. Camera dollies forward steadily through the gap in the dark tree canopy as golden hour light floods through in volumetric beams. Flower petals drift in the foreground air. Transition from dark forest shadow to warm golden illumination. Continuous forward discovery motion. Warm earth tones with saturated greens and amber sun rays."},
        {"name": "sunset_canopy", "prompt": "Cinematic drone rises above the forest canopy at golden sunset. Camera cranes upward continuously from treetop level, revealing an endless sea of green forest stretching to the horizon. Tiny hikers visible on a trail far below provide human scale. Golden warm light floods across the canopy surface while long shadows stretch between the trees. Smooth vertical tracking shot. Warm amber grading, crushed shadows, cinematic grain."},
    ],
    "desert": [
        {"name": "dunes", "prompt": "FPV drone races forward at extreme low altitude over golden sand dunes at sunrise. Camera dollies forward fast over the ridgelines, foreground sand texture blurring past the lens. Long dramatic shadows stretch across the dune faces below. Fine sand blows off the crests in wispy trails. Continuous fast forward motion with subtle altitude changes. Warm earth tones, enhanced sand texture, golden rim light on dune edges."},
        {"name": "canyon", "prompt": "FPV drone races forward through a narrow red rock slot canyon. Camera dollies fast between towering sandstone walls rising on both sides creating strong parallax depth. Foreground rock texture blurs past while golden sunlight streams down from the narrow opening above casting dramatic light shafts. Continuous forward motion through the winding passage. High contrast, saturated red and orange rock tones against deep blue shadow."},
        {"name": "mesa", "prompt": "Aerial drone orbits slowly around a dramatic desert mesa formation at golden hour. Camera performs a continuous wide orbital arc around the flat-topped rock. Vast desert floor stretches to the distant horizon below creating epic scale. Long shadows stretch from the mesa base across the textured ground. Continuous smooth circular motion. Warm earth tones with enhanced rock texture and long shadow detail, golden rim light."},
        {"name": "oasis", "prompt": "Cinematic drone descends forward toward a hidden desert oasis with clustered palm trees and turquoise water pool. Camera dollies forward and downward simultaneously, golden sand dunes dominating the foreground frame gradually giving way to green vegetation and water below. Continuous smooth approach and descent. Transition from hot desaturated sand to vibrant cool oasis tones. Warm-to-cool color shift."},
        {"name": "stars", "prompt": "Cinematic drone rises slowly above a dark desert landscape at night. Camera cranes upward continuously from ground-level rock formations in the foreground, tilting up to reveal an overwhelming starry sky with the Milky Way band stretching diagonally across the entire frame. Slow smooth vertical tracking upward. Time-lapse star motion. Deep cinematic blues and purples, enhanced star brightness against inky black, cosmic silence atmosphere."},
    ],
    "coast": [
        {"name": "lighthouse", "prompt": "Cinematic drone approaches a dramatic lighthouse perched on rocky sea cliffs at golden sunrise. Camera dollies forward continuously toward the lighthouse growing larger in frame. Waves crash against foreground rocks sending spray upward. Warm beacon light glows from the tower. Continuous smooth forward approach with rising altitude. Warm golden grading, crushed shadows, amber highlights. Volumetric mist around the cliff base."},
        {"name": "beach_flight", "prompt": "FPV drone races forward at low altitude along a pristine sandy beach at golden hour. Camera tracks fast along the shoreline with turquoise waves rolling in on one side and palm tree silhouettes on the other creating strong lateral parallax. Foreground sand texture blurs from speed. Continuous forward coastal tracking. Saturated tropical color palette, warm golden sidelight, motion blur on wave foam."},
        {"name": "tide_pools", "prompt": "Aerial drone glides forward steadily over beautiful rocky tide pools at low tide. Camera dollies forward over the crystal clear pool formations revealing underwater detail through the still water surface. Gentle waves lap at the far edges creating subtle motion. Morning golden light reflects off each pool in the mid-ground. Continuous smooth forward tracking at moderate pace. Natural tones with enhanced turquoise water clarity."},
        {"name": "cliff_sunset", "prompt": "Cinematic drone tracks laterally along towering sea cliffs at golden sunset. Camera pans slowly along the cliff face while dramatic warm light paints the rock textures orange and gold. Seabirds soar in the foreground below camera level creating depth parallax. Continuous smooth lateral movement. Teal ocean below contrasts with warm orange cliff face. Anamorphic bokeh, cinematic grain, epic coastal scale."},
        {"name": "aerial_rise", "prompt": "Cinematic drone rises high above a curved bay coastline at sunset. Camera cranes upward continuously from beach level, the golden sand beach and turquoise water expanding below with increasing altitude. The bay curve reveals its full shape as the frame widens. Smooth continuous vertical tracking shot. Warm golden highlights on sand, cool teal shadows in deep water. Scale transition from intimate to epic."},
    ],
    "volcano": [
        {"name": "crater", "prompt": "Cinematic drone approaches a massive volcanic crater at dawn. Camera dollies forward slowly toward the rim as wisps of steam rise through the foreground. Dark volcanic landscape dominates the mid-ground with a growing orange glow visible ahead from within the crater. Continuous smooth forward approach building tension. Dramatic orange and deep shadow contrast, desaturated earth tones, volumetric steam lit from below."},
        {"name": "lava_flow", "prompt": "Aerial drone tracks forward low over rivers of glowing orange molten lava flowing down a dark volcanic slope at night. Camera dollies forward along the lava river course. Intense heat shimmer distorts the air above the flow in the foreground. Red-orange lava veins branch below against black cooled rock. Continuous forward motion following the flow. High contrast orange-against-black, enhanced thermal glow, no ambient light."},
        {"name": "ash_fields", "prompt": "Aerial drone glides forward steadily over vast black volcanic ash fields. Camera dollies forward over dramatic cracks and hardened texture patterns. Patches of bright green vegetation breaking through the dark surface create contrast in the mid-ground. Continuous smooth forward tracking. Highly desaturated with enhanced surface texture contrast and detail. Muted palette punctuated by vivid green life emerging."},
        {"name": "steam_vents", "prompt": "Cinematic drone orbits slowly around geothermal steam vents erupting from dark fractured volcanic rock. Camera performs a continuous circular arc around the vents. Golden sunrise backlights the rising steam columns creating dramatic volumetric god rays and silhouettes. Continuous smooth orbital motion. Warm orange-gold backlight against cool teal shadow. Dramatic contrast between light steam and dark rock."},
        {"name": "volcano_sunset", "prompt": "Cinematic drone rises above a volcanic island at golden sunset. Camera cranes upward continuously revealing the entire dark landscape glowing orange below while the surrounding ocean catches warm sunset reflections stretching to the horizon. Scale shifts from close volcanic texture to epic island overview. Smooth vertical tracking. Warm golden-amber grading, crushed deep shadows, cinematic grain."},
    ],
    "northern_lights": [
        {"name": "first_glow", "prompt": "Cinematic drone glides forward low over a frozen arctic landscape at blue-hour twilight. Camera dollies forward steadily over snow and ice formations in the foreground. Faint green aurora borealis shimmers on the distant horizon ahead growing slowly brighter. Continuous smooth forward motion into the emerging light. Deep cinematic blues and teals transitioning to aurora green. Magical atmosphere, soft diffused ambient light."},
        {"name": "full_display", "prompt": "Aerial drone orbits slowly above a snow-covered valley as vivid green and purple northern lights dance overhead in curtain-like ribbons. Camera performs a wide continuous orbital arc. Aurora reflections shimmer on a frozen lake surface below creating a mirror effect. Stars visible through the auroral gaps. Continuous smooth circular motion. Vibrant saturated aurora greens and purples against deep blue-black sky."},
        {"name": "mountains", "prompt": "Cinematic drone dollies forward between snow-capped arctic mountain peaks at night. Camera moves continuously through the mountain corridor. Brilliant green and blue aurora borealis curtains wave and pulse overhead between the peaks. Snow reflects the green glow in the foreground. Continuous forward tracking through the illuminated passage. Deep cinematic blues with vivid aurora greens, enhanced color saturation."},
        {"name": "reflection", "prompt": "Aerial drone glides forward over a perfectly still arctic fjord at night. Camera dollies forward steadily over the mirror-like water surface. Vivid green and pink northern lights reflected perfectly in the water below creating a symmetric double image. Dark mountain silhouettes frame both sides. Continuous smooth forward motion. Enhanced aurora colors with deep shadow contrast, glass-like water texture."},
        {"name": "fade", "prompt": "Cinematic drone rises slowly above the arctic landscape as northern lights soften into pre-dawn blue. Camera cranes upward continuously. The aurora fades while first warm golden sunlight touches distant mountain peaks on the horizon. Transitional atmosphere from night magic to dawn reality. Smooth continuous vertical tracking. Color grading transitions from cool aurora blues to warm golden sunrise tones."},
    ],
    "tropical_island": [
        {"name": "discovery", "prompt": "FPV drone races forward over deep blue ocean toward a lush tropical island on the distant horizon. Camera dollies forward fast with ocean surface blurring in the foreground. The island grows steadily larger revealing palm trees and white sand beaches through atmospheric haze. Continuous forward approach with building anticipation. Vibrant tropical color grading, saturated blues transitioning to greens, motion blur on wave crests."},
        {"name": "lagoon", "prompt": "Aerial drone glides forward over a stunning turquoise tropical lagoon. Camera dollies forward in smooth steady motion. Crystal clear water reveals coral reef formations and white sand patterns on the shallow bottom below. Gentle surface ripples catch sunlight creating dancing caustic light patterns. Continuous forward tracking over paradise water. Vibrant turquoise and emerald tones, warm golden sunlight highlights."},
        {"name": "palm_beach", "prompt": "FPV drone races forward along a pristine white sand beach lined with coconut palms. Camera tracks fast at low altitude along the shoreline. Crystal clear turquoise waves roll in on one side while tropical vegetation creates a green wall on the other, strong lateral parallax. Foreground sand texture blurs from speed. Continuous forward coastal motion. Saturated warm tropical palette, golden sidelight through palm fronds."},
        {"name": "jungle", "prompt": "Cinematic drone pushes forward through lush tropical jungle canopy at low altitude. Camera dollies steadily through the green tunnel of leaves and branches. Exotic flowers and large leaves pass close in the foreground while a hidden waterfall becomes visible ahead through the parting trees. Continuous forward discovery motion. Rich saturated greens with warm dappled golden highlights filtering through the canopy gaps."},
        {"name": "island_sunset", "prompt": "Cinematic drone rises high above the tropical island at golden sunset. Camera cranes upward continuously revealing the full island shape surrounded by glowing turquoise water gradually expanding below. The horizon widens with increasing altitude. Smooth vertical tracking shot creating epic scale transition. Warm golden-amber sky grading, crushed shadows, turquoise water contrast. Intimate to infinite."},
    ],
    "storm_clearing": [
        {"name": "dark_approach", "prompt": "Cinematic drone flies forward toward massive dark storm clouds building on the horizon. Camera dollies forward toward the storm wall. Lightning flickers inside the towering clouds ahead while wind bends tall grass in the foreground below. Continuous forward approach building dramatic tension. Desaturated color palette with high contrast, dark dramatic sky dominating frame. Volumetric cloud detail."},
        {"name": "rain_wall", "prompt": "Aerial drone tracks forward alongside a dramatic wall of heavy rain sweeping across green countryside. Camera dollies forward parallel to the curtain of rain. Dark sky above contrasts with bright sunlit landscape visible ahead beyond the rain edge. Continuous forward motion along the weather boundary. High contrast between dark storm and bright clearing. Desaturated rain zone against saturated sunlit zone."},
        {"name": "eye_of_storm", "prompt": "Cinematic drone rises vertically through a break in massive storm clouds. Camera cranes upward through the narrow gap. Dark threatening clouds tower on all sides of the frame while brilliant blue sky and golden sunlight appear above through the opening. Smooth continuous vertical tracking upward through the eye. Dramatic contrast transition from dark moody tones to warm hopeful golden light above."},
        {"name": "rainbow", "prompt": "Aerial drone dollies forward toward a vivid double rainbow arcing across the clearing sky. Camera moves steadily toward the rainbow as storm clouds retreat in the background. Golden sunlight breaks through in volumetric beams illuminating rain-wet landscape in the foreground. Continuous forward tracking toward the light. Prismatic rainbow highlights with enhanced saturation. Transition from storm to clarity."},
        {"name": "clear_sky", "prompt": "Cinematic drone rises above freshly washed green landscape after a storm. Camera cranes upward continuously revealing everything glistening with rain droplets catching warm golden sunlight. Blue sky expands rapidly overhead as altitude increases. Rain-wet surfaces create reflective highlights across fields and trees. Smooth vertical tracking. Warm golden grading, enhanced wet surface reflections, deep saturated greens."},
    ],
    "lake_morning": [
        {"name": "mist", "prompt": "Cinematic drone glides forward at low altitude over a glassy calm lake at dawn. Camera dollies through thick white morning mist hovering just above the water surface. Dark pine tree silhouettes emerge from the fog ahead as shapes. Foreground mist wraps around the lens. Continuous smooth forward tracking through the atmospheric layer. Monochromatic cool palette with subtle warm golden shifts where sunlight penetrates."},
        {"name": "reflection", "prompt": "Aerial drone glides forward over perfectly still lake water reflecting mountains like a symmetrical mirror. Camera dollies steadily forward over the glass-like surface. The real mountains above and their inverted reflection below create a doubled landscape. Morning golden light touches the peaks. Continuous smooth forward motion across the mirror. Natural color palette with enhanced cool blues and warm peak highlights."},
        {"name": "shoreline", "prompt": "Aerial drone tracks forward following a winding lake shoreline at golden hour. Camera dollies along the shore contour. Crystal clear shallows reveal bottom detail in the foreground while autumn-colored trees in orange and red line the far bank creating warm lateral parallax. Continuous forward motion following the natural curve. Warm autumn palette with saturated reds and golds against cool water tones."},
        {"name": "birds", "prompt": "Cinematic drone pushes forward over a misty lake as a flock of birds lifts off from the water surface ahead. Camera dollies forward through the rising flock. Water droplets scatter from the birds' wings catching golden backlight in the foreground. Mist swirls from the disturbance. Continuous forward tracking through the moment. Warm golden backlighting, crushed shadows, anamorphic bokeh on water droplets."},
        {"name": "sunrise_lake", "prompt": "Cinematic drone rises above the lake as golden sunrise floods across the landscape. Camera cranes upward continuously. Morning mist burns away gradually revealing mountain scenery reflected in the still water expanding below. The world opens up with altitude. Smooth continuous vertical tracking. Teal-and-orange color grading, warm golden sunrise tones, cool blue water shadows, cinematic grain."},
    ],
    "waterfall_journey": [
        {"name": "source", "prompt": "Aerial drone tracks forward following a mountain stream from its source high in misty peaks. Camera dollies forward along the stream course as crystal clear water tumbles over mossy rocks in the foreground below. Mountain fog drifts past at camera level. Continuous forward motion downstream. Cool blue-teal water tones with rich emerald green moss. Volumetric mist, soft diffused mountain light."},
        {"name": "cascade", "prompt": "Cinematic drone tracks forward alongside a series of cascading waterfalls stepping down through lush jungle terrain. Camera dollies forward and slightly downward following the water's descent. White water crashes over each rock tier in the foreground while the next cascade reveals below. Continuous forward-and-down tracking motion. Rich saturated greens with cool white water highlights, mist spray in foreground."},
        {"name": "main_fall", "prompt": "Cinematic drone rises slowly in front of an enormous waterfall plunging into a deep blue pool. Camera cranes upward continuously from pool level. Foreground mist and spray fill the lens while the full massive scale of the falls reveals as the camera climbs. A rainbow arcs through the spray in the mid-ground. Smooth continuous vertical tracking. Cool blues and whites with prismatic iridescent mist highlights."},
        {"name": "pool", "prompt": "Aerial drone glides forward over a crystal clear turquoise pool at the base of a waterfall. Camera dollies forward over the transparent water surface. Sunlight penetrates deep revealing smooth stones and rippling sand on the bottom. Fine waterfall mist drifts through the foreground creating soft diffusion. Continuous smooth forward tracking. Vibrant turquoise with prismatic highlights, warm golden sun penetration through water."},
        {"name": "river_out", "prompt": "Aerial drone tracks forward following the river flowing away from the waterfall through a peaceful widening valley. Camera dollies forward along the calming water as it settles from turbulent to smooth. Golden sunset light floods the valley from ahead. Continuous forward journey-completion motion. Warm golden color grading, crushed shadows, amber highlights. Transition from cool blue water to warm golden resolution."},
    ],
    "countryside": [
        {"name": "dawn_fields", "prompt": "Cinematic drone glides forward low over endless golden wheat fields at dawn. Camera dollies forward over the uniform golden rows stretching to the horizon. Morning white mist hovers just above the crop in the foreground. Long dramatic shadows stretch across the landscape from rising sun. Continuous smooth forward tracking at low altitude. Warm earth tones with enhanced grain texture, golden rim light on wheat tips."},
        {"name": "rolling_hills", "prompt": "Aerial drone flies forward over lush green rolling hills and patchwork farmland. Camera dollies forward over the undulating landscape. Stone walls and hedgerows create geometric patterns below in the mid-ground. Warm golden hour sidelight rakes across the textured green surface. Continuous smooth forward tracking. Vibrant saturated greens and golds with high contrast, pastoral depth and scale."},
        {"name": "winding_road", "prompt": "Aerial drone tracks forward following a narrow winding country road through emerald green hills. Camera dollies along the road below as it curves between ancient oak trees. Dappled sunlight filters through the canopy creating moving light patterns on the road surface. Continuous forward motion following the path curves. Rich greens with warm golden dappled highlights, depth through tree canopy parallax."},
        {"name": "village", "prompt": "Cinematic drone approaches and descends toward a picturesque countryside village with stone cottages nestled in a green valley. Camera dollies forward and downward simultaneously. Golden afternoon light illuminates the warm stone buildings ahead while green fields frame the approach. Continuous smooth forward-and-down approach revealing village detail. Warm medieval palette with enhanced stone textures, pastoral atmosphere."},
        {"name": "sunset_fields", "prompt": "Cinematic drone rises above the countryside at golden sunset. Camera cranes upward continuously revealing the entire landscape glowing warm orange below. Long shadows stretch across green fields and stone walls creating geometric patterns. The horizon expands with altitude. Smooth continuous vertical tracking. Warm golden-amber grading, crushed deep shadows, cinematic grain. Intimate pastoral to epic landscape transition."},
    ],
    "urban_night": [
        {"name": "skyline_approach", "prompt": "Cinematic drone approaches a glowing city skyline at night. Camera dollies forward toward the towers of light. Millions of windows reflect in glass facades while neon signs and warm street lights create a carpet of color below. Continuous forward approach with buildings growing in frame. Teal-and-orange color grading, enhanced light bloom, anamorphic bokeh on distant city lights."},
        {"name": "highway_flow", "prompt": "Aerial drone tracks forward above a busy highway at night. Camera dollies steadily forward over flowing red tail-light and white headlight trails streaking below in time-lapse motion. City skyline glows in the warm background while dark road cuts through the foreground. Continuous forward motion above the traffic flow. Desaturated with enhanced light trail streaks, high contrast dark road against bright city glow."},
        {"name": "neon_streets", "prompt": "FPV drone races forward low through neon-lit city streets at night. Camera dollies fast between glowing colorful signs on both sides. Rain-slicked road surface reflects neon pink and blue creating mirror effect in the foreground. Foreground motion blur from speed and proximity. Continuous fast forward motion through the urban canyon. Vibrant saturated neon color palette, wet reflection highlights, cinematic grain."},
        {"name": "rooftop_orbit", "prompt": "Cinematic drone orbits slowly around a rooftop at night. Camera performs a continuous wide circular arc with the entire city sprawling below to the horizon twinkling with countless lights. Warm interior glow from rooftop windows in the foreground. Stars visible above the city light pollution. Continuous smooth orbital motion. Warm rooftop highlights against cool blue city panorama, anamorphic bokeh on distant lights."},
        {"name": "city_dawn", "prompt": "Cinematic drone rises above the city as first golden dawn light appears on the eastern horizon. Camera cranes upward continuously. City lights still glow below in cool blue while warm golden sunrise floods across the upper skyline creating a dramatic color split. Smooth continuous vertical tracking. Teal-and-orange color grading, transitional moment between night blue and dawn gold, cinematic grain."},
    ],
    "fog_weather": [
        {"name": "fog_rollin", "prompt": "Aerial drone glides forward above a dense fog bank rolling over coastal hills. Camera dollies steadily forward over the white mist blanket. Dark treetops poke through the fog like islands creating scattered vertical elements. Diffused golden sunlight through the fog creates an ethereal warm glow above the mist surface. Continuous smooth forward motion. Soft monochromatic palette with warm golden highlights where light penetrates."},
        {"name": "valley_mist", "prompt": "Cinematic drone pushes forward through a misty mountain valley at dawn. Camera dollies through layered mist between dark ridges. Visibility shifts between clear passages and obscured fog banks creating a rhythm of reveal and concealment. Golden light filters through from behind distant ridges. Continuous smooth forward tracking. Desaturated with subtle warm shifts, volumetric mist layers, atmospheric depth."},
        {"name": "storm_approach", "prompt": "FPV drone races forward toward massive dark storm clouds building on the distant horizon. Camera dollies fast at low altitude over green fields bending in growing wind. Lightning flickers inside the towering cloud formations ahead. Foreground grass motion blur from speed. Continuous fast forward approach toward the wall of weather. High contrast dramatic sky, dark clouds against bright foreground, electric tension."},
        {"name": "rain_clearing", "prompt": "Cinematic drone rises through a break in heavy rain clouds. Camera cranes upward continuously through the narrowing gap. Dark storm clouds part on both sides revealing brilliant blue sky and warm golden sunlight above. Water droplets catch light as prismatic foreground sparkle. Smooth continuous vertical tracking upward through the opening. Dramatic tonal transition from dark storm to bright hopeful warm light."},
        {"name": "mist_sunrise", "prompt": "Aerial drone glides forward over landscape emerging from morning mist as golden sunrise burns it away. Camera dollies forward through dissolving fog. Lush green valleys and sparkling rivers reveal progressively ahead as mist evaporates in the warm light. Continuous forward discovery motion. Warm golden earth tones, transitional atmosphere from cool misty mystery to warm clear morning, enhanced green saturation."},
    ],
    "architecture": [
        {"name": "castle_reveal", "prompt": "Cinematic drone approaches a medieval castle on a hilltop being revealed through lifting morning mist. Camera dollies forward continuously as ancient stone walls and towers grow larger and more detailed through the clearing fog. Golden sunrise backlights the mist creating volumetric god rays around the fortress silhouette. Smooth forward approach. Warm medieval palette with enhanced stone textures, atmospheric mist diffusion."},
        {"name": "bridge_flyunder", "prompt": "FPV drone races forward under a dramatic suspension bridge spanning a wide river. Camera dollies fast between massive cables and steel structural beams on both sides creating strong parallax depth. Water rushes far below while the bridge structure frames the exit point ahead. Continuous fast forward motion through the architectural corridor. Cool metallic tones with enhanced structural detail and contrast."},
        {"name": "monument_spiral", "prompt": "Aerial drone ascends in a continuous spiral around a grand historical cathedral or monument. Camera orbits upward steadily revealing intricate carved architectural details at each level. Dramatic warm sidelight emphasizes stone texture and depth of carved elements. Continuous combined orbital and vertical ascending motion. Classic warm palette, enhanced stone detail, Gothic or Renaissance architectural depth revealed progressively."},
        {"name": "ruins_discovery", "prompt": "Cinematic drone pushes forward low over ancient stone ruins overgrown with jungle vegetation. Camera dollies steadily forward over crumbling walls and moss-covered columns. Golden shafts of light pierce through the canopy above creating volumetric beams illuminating the ruins. Continuous forward exploration motion. Rich saturated greens against warm sandstone, archaeological discovery atmosphere, dappled light and shadow."},
        {"name": "lighthouse_orbit", "prompt": "Aerial drone orbits around a dramatic lighthouse on rocky cliffs at golden sunset. Camera performs a continuous wide circular arc. Enormous waves crash against the foreground rocks below while warm golden light paints the lighthouse tower and surrounding cliffs orange. Continuous smooth orbital motion. Teal ocean below against warm orange cliff and sky, anamorphic bokeh, epic coastal drama, cinematic grain."},
    ],
    "ice_adventure": [
        {"name": "glacial_dive", "prompt": "FPV cinematic drone descends over a glacial valley moraine. Camera dollies forward while banking gently and losing altitude toward a dark meltwater channel. Snow-streaked rocky terrain blurs in the foreground while dark jagged mountain peaks fill the distant horizon. Pre-dawn blue hour with no visible sun, soft diffused ambient skylight. Deep teal-and-black grading, crushed shadows, continuous forward-and-down motion. Foreground motion blur from low altitude."},
        {"name": "snow_race", "prompt": "FPV racing drone flies forward at extreme low altitude over a flat snow-covered field. Camera banks aggressively side to side with a dutch angle tilting the horizon. Ground snow texture streaks past the lens in the foreground. Sparse bare trees stand on the distant horizon as vertical elements. Twilight blue hour under heavy overcast sky with even diffused lighting. Deep teal-and-cyan grading, desaturated icy snow, continuous fast forward motion."},
        {"name": "lone_tree", "prompt": "FPV cinematic drone flies forward at low altitude along a snow-covered single-track road. Camera locks toward a single tall conifer tree standing at the vanishing point ahead. Snow-covered rolling hills slope away on both sides creating depth lines. Distant mountains silhouette the horizon. Deep blue hour after sunset with a hint of warmer ambient on the horizon. Teal sky over desaturated bluish snow, continuous steady forward motion."},
        {"name": "lake_skim", "prompt": "FPV cinematic drone skims forward at extreme low altitude over a calm alpine lake surface. Camera angles slightly down catching water texture and subtle surface ripples in the immediate foreground. Two tiny kayakers visible in the middle distance provide human scale. Snow-capped mountain ridges silhouette the horizon. Overcast twilight with soft diffused lighting. Deep teal water and muted cyan sky, continuous steady forward motion."},
        {"name": "cliff_plunge", "prompt": "FPV cinematic drone dives vertically off the edge of a massive cliff. Camera plummets downward along the layered rock cliff face filling the frame. A row of tiny silhouetted people standing on the cliff rim above provide dramatic scale reference. Deep shadowed cliff texture dominates with teal twilight sky at the top edge. Blue hour overcast lighting. Deep teal-and-black grading, continuous fast vertical downward motion with strong motion blur."},
    ],
}


def assemble_drone_journey(clip_paths, output_path, crossfade_dur=None):
    if crossfade_dur is None: crossfade_dur = CROSSFADE_DURATION
    if not clip_paths: raise RuntimeError("No clips to assemble")
    if len(clip_paths) == 1:
        import shutil; shutil.copy2(clip_paths[0], output_path); return output_path
    durations = []
    for cp in clip_paths:
        dur = _get_duration(cp); durations.append(dur)
        print(f"  [Crossfade] Clip duration: {dur:.2f}s")
    inputs = []
    for p in clip_paths: inputs.extend(["-i", p])
    filters = []; offset = durations[0] - crossfade_dur; prev = "0:v"
    for i in range(1, len(clip_paths)):
        out_label = f"v{i}" if i < len(clip_paths) - 1 else "outv"
        filters.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={crossfade_dur}:offset={offset:.2f}[{out_label}]")
        prev = out_label
        if i < len(clip_paths) - 1: offset += durations[i] - crossfade_dur
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[outv]", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", output_path]
    print(f"  [Crossfade] Assembling {len(clip_paths)} clips with {crossfade_dur}s crossfade...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [Crossfade] FFmpeg error: {result.stderr[-500:]}"); return _simple_concat(clip_paths, output_path)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    total_dur = sum(durations) - crossfade_dur * (len(clip_paths) - 1)
    print(f"  [Crossfade] Done: {size_mb:.1f} MB | ~{total_dur:.0f}s"); return output_path

def _get_duration(video_path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def _simple_concat(clip_paths, output_path):
    cf = str(Path(output_path).parent / "concat_fallback.txt")
    with open(cf, "w") as f:
        for p in clip_paths: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cf, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", output_path], check=True, capture_output=True)
    return output_path


def _submit_job(prompt, num_frames=81, height=832, width=480, upscale=None):
    if upscale is None: upscale = UPSCALE_FACTOR
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
    payload = {"input": {"prompt": prompt, "num_frames": num_frames, "height": height, "width": width, "guidance_scale": 7.5, "fps": 16, "upscale": upscale}}
    resp = requests.post(f"{RUNPOD_API_URL}/run", headers=headers, json=payload, timeout=30)
    resp.raise_for_status(); return resp.json().get("id")

def _poll_result(job_id, timeout=1800, interval=10):
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{RUNPOD_API_URL}/status/{job_id}", headers=headers, timeout=30)
        resp.raise_for_status(); data = resp.json(); status = data.get("status")
        if status == "COMPLETED": return data.get("output", {})
        elif status in ("FAILED", "CANCELLED"): raise RuntimeError(f"RunPod job {job_id} {status}: {data}")
        print(f"  [RunPod] {status}... ({int(deadline - time.time())}s remaining)"); time.sleep(interval)
    raise TimeoutError(f"RunPod job {job_id} timed out after {timeout}s")

def fetch_runpod_clip(prompt, scene_idx, output_path, timeout=1800):
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID: raise RuntimeError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")
    print(f"  [RunPod] Submitting: {prompt[:60]}..."); job_id = _submit_job(prompt)
    print(f"  [RunPod] Job {job_id} submitted"); result = _poll_result(job_id, timeout=timeout)
    video_b64 = result.get("video_base64", "")
    if not video_b64: raise RuntimeError(f"RunPod returned empty video for job {job_id}")
    with open(output_path, "wb") as f: f.write(base64.b64decode(video_b64))
    print(f"  [RunPod] Clip saved: {Path(output_path).stat().st_size / 1024:.0f} KB"); return output_path

def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1):
    """Generate all clips IN PARALLEL -- submit all jobs at once, poll simultaneously."""
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
        import random; theme_name = random.choice(list(DRONE_THEMES.keys())); theme = DRONE_THEMES[theme_name]
    print(f"  [RunPod] Drone journey: {theme_name} ({len(theme)} scenes) -- PARALLEL + {UPSCALE_FACTOR}x UPSCALE")

    jobs = []
    for i, scene in enumerate(theme):
        clip_path = os.path.join(output_dir, f"drone_{i}_{scene['name']}.mp4")
        try:
            print(f"  [RunPod] Submitting [{i+1}/{len(theme)}]: {scene['prompt'][:55]}...")
            job_id = _submit_job(scene["prompt"])
            jobs.append({"job_id": job_id, "scene": scene, "clip_path": clip_path, "index": i, "done": False, "result": None})
            print(f"  [RunPod] Job {job_id} submitted")
        except Exception as e:
            print(f"  [RunPod] Submit failed for {scene['name']}: {e}")
    if not jobs:
        return []
    print(f"  [RunPod] All {len(jobs)} jobs submitted -- polling in parallel...")

    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + 1800
    while time.time() < deadline:
        all_done = True
        for job in jobs:
            if job["done"]:
                continue
            all_done = False
            try:
                resp = requests.get(f"{RUNPOD_API_URL}/status/{job['job_id']}", headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status == "COMPLETED":
                    job["done"] = True
                    job["result"] = data.get("output", {})
                    print(f"  [RunPod] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} COMPLETED")
                elif status in ("FAILED", "CANCELLED"):
                    job["done"] = True
                    print(f"  [RunPod] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} {status}")
            except Exception as e:
                print(f"  [RunPod] Poll error for {job['scene']['name']}: {e}")
        if all_done:
            break
        pending = sum(1 for j in jobs if not j["done"])
        remaining = int(deadline - time.time())
        print(f"  [RunPod] {pending} clips generating... ({remaining}s remaining)")
        time.sleep(10)

    clips = []
    for job in jobs:
        if job["result"] and job["result"].get("video_base64"):
            with open(job["clip_path"], "wb") as f:
                f.write(base64.b64decode(job["result"]["video_base64"]))
            size_kb = Path(job["clip_path"]).stat().st_size / 1024
            print(f"  [RunPod] Saved {job['scene']['name']}: {size_kb:.0f} KB")
            clips.append((job["clip_path"], job["scene"]["name"]))
        elif not job["done"]:
            print(f"  [RunPod] {job['scene']['name']} timed out")
        else:
            print(f"  [RunPod] {job['scene']['name']} failed (no video)")
    print(f"  [RunPod] {len(clips)}/{len(jobs)} clips generated successfully")
    return clips

def render_drone_journey(theme_name, output_dir, output_path, github_run_number=1):
    clips = fetch_drone_journey_clips(theme_name, output_dir, github_run_number)
    if not clips: raise RuntimeError(f"No clips generated for theme '{theme_name}'")
    return assemble_drone_journey([cp for cp, _ in clips], output_path)

def get_theme_for_run(github_run_number):
    return list(DRONE_THEMES.keys())[github_run_number % len(DRONE_THEMES)]

def reset_used_prompts():
    global _used_prompts; _used_prompts = set()
