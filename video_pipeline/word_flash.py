"""
MindCore AI -- Word Flash Selection v1.0
==========================================
Shared by both male and female pipelines.
Fixes: apostrophe matching, expanded stopwords, expanded power words.

The analysis showed flashes landing on ISN'T, DOESN'T, ACTUALLY, SAID
instead of DISMISSED, FLINCH, HEARD, SERIOUSLY.

Two bugs fixed:
1. Apostrophes in contractions (ISN'T) didn't match stopword (isnt)
2. Common verbs/adverbs weren't in the stopword list
"""

# Words that should NEVER flash -- grammar, filler, common verbs
WORD_FLASH_STOPWORDS = {
    # articles, pronouns, prepositions, conjunctions
    'the','and','for','are','but','not','you','all','can','had','her','was',
    'one','our','out','get','has','him','his','how','its','may','new','now',
    'old','see','two','way','who','did','let','put','say','she','too','use',
    'a','i','in','is','it','if','do','an','so','at','be','by','no','or',
    'on','up','as','of','to','from','that','this','with','have','they',
    'what','when','your','will','been','were','just','than','then','them',
    'these','into','some','there','about','which','their','after','every',
    'where','would','could','should','still','going','really','never',
    'always','here','more','very','even','also','back','down','only',
    'look','come','want','give','most','know','take','think','good',
    'like','time','feel','make','right','both','each','much','well',
    # contractions (without apostrophe -- matching strips them)
    'dont','doesnt','didnt','wont','cant','its','youre','theyre',
    'were','im','thats','theres','heres','ive','youve','weve',
    'isnt','wasnt','arent','havent','hadnt','wouldnt','couldnt','shouldnt',
    'mustnt','whos','whats','wheres','hows','whys',
    # common verbs/adverbs that should never flash
    'actually','said','stopped','started','getting','being','having',
    'making','trying','saying','told','asked','thought','happened',
    'called','became','meant','kept','went','came','left','found',
    'turned','looked','looked','seems','maybe','almost','already',
    'finally','suddenly','slowly','probably','sometimes',
    # common nouns that aren't emotional
    'things','people','person','something','someone','anything',
    'everything','nothing','somewhere','nobody','everybody',
    'yourself','myself','himself','herself','themselves',
    'moment','around','inside','before','because','another',
    'morning','tonight','today','yesterday','tomorrow','years',
    'remember','understand','believe','suppose','imagine',
    # platform/app words that should never flash in emotional content
    'google','play','download','app','phone','screen',
}

# Words that SHOULD flash -- emotional weight, visceral, scroll-stopping
POWER_WORDS = {
    # core emotional states
    'broken','tired','alone','lost','numb','empty','heavy','dark','scared',
    'hurt','pain','shame','guilt','anger','grief','fear','doubt','silence',
    'hollow','drained','invisible','worthless','hopeless','desperate','trapped',
    'sober','healing','recovery','depression','anxiety','trauma','burnout',
    'relapse','exhausted','overwhelmed','suffocating','withdrawn',
    # verbs with emotional punch
    'fight','carry','hold','fall','rise','change','truth','real',
    'survive','breathe','pretend','mask','hide','quit','disappear',
    # identity/worth
    'enough','worthy','seen','heard','free','strong','silent',
    'soul','heart','weight','burden','purpose','missing','love',
    # -ing forms with emotional weight
    'pretending','performing','disappearing','shrinking','drowning','fading',
    'pleasing','hiding','carrying','protecting','managing','fixing',
    'crumbling','unraveling','surviving','enduring','aching','breaking',
    'choking','gasping','sinking','spinning','screaming','bleeding',
    # emotional nouns -- the words the analysis said SHOULD flash
    'dismissed','flinch','labels','hormones','stress','medication',
    'diagnosis','crisis','addiction','breakdown','panic','rage',
    'disconnect','abandon','reject','neglect','toxic','boundary',
    'trigger','flashback','nightmare','insomnia','surrender','collapse',
    'wound','depleted','difference','flaw','earned','rooms','wrong',
    'apologize','perception','rehearse','glass',
    # states that hit hard
    'shattered','crushed','destroyed','torn','raw','exposed',
    'vulnerable','powerless','helpless','voiceless','unseen','unheard',
    'forgotten','abandoned','ignored','minimized','betrayed',
}


def pick_power_word(words_in_chunk):
    """Select the best word to flash from a subtitle chunk.
    
    v1.0 fix: strips apostrophes before stopword matching so
    contractions like ISN'T correctly match stopword 'isnt'.
    Prioritises POWER_WORDS over longest-word fallback.
    """
    def clean(w):
        """Normalize a word for matching: lowercase, strip punctuation + apostrophes."""
        return w.strip().lower().rstrip(".,!?'\"").replace("'", "").replace("\u2019", "")
    
    candidates = [
        w for w in words_in_chunk
        if len(w["word"].strip()) > 2
        and clean(w["word"]) not in WORD_FLASH_STOPWORDS
        and w["word"].strip().replace("'", "").replace("\u2019", "").replace("-", "").isalpha()
    ]
    if not candidates:
        return None
    
    # First priority: words in POWER_WORDS
    power = [w for w in candidates if clean(w["word"]) in POWER_WORDS]
    if power:
        return power[0]["word"].strip().upper()
    
    # Fallback: longest remaining word (likely a meaningful noun)
    return max(candidates, key=lambda w: len(w["word"].strip()))["word"].strip().upper()
