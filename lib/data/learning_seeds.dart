// lib/services/learning_seeds.dart

class LearningSeed {
  final String id;
  final String title;
  final String overview;
  final List<String> examples;
  final List<String> strategies;
  final List<String> tags;
  const LearningSeed({
    required this.id,
    required this.title,
    required this.overview,
    required this.examples,
    required this.strategies,
    this.tags = const [],
  });
}

/// Edit this list to add/remove topics (no UI button needed).
/// TIP: Keep `id` stable; it’s used to merge with saved data.
const List<LearningSeed> kLearningSeeds = [
  LearningSeed(
    id: 'what-is-anxiety',
    title: 'What is anxiety?',
    overview:
    'Anxiety is your body’s built-in alarm system, designed to prepare you to face potential threats. '
        'Mild anxiety can sharpen focus and motivate action, but it becomes a problem when the alarm misfires—'
        'showing up too often, too intensely, or in situations that aren’t actually dangerous. '
        'You might notice physical changes (racing heart, shaky hands, stomach discomfort), mental patterns '
        '(catastrophic “what ifs”), and behavioral shifts (avoidance, seeking reassurance). Understanding anxiety as a '
        'normal, protective system that has become over-sensitive helps you respond with skills rather than fear.',
    examples: [
      'Racing thoughts before meetings or social events',
      'Tension, stomach discomfort, restlessness',
      'Avoiding situations that might trigger worry',
    ],
    strategies: [
      'Box breathing: 4-in, 4-hold, 4-out, 4-hold (2–3 minutes)',
      'Label the worry (“I’m noticing anxious thoughts”)',
      'Tiny exposures: approach the situation in small steps',
      'Reduce caffeine; keep consistent sleep/wake times',
    ],
    tags: ['anxiety', 'basics'],
  ),
  LearningSeed(
    id: 'panic-attacks',
    title: 'What are panic attacks?',
    overview:
    'Panic attacks are sudden surges of intense fear or discomfort that peak within minutes. '
        'Common symptoms include a pounding heart, shortness of breath, dizziness, tingling, or a sense of unreality. '
        'They often feel catastrophic (“I’m dying” or “I’m going to faint”), but they are not dangerous. '
        'Panic attacks are driven by a feedback loop: you notice a sensation, interpret it as a threat, and the body releases '
        'more adrenaline—intensifying sensations. Learning to ride the wave and reinterpret symptoms breaks the cycle.',
    examples: [
      'Feeling “I’m dying” or “I’m going to faint”',
      'Chest tightness or dizziness in a store or on transport',
      'Fear of future attacks leading to avoidance',
    ],
    strategies: [
      'Grounding: name 5 things you see, 4 feel, 3 hear, 2 smell, 1 taste',
      'Slow exhales; let the wave rise and fall (usually <10 minutes)',
      'Rewrite catastrophic thoughts after the wave passes',
    ],
    tags: ['anxiety', 'panic'],
  ),
  LearningSeed(
    id: 'depression-vs-low-mood',
    title: 'Low mood vs. depression',
    overview:
    'Everyone has low days; depression is different. It is a cluster of symptoms—low mood, loss of interest, changes in sleep '
        'and appetite, fatigue, and self-critical thinking—occurring most days for at least two weeks, and it interferes with life. '
        'Depression narrows your world: energy shrinks, motivation drops, and things you used to enjoy feel far away. '
        'Treatments focus on gently re-expanding your life (behavioral activation), rebalancing thoughts, and restoring body rhythms.',
    examples: [
      'Loss of interest in usual activities',
      'Early-morning awakening, low energy',
      'Self-critical rumination',
    ],
    strategies: [
      'Behavioral activation: schedule 1 small, meaningful action daily',
      'Sunlight and movement (even 5–10 min helps)',
      'Talk with someone; consider professional support if persistent',
    ],
    tags: ['mood'],
  ),
  LearningSeed(
    id: 'intrusive-thoughts',
    title: 'Intrusive thoughts',
    overview:
    'Intrusive thoughts are unwanted thoughts or images that seem to pop in from nowhere. They’re common—especially under stress. '
        'Struggling with them (arguing, suppressing, seeking reassurance) paradoxically makes them stickier. '
        'The skill is to notice, label, and allow the thought to be present without giving it power, while you refocus on what matters.',
    examples: [
      'Disturbing “what if” images',
      'Fear of acting on a thought (very unlikely)',
      'Checking or seeking reassurance repeatedly',
    ],
    strategies: [
      'Name it: “That’s an intrusive thought”',
      'Allow, don’t fight; refocus on a chosen task',
      'Limit reassurance rituals; try scheduled worry time',
    ],
    tags: ['ocd', 'anxiety'],
  ),
  LearningSeed(
    id: 'sleep-hygiene',
    title: 'Sleep hygiene (better sleep)',
    overview:
    'Good sleep depends on consistent circadian cues and a calm pre-sleep routine. '
        'Irregular schedules, bright evening light, caffeine, and worry in bed all train the brain to stay alert at night. '
        'Aim to strengthen the bed-sleep association and let sleep pressure build naturally.',
    examples: [
      'Irregular bed/wake times',
      'Screen time in bed; clock-watching',
      'Late caffeine or heavy meals',
    ],
    strategies: [
      'Same wake time daily; dim lights 1 hour before bed',
      'Bed = sleep & intimacy only; get up if awake >20 minutes',
      'Caffeine cutoff ~8 hours before bed',
    ],
    tags: ['sleep'],
  ),

  // ===== 20 MORE SEEDS =====
  LearningSeed(
    id: 'social-anxiety',
    title: 'Social anxiety',
    overview:
    'Social anxiety involves a strong fear of being judged, embarrassed, or rejected. '
        'You may scan for flaws, replay conversations, or avoid situations. This keeps fear alive. '
        'Gradual exposure—testing your predictions while behaving more like the person you want to be—reduces anxiety over time.',
    examples: [
      'Avoiding speaking up or meeting new people',
      'Replay of “awkward” moments for hours',
      'Safety behaviors (over-preparing, hiding, avoiding eye contact)',
    ],
    strategies: [
      'Create a graded exposure ladder and practice',
      'Focus attention outward (on the task) instead of self-monitoring',
      'Use compassionate self-talk to counter harsh inner critique',
    ],
    tags: ['anxiety', 'social'],
  ),
  LearningSeed(
    id: 'health-anxiety',
    title: 'Health anxiety',
    overview:
    'Health anxiety is excessive worry about illness despite reassurance or normal tests. '
        'The cycle is driven by hyper-monitoring body sensations and repeated checking or Googling. '
        'Reducing reassurance and using balanced, evidence-based reappraisal weaken the loop.',
    examples: [
      'Repeatedly checking pulse, moles, or blood pressure',
      'Doctor-shopping, constant searching online',
      'Catastrophic interpretations of benign symptoms',
    ],
    strategies: [
      'Delay checking/reassurance with a “worry period”',
      'Write balanced explanations for sensations',
      'Keep normal activity levels to disconfirm danger',
    ],
    tags: ['anxiety', 'health'],
  ),
  LearningSeed(
    id: 'generalized-anxiety',
    title: 'Generalized anxiety (GAD)',
    overview:
    'GAD features persistent, hard-to-control worry about multiple life areas. '
        'Worry can feel productive but often leads to mental exhaustion and avoidance. '
        'Skills include postponing worry, challenging cognitive biases, and engaging in valued activities.',
    examples: [
      'Endless “what if” loops',
      'Trouble relaxing, irritability, poor sleep',
      'Difficulty concentrating due to worry',
    ],
    strategies: [
      'Schedule daily 15-minute “worry time”; postpone outside it',
      'Record evidence for/against feared outcomes',
      'Practice relaxation paired with action steps',
    ],
    tags: ['anxiety'],
  ),
  LearningSeed(
    id: 'ocd-basics',
    title: 'OCD: basics',
    overview:
    'Obsessive-Compulsive Disorder includes intrusive obsessions (thoughts, images, urges) and compulsions (behaviors or mental acts) '
        'performed to reduce distress. Compulsions bring short relief but reinforce the cycle. Exposure and Response Prevention (ERP) '
        'helps by facing triggers while resisting rituals, allowing anxiety to decline naturally.',
    examples: [
      'Contamination fears → washing rituals',
      'Doubt (“Did I lock the door?”) → checking',
      'Harm or moral obsessions → mental neutralizing',
    ],
    strategies: [
      'Create an ERP plan with a graded hierarchy',
      'Practice tolerating uncertainty without rituals',
      'Reduce reassurance and tracking compulsions',
    ],
    tags: ['ocd', 'anxiety'],
  ),
  LearningSeed(
    id: 'ptsd-overview',
    title: 'Trauma & PTSD',
    overview:
    'Post-traumatic stress can follow threatening or overwhelming events. Symptoms may include intrusive memories, avoidance, '
        'hypervigilance, and negative mood shifts. Recovery involves re-establishing safety, processing memories, rebuilding routines, '
        'and reconnecting with supportive people and activities.',
    examples: [
      'Nightmares, flashbacks, startle sensitivity',
      'Avoiding reminders or places',
      'Feeling detached, guilt, or shame',
    ],
    strategies: [
      'Grounding and present-moment skills',
      'Trauma-focused therapy (e.g., TF-CBT, EMDR) if available',
      'Gentle re-engagement with meaningful activities',
    ],
    tags: ['trauma'],
  ),
  LearningSeed(
    id: 'bipolar-basics',
    title: 'Bipolar: basics',
    overview:
    'Bipolar spectrum disorders involve mood episodes that swing between depression and periods of elevated or irritable mood '
        '(hypomania/mania) with increased energy, reduced need for sleep, and impulsivity. Routines, sleep stability, and professional care '
        'are key pillars, alongside education for you and close supports.',
    examples: [
      'Days of minimal sleep with racing ideas',
      'Risky spending or impulsive decisions',
      'Crashes into low mood after highs',
    ],
    strategies: [
      'Keep a daily routine and sleep-wake regularity',
      'Monitor early warning signs; build a plan',
      'Coordinate with a clinician for ongoing care',
    ],
    tags: ['mood'],
  ),
  LearningSeed(
    id: 'adhd-adults',
    title: 'ADHD in adults',
    overview:
    'ADHD affects attention regulation, impulse control, and time management. It’s not a lack of effort—it’s a difference in how the brain '
        'prioritizes signals. External structure (timers, lists, visual cues) and body-doubling can dramatically improve follow-through.',
    examples: [
      'Starting many tasks, finishing few',
      'Time blindness; frequent late starts',
      'Difficulty organizing or prioritizing',
    ],
    strategies: [
      'Break tasks into tiny steps with visible checklists',
      'Use timers (Pomodoro) and body-doubling',
      'Design frictionless environments (tools visible & ready)',
    ],
    tags: ['adhd'],
  ),
  LearningSeed(
    id: 'burnout',
    title: 'Burnout',
    overview:
    'Burnout is emotional exhaustion, cynicism, and reduced effectiveness due to chronic stress. '
        'It often blends overwork with under-recovery. Recovery is not just rest; it’s rebalancing demands, restoring meaning, and improving boundaries.',
    examples: [
      'Numbness or irritability about work',
      'Feeling ineffective despite effort',
      'Dreading the next day',
    ],
    strategies: [
      'Audit demands vs. recovery; increase micro-rest',
      'Clarify values; re-align tasks with meaning',
      'Negotiate boundaries and supports where possible',
    ],
    tags: ['stress', 'work'],
  ),
  LearningSeed(
    id: 'grief',
    title: 'Grief',
    overview:
    'Grief is a natural response to loss. It ebbs and flows—waves can feel strong, then quieter. '
        'There’s no single timeline. Integrating the loss involves oscillating between mourning and restoration: feeling and doing.',
    examples: [
      'Sudden waves triggered by reminders',
      'Guilt about “moving on” or laughing',
      'Sleep or appetite changes',
    ],
    strategies: [
      'Allow waves; schedule islands of restoration',
      'Share memories with safe people',
      'Rituals that honor the relationship',
    ],
    tags: ['grief'],
  ),
  LearningSeed(
    id: 'perfectionism',
    title: 'Perfectionism',
    overview:
    'Perfectionism pairs high standards with harsh self-criticism and fear of mistakes. Paradoxically, it can reduce output and joy. '
        'Shifting to “excellent and human” standards and practicing imperfect action increase growth and well-being.',
    examples: [
      'Procrastinating until conditions are “just right”',
      'Ruminating over tiny flaws',
      'All-or-nothing self-worth',
    ],
    strategies: [
      'Define “good enough” explicitly before starting',
      'Ship small imperfect versions on purpose',
      'Practice self-compassion after errors',
    ],
    tags: ['thinking', 'performance'],
  ),
  LearningSeed(
    id: 'rumination',
    title: 'Rumination',
    overview:
    'Rumination is repetitive, unproductive thinking about problems or regrets. It feels like problem-solving but rarely ends in action. '
        'Training the mind to notice and shift—toward concrete next steps or to the present—shrinks rumination time.',
    examples: [
      'Replaying conversations at night',
      'Looping on “why” something happened',
      'Feeling stuck despite lots of thinking',
    ],
    strategies: [
      'Name it and set a 2-minute timer to choose an action',
      'Redirect attention to a values task or sensory anchor',
      'Schedule specific “thinking time” to contain it',
    ],
    tags: ['thinking'],
  ),
  LearningSeed(
    id: 'self-compassion',
    title: 'Self-compassion',
    overview:
    'Self-compassion treats yourself as you would a good friend—acknowledging pain, recognizing common humanity, and responding kindly. '
        'It reduces shame and supports healthy change better than self-criticism does.',
    examples: [
      'Harsh inner voice after mistakes',
      'Feeling uniquely broken',
      'Avoiding help due to shame',
    ],
    strategies: [
      'Write a kind note to yourself from a friend’s voice',
      'Use a self-compassion break (mindfulness, common humanity, kindness)',
      'Pair accountability with warmth instead of judgment',
    ],
    tags: ['skills'],
  ),
  LearningSeed(
    id: 'boundaries',
    title: 'Boundaries',
    overview:
    'Boundaries are the rules you set for what you give and accept. Clear, calm boundaries reduce resentment and prevent burnout. '
        'They are about your choices—not controlling others.',
    examples: [
      'Saying yes while feeling “I can’t”',
      'Taking responsibility for others’ feelings',
      'Resentment that builds over time',
    ],
    strategies: [
      'Use short, kind, clear statements (“I’m not available Saturday”)',
      'Decide consequences you can control',
      'Practice tolerating guilt in service of values',
    ],
    tags: ['relationships'],
  ),
  LearningSeed(
    id: 'assertive-communication',
    title: 'Assertive communication',
    overview:
    'Assertiveness is direct, respectful expression of needs and limits. It sits between passivity and aggression and improves relationships over time.',
    examples: [
      'Hinting instead of asking',
      'Exploding after long silence',
      'People-pleasing that backfires',
    ],
    strategies: [
      'Use “I” statements and specific requests',
      'Validate others’ views without surrendering your own',
      'Rehearse key lines; keep a warm tone',
    ],
    tags: ['communication'],
  ),
  LearningSeed(
    id: 'substance-coping',
    title: 'Substances & coping',
    overview:
    'Alcohol and other substances can offer short-term relief but often worsen sleep, mood, and anxiety. '
        'If use is creeping up, building alternative coping plans and tracking triggers helps regain control.',
    examples: [
      'Needing alcohol to sleep or socialize',
      'Using after stress to “numb out”',
      'Trying to cut back but slipping',
    ],
    strategies: [
      'Plan “if-then” alternatives for high-risk times',
      'Track triggers; increase dose of healthy rewards',
      'Seek specialized support if needed',
    ],
    tags: ['habits'],
  ),
  LearningSeed(
    id: 'eating-habits',
    title: 'Eating patterns & mood',
    overview:
    'Nutrition influences energy, focus, and emotional balance. Irregular meals, extreme restriction, or binge cycles can destabilize mood. '
        'Gentle nutrition—regular meals, adequate protein, and flexible variety—supports mental health.',
    examples: [
      'Skipping breakfast then late overeating',
      'Rules that trigger guilt around food',
      'Mood swings tied to blood sugar dips',
    ],
    strategies: [
      'Regular meals/snacks every 3–4 hours',
      'Aim for balanced plates (protein, fiber, fats)',
      'Practice flexibility; reduce all-or-nothing rules',
    ],
    tags: ['habits', 'nutrition'],
  ),
  LearningSeed(
    id: 'movement',
    title: 'Movement for mental health',
    overview:
    'Movement improves sleep, attention, and mood via endorphins and inflammation pathways. The best plan is the one you’ll do consistently. '
        'Small, frequent bouts count—especially outdoors or with people.',
    examples: [
      'All-or-nothing exercise cycles',
      'Sedentary days with foggy focus',
      'Stress relief after short walks',
    ],
    strategies: [
      'Start with 5–10 minutes daily; stack to habits',
      'Pair movement with music, nature, or friends',
      'Track “mood after” to reinforce the loop',
    ],
    tags: ['habits', 'sleep'],
  ),
  LearningSeed(
    id: 'digital-overload',
    title: 'Digital overload',
    overview:
    'Constant notifications fragment attention and increase stress. Gentle digital boundaries restore depth, focus, and calm.',
    examples: [
      'Endless scrolling at night',
      'Compulsively checking messages',
      'Difficulty focusing on deep work',
    ],
    strategies: [
      'Batch notifications; use Do Not Disturb blocks',
      'Move tempting apps off the home screen',
      'Create phone-free wind-down time',
    ],
    tags: ['habits', 'focus'],
  ),
  LearningSeed(
    id: 'relationships-mental-health',
    title: 'Relationships & mental health',
    overview:
    'Supportive relationships buffer stress and protect against depression. Skills like validation, curiosity, and repair after conflict '
        'strengthen bonds and reduce anxiety.',
    examples: [
      'Talking past each other in conflict',
      'Loneliness despite contact',
      'Escalating criticism and defensiveness',
    ],
    strategies: [
      'Express needs early (soft starts)',
      'Practice reflective listening & validation',
      'Schedule regular connection rituals',
    ],
    tags: ['relationships'],
  ),
  LearningSeed(
    id: 'values-goals',
    title: 'Values & goals',
    overview:
    'Values are directions (like a compass); goals are steps. Clarifying values protects against avoidance and helps you choose meaningful actions '
        'even when emotions are strong.',
    examples: [
      'Stuck between options that all feel bad',
      'Acting from fear rather than purpose',
      'Losing track of what matters',
    ],
    strategies: [
      'Write top 5 values; name 1 tiny step per value',
      'Schedule value-based actions weekly',
      'Review progress with kindness, not perfectionism',
    ],
    tags: ['motivation'],
  ),
  LearningSeed(
    id: 'mindfulness-basics',
    title: 'Mindfulness basics',
    overview:
    'Mindfulness is present-moment awareness with openness and curiosity. It reduces reactivity and expands choice. '
        'Short, regular practice changes how you relate to thoughts and feelings.',
    examples: [
      'Auto-pilot reactions in stress',
      'Getting hooked by thoughts',
      'Difficulty noticing early signs of overwhelm',
    ],
    strategies: [
      '2–5 minute daily breath or body scan',
      'Informal practice: feel feet while walking',
      'Name thoughts as “thinking” and return attention',
    ],
    tags: ['skills'],
  ),
  LearningSeed(
    id: 'gratitude',
    title: 'Gratitude & positive emotion',
    overview:
    'Gratitude exercises shift attention toward resources and connection, broadening perspective and building resilience. '
        'This isn’t denial of difficulty; it’s training the mind to also register what’s going well.',
    examples: [
      'Negativity bias dominates your day',
      'Dismissing positive feedback',
      'Forgetting small wins quickly',
    ],
    strategies: [
      'Write 3 specific gratitudes nightly',
      'Savoring: linger 20–30 seconds on a pleasant moment',
      'Share appreciations aloud with someone',
    ],
    tags: ['skills', 'mood'],
  ),
  LearningSeed(
    id: 'time-management-stress',
    title: 'Time management & stress',
    overview:
    'Unclear priorities and hidden friction points create avoidable stress. Externalizing your plan and designing better environments '
        'reduce mental load and increase follow-through.',
    examples: [
      'Keeping plans in your head',
      'Losing track of tasks and deadlines',
      'Underestimating time (“planning fallacy”)',
    ],
    strategies: [
      'Single trusted list + calendar; review daily',
      'Time-block focused work and recovery',
      'Pre-decide start rituals for sticky tasks',
    ],
    tags: ['focus', 'work'],
  ),
  LearningSeed(
    id: 'financial-stress',
    title: 'Financial stress & mental health',
    overview:
    'Money stress activates threat systems and narrows thinking. Building clarity (even when numbers are tough) and small wins '
        'restores a sense of control and reduces anxiety.',
    examples: [
      'Avoiding bills or statements',
      'Impulse purchases to cope',
      'Conflict about money in relationships',
    ],
    strategies: [
      'Weekly money check-in with a simple dashboard',
      'Automate bills/savings to reduce decision fatigue',
      'Set tiny, realistic targets toward stability',
    ],
    tags: ['stress', 'practical'],
  ),
  LearningSeed(
    id: 'resilience',
    title: 'Resilience',
    overview:
    'Resilience grows from supportive relationships, flexible thinking, healthy routines, and purposeful action. '
        'It’s not about never struggling—it’s about recovering and adapting in ways aligned with your values.',
    examples: [
      'Feeling knocked down by setbacks',
      'Thinking “I can’t handle this”',
      'Losing routines during stress',
    ],
    strategies: [
      'Map supports; ask for specific help',
      'Reframe setbacks as experiments and feedback',
      'Keep core routines (sleep, movement, connection)',
    ],
    tags: ['skills', 'growth'],
  ),
];
