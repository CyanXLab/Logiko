#!/usr/bin/env python3
"""
Logiko Corpus Generator v3 (Logiko v2.0 spec)
================================================
Changes from v2:
  - Use v2 language rules: cu for yes/no, I-a for possessive
  - past/fut for tense (avoid aux stacking)
  - Fuse suffixes: teachist, learnej, cutil, teauc
  - Cleaner semantic collocation
  - Multi-turn Q&A mixed in (15%)
"""
import random
import os
import sys
import json

# =========================================================================
# Vocabulary with semantic classes
# =========================================================================
NOUN_CLASSES = {
    "weather": ["sun", "moon", "star", "sky", "cloud", "rain", "snow", "wind", "storm", "mist", "frost", "weather", "thunder"],
    "landscape": ["mountain", "sea", "river", "lake", "forest", "desert", "island", "field", "cave", "hill", "valley", "cliff", "ground"],
    "plant": ["tree", "wood", "grass", "leaf", "flower", "root", "fruit", "seed", "branch", "trunk", "bark", "moss", "fern"],
    "animal": ["dog", "cat", "horse", "cow", "pig", "sheep", "goat", "chicken", "duck", "rabbit", "bird", "fish", "snake", "frog", "lion", "tiger", "bear", "wolf", "fox", "deer", "monkey", "elephant", "whale", "dolphin", "eagle", "owl", "ant", "bee"],
    "person": ["person", "man", "woman", "child", "boy", "girl", "friend", "family", "father", "mother", "son", "brother", "sister", "teachist", "student", "doctor", "farmer", "artist", "scientist"],
    "body": ["head", "hair", "face", "eye", "ear", "nose", "mouth", "tooth", "tongue", "neck", "shoulder", "arm", "hand", "finger", "chest", "leg", "foot", "heart", "blood", "skin", "bone", "brain", "muscle", "stomach", "lung"],
    "food": ["bread", "rice", "noodle", "meat", "fish", "egg", "milk", "cheese", "butter", "soup", "cake", "honey", "sugar", "tea", "coffee", "juice", "wine", "beer", "apple", "orange", "banana", "grape", "pear", "peach", "lemon", "melon", "berry", "nut", "bean", "corn", "potato", "tomato", "onion", "garlic"],
    "object": ["book", "pen", "table", "chair", "bed", "door", "window", "key", "lock", "box", "bag", "basket", "bottle", "cup", "plate", "bowl", "pot", "knife", "fork", "spoon", "tool", "hammer", "nail", "rope", "wheel", "engine", "machine", "computer", "phone", "screen", "lamp", "candle", "bell", "mirror", "comb", "brush", "towel", "soap", "umbrella", "shoe", "hat", "shirt", "coat", "dress", "pants", "glove", "sock"],
    "building": ["house", "room", "cookej", "learnej", "healej", "temple", "market", "bank", "factory", "library", "museum", "tower", "bridge", "road", "path", "garden", "farm"],
    "time": ["day", "night", "morning", "evening", "noon", "today", "yesterday", "tomorrow", "week", "month", "year", "season", "spring", "summer", "autumn", "winter", "hour", "minute", "second", "century"],
    "abstract": ["life", "death", "love", "hate", "hope", "fear", "joy", "sadness", "anger", "wisdom", "knowledge", "truth", "false", "freedom", "justice", "peace", "war", "power", "time", "history", "future", "music", "art", "science", "magic", "dream"],
    "color": ["red", "blue", "green", "yellow", "white", "black", "color"],
    "substance": ["water", "fire", "air", "stone", "sand", "earth", "metal", "iron", "gold", "silver", "copper", "salt", "oil", "glass", "paper", "cloth", "wood", "coal", "ice"],
}

VERB_CLASSES = {
    "motion": ["go", "come", "arrive", "leave", "return", "enter", "travel", "visit", "walk", "run", "jump", "climb", "swim", "fly", "ride", "drive", "fall", "rise", "move", "stop", "turn", "follow", "lead"],
    "body_action": ["eat", "drink", "sleep", "wake", "breathe", "see", "look", "hear", "smell", "taste", "touch", "feel", "speak", "talk", "say", "tell", "sing", "dance", "laugh", "cry", "smile", "sit", "stand", "lie"],
    "mental": ["think", "know", "believe", "remember", "forget", "understand", "learn", "study", "guess", "imagine", "dream", "want", "need", "choose", "decide", "plan", "hope", "fear", "wonder", "notice", "focus", "ignore", "realize", "expect", "predict"],
    "communication": ["ask", "answer", "tell", "say", "speak", "talk", "read", "write", "explain", "describe", "show", "prove", "promise", "advise", "warn", "thank", "forgive", "blame", "praise", "agree", "refuse", "accept"],
    "creation": ["make", "build", "create", "draw", "paint", "carve", "sew", "knit", "weave", "cook", "bake", "plant", "grow", "decorate", "repair", "fix"],
    "destruction": ["break", "cut", "tear", "burn", "destroy", "kill", "drop", "crash"],
    "exchange": ["give", "take", "send", "bring", "receive", "buy", "sell", "pay", "cost", "share", "trade", "own"],
    "state": ["be", "have", "become", "seem", "exist", "happen", "stay", "remain", "change"],
    "nature_verb": ["rain", "snow", "blow", "shine", "freeze", "melt", "boil", "burn", "grow", "wither", "bloom", "flow"],
    "work": ["work", "do", "make", "use", "help", "try", "begin", "finish", "continue", "manage", "organize"],
}

ADJ_CLASSES = {
    "size": ["big", "small", "long", "short", "tall", "wide", "narrow", "thick", "thin"],
    "color_a": ["red", "blue", "green", "yellow", "white", "black", "brown", "gray"],
    "age": ["young", "old", "new", "ancient", "modern", "recent"],
    "quality": ["good", "bad", "beautiful", "ugly", "clean", "dirty", "safe", "dangerous", "useful", "useless", "important", "simple", "complex", "easy", "difficult", "right", "wrong", "true", "false", "real", "fake"],
    "feeling": ["happy", "sad", "angry", "calm", "excited", "bored", "tired", "fresh", "strong", "weak", "healthy", "sick"],
    "temperature": ["hot", "cold", "warm", "cool"],
    "speed": ["fast", "slow", "quick", "sudden"],
    "quantity": ["many", "much", "few", "little", "more", "less", "full", "empty", "rich", "poor"],
    "property": ["hard", "soft", "sharp", "dull", "smooth", "rough", "dry", "wet", "heavy", "light", "bright", "dark", "deep", "high", "low"],
    "taste": ["sweet", "sour", "bitter", "spicy", "salty", "delicious"],
}

ADV_BASE = ["fast", "slow", "good", "easy", "happy", "careful", "quick", "sudden",
            "quiet", "loud", "soft", "well", "safe", "true", "correct", "early", "late", "soon"]

PRONOUNS = ["I", "we", "you", "ta", "ta-many"]
DEMO = ["this", "that"]
QUANT = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "many", "few", "some", "all", "several", "every"]
# v2: use past/fut for tense, cu for yes/no
TIME_ADVS = ["today", "yesterday", "tomorrow", "now", "soon", "later", "always", "never",
             "often", "sometimes", "early", "late", "past", "fut"]
AUX = ["did", "is", "will", "have"]  # still used, but past/fut preferred for complex
MODALS = ["can", "must", "should", "may"]
CONNECTORS = ["and", "or", "but", "because", "so", "therefore", "although", "if", "when"]
PREP_PLACE = ["in", "on", "at", "under", "over", "between", "among", "through", "across", "along", "around", "near", "far"]
PREP_TIME = ["before", "after", "during", "since", "until"]
PREP_DIR = ["to", "from", "toward", "into"]
PREP_OTHER = ["with", "by", "for", "of", "about", "without", "against"]
QWORDS = ["what", "who", "where", "when", "why", "how", "how-many"]

SUBJ_VERB_COMPAT = {
    "person": ["body_action", "mental", "communication", "creation", "motion", "exchange", "work", "state"],
    "animal": ["body_action", "motion", "state"],
    "weather": ["nature_verb", "state"],
    "landscape": ["state"],
    "plant": ["nature_verb", "state"],
    "object": ["state"],
    "building": ["state"],
    "body": ["body_action", "state"],
    "food": ["state"],
    "abstract": ["state"],
    "color": ["state"],
    "substance": ["state", "nature_verb"],
    "time": ["state"],
}

VERB_OBJ_COMPAT = {
    "eat": ["food"],
    "drink": ["food"],
    "read": ["object"],
    "write": ["object"],
    "buy": ["object", "food"],
    "sell": ["object", "food"],
    "build": ["building", "object"],
    "plant": ["plant"],
    "grow": ["plant", "food"],
    "cook": ["food"],
    "see": ["animal", "person", "object", "landscape", "plant", "weather", "building"],
    "hear": ["abstract", "animal", "person"],
    "know": ["abstract", "person"],
    "love": ["person", "animal", "abstract", "food"],
    "give": ["object", "food"],
    "take": ["object", "food"],
    "make": ["object", "food"],
    "use": ["object"],
    "open": ["object", "building"],
    "close": ["object", "building"],
    "wash": ["object", "body", "food"],
    "wear": ["object"],
    "ride": ["animal"],
    "feed": ["animal", "person"],
    "teach": ["person"],
    "help": ["person", "animal"],
    "visit": ["person", "building", "landscape"],
    "find": ["object", "person", "animal", "abstract"],
    "want": ["object", "food", "abstract"],
    "need": ["object", "food", "abstract"],
}


def adj(w): return w + "-a"
def adv(w): return w + "-e"
def neg(w): return "mal-" + w


def pick_noun(cls=None):
    if cls and cls in NOUN_CLASSES:
        return random.choice(NOUN_CLASSES[cls]), cls
    cls = random.choice(list(NOUN_CLASSES.keys()))
    return random.choice(NOUN_CLASSES[cls]), cls


def pick_verb(cls=None):
    if cls and cls in VERB_CLASSES:
        return random.choice(VERB_CLASSES[cls]), cls
    cls = random.choice(list(VERB_CLASSES.keys()))
    return random.choice(VERB_CLASSES[cls]), cls


def pick_adj(cls=None):
    if cls and cls in ADJ_CLASSES:
        return random.choice(ADJ_CLASSES[cls])
    cls = random.choice(list(ADJ_CLASSES.keys()))
    return random.choice(ADJ_CLASSES[cls])


def noun_phrase(noun_class=None, allow_adj=True):
    parts = []
    if random.random() < 0.4:
        parts.append(random.choice(DEMO))
    if random.random() < 0.6:
        parts.append(random.choice(QUANT))
    if allow_adj:
        n_adj = random.randint(0, 2)
        for _ in range(n_adj):
            if noun_class == "person" and random.random() < 0.5:
                a = pick_adj("feeling") if random.random() < 0.5 else pick_adj("age")
            elif noun_class == "food" and random.random() < 0.5:
                a = pick_adj("taste") if random.random() < 0.5 else pick_adj("temperature")
            elif noun_class == "weather" and random.random() < 0.5:
                a = pick_adj("temperature")
            else:
                a = pick_adj("size") if random.random() < 0.4 else pick_adj("quality")
            if random.random() < 0.15:
                a = neg(a)
            parts.append(adj(a))
    if noun_class:
        n = random.choice(NOUN_CLASSES[noun_class])
    else:
        cls = random.choice(list(NOUN_CLASSES.keys()))
        n = random.choice(NOUN_CLASSES[cls])
        noun_class = cls
    parts.append(n)
    return " ".join(parts), noun_class


def verb_phrase(subj_class=None):
    parts = []
    if random.random() < 0.3:
        parts.append(random.choice(TIME_ADVS))
    r = random.random()
    if r < 0.20:
        # v2: prefer past/fut for clear time reference
        time_word = random.choice(["past", "fut", "did", "will"])
        parts.append(time_word)
    elif r < 0.35:
        parts.append("not")
        if random.random() < 0.4:
            parts.append(random.choice(AUX))
    elif r < 0.45:
        parts.append(random.choice(MODALS))
    if random.random() < 0.4:
        parts.append(adv(random.choice(ADV_BASE)))

    if subj_class and subj_class in SUBJ_VERB_COMPAT:
        compat_verb_classes = SUBJ_VERB_COMPAT[subj_class]
        verb_cls = random.choice(compat_verb_classes)
        v = random.choice(VERB_CLASSES[verb_cls])
    else:
        v = random.choice(VERB_CLASSES["state"] + VERB_CLASSES["motion"] + VERB_CLASSES["body_action"])
    parts.append(v)

    if random.random() < 0.7:
        if v in VERB_OBJ_COMPAT:
            obj_cls = random.choice(VERB_OBJ_COMPAT[v])
            obj_phrase, _ = noun_phrase(obj_cls)
        else:
            obj_phrase, _ = noun_phrase()
        parts.append(obj_phrase)
    return " ".join(parts), v


def sentence_simple():
    subj_cls = random.choice(list(NOUN_CLASSES.keys()))
    if subj_cls in ("person", "animal"):
        subj = random.choice(PRONOUNS) if random.random() < 0.4 else random.choice(NOUN_CLASSES[subj_cls])
    else:
        subj = random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"{subj} {vp}."


def sentence_with_prep():
    s = sentence_simple().rstrip(".")
    if random.random() < 0.6:
        prep = random.choice(PREP_PLACE + PREP_DIR)
        obj_cls = random.choice(["building", "landscape", "object"])
    else:
        prep = random.choice(PREP_TIME)
        obj_cls = "time"
    obj_phrase, _ = noun_phrase(obj_cls)
    return f"{s} {prep} {obj_phrase}."


def sentence_question_wh():
    q = random.choice(QWORDS)
    subj_cls = random.choice(["person", "animal", "object", "food"])
    subj = random.choice(PRONOUNS) if subj_cls in ("person", "animal") and random.random() < 0.5 else random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"{q} {subj} {vp}?"


def sentence_question_yn():
    """v2: use cu instead of if"""
    subj_cls = random.choice(["person", "animal", "object"])
    subj = random.choice(PRONOUNS) if subj_cls == "person" and random.random() < 0.5 else random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"cu {subj} {vp}?"


def sentence_compound():
    s1 = sentence_simple().rstrip(".")
    conn = random.choice(CONNECTORS)
    s2 = sentence_simple().rstrip(".")
    return f"{s1}, {conn} {s2.lower()}."


def sentence_complex_cause():
    s1 = sentence_simple().rstrip(".")
    s2 = sentence_simple().rstrip(".")
    return f"{s1}, because {s2.lower()}."


def sentence_passive():
    v = random.choice(list(VERB_OBJ_COMPAT.keys()))
    obj_cls = random.choice(VERB_OBJ_COMPAT[v])
    subj_phrase, _ = noun_phrase(obj_cls)
    agent = random.choice(PRONOUNS + ["that person", "this person"])
    # v2: use past for past passive
    return f"{subj_phrase} past be {v} by {agent}."


def sentence_compare():
    a1 = pick_adj("size") if random.random() < 0.5 else pick_adj("quality")
    s1 = random.choice(PRONOUNS)
    s2 = random.choice(PRONOUNS)
    return f"{s1} more {adj(a1)} than {s2}."


def sentence_superlative():
    a1 = pick_adj("size") if random.random() < 0.5 else pick_adj("quality")
    s1 = random.choice(PRONOUNS)
    return f"{s1} most {adj(a1)} of all person."


def sentence_possessive():
    """v2: use I-a, ta-a etc."""
    pron = random.choice(PRONOUNS)
    a = pick_adj("size") if random.random() < 0.4 else pick_adj("quality")
    n_cls = random.choice(["object", "animal", "person"])
    n = random.choice(NOUN_CLASSES[n_cls])
    return f"{pron}-a {adj(a)} {n} be here."


SENTENCE_GEN = [
    (sentence_simple, 0.25),
    (sentence_with_prep, 0.18),
    (sentence_question_wh, 0.08),
    (sentence_question_yn, 0.07),
    (sentence_compound, 0.15),
    (sentence_complex_cause, 0.10),
    (sentence_passive, 0.05),
    (sentence_compare, 0.05),
    (sentence_superlative, 0.04),
    (sentence_possessive, 0.03),
]


def gen_sentence():
    r = random.random()
    acc = 0
    for gen, p in SENTENCE_GEN:
        acc += p
        if r < acc:
            return gen()
    return sentence_simple()


# =========================================================================
# Math (deterministic, always correct)
# =========================================================================
def gen_math_add():
    a = random.randint(1, 99); b = random.randint(1, 99); r = a + b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we add {a} and {b}, result be {r}. {a} {cmp} big-a than {b}."

def gen_math_subtract():
    a = random.randint(1, 99); b = random.randint(1, 99); r = a - b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we subtract {b} from {a}, result be {r}. {a} {cmp} big-a than {b}."

def gen_math_multiply():
    a = random.randint(2, 12); b = random.randint(2, 12); r = a * b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we multiply {a} by {b}, result be {r}. {a} {cmp} big-a than {b}."

def gen_math_divide():
    b = random.randint(2, 12); q = random.randint(1, 12); a = b * q
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we divide {a} by {b}, result be {q}. {a} {cmp} big-a than {b}."

def gen_math_paragraph():
    n = random.randint(5, 10)
    gens = [gen_math_add, gen_math_subtract, gen_math_multiply, gen_math_divide]
    return " ".join(random.choice(gens)() for _ in range(n))


# =========================================================================
# Knowledge paragraphs (factual, with v2 language)
# =========================================================================
KNOWLEDGE_TEMPLATES = [
    ("water", [
        "water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree.",
        "all life need water for live. without water, life die.",
        "river and sea have much water. sea water be salt, so person can not drink ta.",
        "water cover most of earth surface. ta be essential-a for all living thing.",
        "ice be solid-a water. steam be gas-a water. both be same substance.",
    ]),
    ("fire", [
        "fire be hot-a and bright-a. ta need air for burn.",
        "fire can burn wood, paper, cloth. ta can not burn water or stone.",
        "person use fire for cook food and warm body in winter.",
        "if fire not have air, ta will die. so person can put out fire by cover ta.",
        "fire be one chemical-a reaction that release heat and light.",
    ]),
    ("sun", [
        "sun be one star. ta be big-a and hot-a.",
        "sun give light and warm to earth. without sun, life not possible.",
        "sun rise in east, and set in west. ta make day bright-a.",
        "all plant need sun-light for grow. ta make food through photosynthesis.",
        "sun be center of we-a solar system. earth orbit around ta.",
    ]),
    ("moon", [
        "moon go around earth. ta take about one month for one orbit.",
        "moon shine, but moon not have own light. ta reflect sun light.",
        "moon have four phase: new, first-quarter, full, last-quarter.",
        "person can see moon in night. sometimes ta be visible in day too.",
        "moon be smaller than earth. ta have no air and no water.",
    ]),
    ("tree", [
        "tree be one plant. ta have root, trunk, branch, leaf.",
        "root take water from ground. leaf take sun-light and make food.",
        "tree can live many year. some tree live over thousand year.",
        "tree give fruit, wood, and shadow. ta be very useful-a for person.",
        "forest be place with many tree. ta be home for many animal.",
    ]),
    ("dog", [
        "dog be one animal. ta be loyal-a friend of person.",
        "dog have four leg, one tail, and sharp-a tooth.",
        "dog can run fast-a and smell well-e. ta hear better-e than person.",
        "dog eat meat, but can also eat rice and vegetable.",
        "person often keep dog as friend. ta can help hunt, guard, and guide.",
    ]),
    ("person", [
        "person be one animal, but person can think and speak.",
        "person have head, body, two arm, two leg. ta walk on two leg.",
        "person brain can think, learn, remember, create. ta be very complex-a.",
        "person can make tool, build house, grow food. ta change earth.",
        "person live in family, society, country. ta have culture and language.",
    ]),
    ("food", [
        "food give energy to body. person need food for live.",
        "bread, rice, meat, vegetable be common-a food in many culture.",
        "fruit have sweet-a taste and be good-a for health.",
        "if food be raw, person must cook ta before eat.",
        "if food be old or dirty, ta can make person sick. so person should check food before eat.",
    ]),
    ("season", [
        "year have four season: spring, summer, autumn, winter.",
        "in spring, plant grow and flower bloom. weather become warm-a.",
        "in summer, weather be hot-a and day be long-a. person often swim.",
        "in autumn, leaf become yellow and fall. weather become cool-a.",
        "in winter, weather be cold-a and snow fall in some place.",
    ]),
    ("book", [
        "book be many paper with word, bind together.",
        "person write book for record knowledge, tell story, express idea.",
        "person read book for learn and enjoy. ta be source of knowledge.",
        "library be place with many book. person can borrow book from library.",
        "before book exist, person tell story by speak. now person can also read book in computer.",
    ]),
    ("computer", [
        "computer be one machine that can calculate and process data.",
        "computer have screen, keyboard, memory, processor.",
        "person use computer for work, study, play, and communicate.",
        "computer can connect to other computer through network. internet be global-a network.",
        "program be instruction for computer. ta be write in programming language.",
    ]),
    ("music", [
        "music be art of sound. ta use rhythm, melody, and harmony.",
        "person make music with voice or instrument.",
        "common-a instrument: piano, guitar, drum, flute, violin.",
        "music can make person feel happy, sad, calm, or excited.",
        "every culture have own music style. ta be universal-a language.",
    ]),
    ("mountain", [
        "mountain be big-a land-form, higher than hill.",
        "mountain top often have snow, even in summer, because ta be cold-a up there.",
        "highest mountain in world be everest. ta be over eight thousand meter high.",
        "river often begin from mountain. snow melt and form stream.",
        "mountain have many tree, animal, and mineral. ta be rich-a in resource.",
    ]),
    ("sea", [
        "sea be big-a body of salt water. ta cover most of earth surface.",
        "many fish, whale, dolphin, shark live in sea.",
        "river flow into sea. water cycle through evaporation and rain.",
        "person can swim, sail, and fish in sea. ta provide food for many person.",
        "sea water be salt, so person can not drink ta. ta be dangerous if drink.",
    ]),
    ("time", [
        "time flow from past to future. ta never stop.",
        "person can not stop or return time. ta be one-way.",
        "one day have twenty-four hour. one hour have sixty minute.",
        "one minute have sixty second. one year have about three hundred sixty-five day.",
        "person measure time with clock, watch, and calendar.",
    ]),
    ("teachist", [
        "teachist be one person who teach. ta work in learnej.",
        "teachist help student learn knowledge and skill.",
        "good-a teachist be patient-a, kind-a, and wise-a.",
        "teachist explain concept, give exercise, and correct mistake.",
        "teachist shape future by educate next generation.",
    ]),
    ("learnej", [
        "learnej be one place where person learn. ta be also call school.",
        "in learnej, teachist teach student. student study various-a subject.",
        "learnej have classroom, library, and sometimes play-a ground.",
        "person usually start learnej at young-a age, around six year old.",
        "learnej be important-a for society because ta spread knowledge.",
    ]),
    ("cutil", [
        "cutil be one tool for cut. ta be also call knife.",
        "cutil have sharp-a blade and handle. person use ta in cookej.",
        "person should use cutil careful-e, because ta can hurt.",
        "different-a cutil exist for different-a purpose: meat, vegetable, bread.",
        "if cutil be dull, person should sharpen ta. sharp-a cutil be safer than dull-a one.",
    ]),
    ("cookej", [
        "cookej be one place where person cook food. ta be also call kitchen.",
        "cookej have stove, oven, sink, and refrigerator.",
        "person prepare meal in cookej. ta be center of home.",
        "cookej should be clean-a, because food be prepare there.",
        "some family gather in cookej for talk while cook.",
    ]),
]


def gen_knowledge_paragraph():
    topic, facts = random.choice(KNOWLEDGE_TEMPLATES)
    first = facts[0]
    rest = facts[1:]
    random.shuffle(rest)
    selected = [first] + rest[:random.randint(3, len(rest))]
    return " ".join(selected)


def gen_dialogue(n_turns=8):
    lines = []
    speakers = ["A", "B"]
    for i in range(n_turns):
        spk = speakers[i % 2]
        if i % 2 == 0:
            sent = random.choice([sentence_question_wh(), sentence_question_yn()])
        else:
            sent = sentence_simple()
            if random.random() < 0.4:
                sent2 = sentence_simple()
                sent = sent + " " + sent2.lower()
        lines.append(f"{spk}: {sent}")
    return "\n".join(lines)


def gen_narrative(n_sentences=15):
    sentences = []
    openings = [
        "once, in one small-a village,",
        "long-time-ago, in one big-a forest,",
        "yesterday, in one city,",
        "one morning,",
        "in ancient time,",
        "in one far-a place,",
    ]
    opening = random.choice(openings)
    first_sent = sentence_simple().lower()
    sentences.append(f"{opening} {first_sent}")
    for _ in range(n_sentences - 2):
        sentences.append(gen_sentence())
    endings = [
        "so, story end here.",
        "and ta-many live happy-a life after.",
        "this be end of story.",
        "from that day, ta-many learn one important-a lesson.",
        "story teach we: be careful and kind.",
    ]
    sentences.append(random.choice(endings))
    return " ".join(sentences)


def gen_instruction(n_steps=6):
    topics = [
        ("cook", "food", ["wash food", "cut food", "put food in pot", "boil water", "add salt", "cook ten minute", "serve in plate"]),
        ("build", "house", ["find flat-a ground", "dig hole for base", "put stone in hole", "build wall with wood", "put roof on wall", "make door and window"]),
        ("plant", "tree", ["dig hole in ground", "put tree in hole", "cover root with earth", "water tree", "wait many day", "tree will grow"]),
        ("write", "letter", ["take one paper", "take one pen", "write greeting", "write you-a message", "write you-a name", "put letter in envelope"]),
        ("learn", "logiko", ["read spec first", "memorize core root", "learn suffix and prefix", "read example text", "write simple-a sentence", "speak with other person"]),
    ]
    verb, obj_cls, steps = random.choice(topics)
    intro = f"if you want {verb} {obj_cls}, you can follow this method:"
    step_strs = []
    for i, step in enumerate(steps):
        step_strs.append(f"step {i+1}: {step}.")
    return intro + " " + " ".join(step_strs)


def gen_news(n_sentences=10):
    places = ["city", "village", "country", "town", "capital"]
    place = random.choice(places)
    sentences = [f"news from {place}:"]
    for _ in range(n_sentences):
        sent = random.choice([
            sentence_simple,
            sentence_with_prep,
            sentence_passive,
            sentence_complex_cause,
        ])()
        sentences.append(sent)
    return " ".join(sentences)


def gen_poem(n_lines=6):
    lines = []
    themes = ["nature", "love", "time", "life"]
    theme = random.choice(themes)
    if theme == "nature":
        nouns_pool = NOUN_CLASSES["landscape"] + NOUN_CLASSES["weather"] + NOUN_CLASSES["plant"]
    elif theme == "love":
        nouns_pool = NOUN_CLASSES["person"] + NOUN_CLASSES["abstract"]
    elif theme == "time":
        nouns_pool = NOUN_CLASSES["time"]
    else:
        nouns_pool = NOUN_CLASSES["abstract"]
    adjs_pool = ADJ_CLASSES["quality"] + ADJ_CLASSES["feeling"]
    verbs_pool = VERB_CLASSES["state"] + VERB_CLASSES["nature_verb"]
    for _ in range(n_lines):
        a = random.choice(adjs_pool)
        n1 = random.choice(nouns_pool)
        v = random.choice(verbs_pool)
        n2 = random.choice(nouns_pool)
        lines.append(f"{adj(a)} {n1} {v} {n2}.")
    return "\n".join(lines)


def gen_qa_paragraph():
    """Generate a multi-turn Q&A paragraph from SFT data."""
    sft_path = "/home/z/my-project/logiko/sft_data.jsonl"
    if not os.path.exists(sft_path):
        return gen_knowledge_paragraph()
    with open(sft_path) as f:
        lines = f.readlines()
    # Pick a random multi-turn example
    candidates = []
    for line in lines:
        ex = json.loads(line)
        if len(ex["turns"]) >= 2:
            candidates.append(ex)
    if not candidates:
        return gen_knowledge_paragraph()
    ex = random.choice(candidates)
    out = []
    for q, a in ex["turns"]:
        out.append(f"Q: {q}")
        out.append(f"A: {a}")
    return "\n".join(out)


GENRES = [
    (gen_dialogue, 0.10),
    (gen_narrative, 0.15),
    (gen_knowledge_paragraph, 0.20),
    (gen_instruction, 0.08),
    (gen_news, 0.07),
    (gen_poem, 0.05),
    (gen_math_paragraph, 0.20),
    (gen_qa_paragraph, 0.15),
]


def gen_paragraph():
    r = random.random()
    acc = 0
    for gen, p in GENRES:
        acc += p
        if r < acc:
            return gen()
    return gen_narrative()


def gen_corpus(target_bytes=5 * 1024 * 1024):
    out = []
    total = 0
    para_id = 0
    while total < target_bytes:
        para = gen_paragraph()
        out.append(f"### paragraph {para_id}")
        out.append(para)
        out.append("")
        para_id += 1
        total += len(para) + 30
        if para_id % 500 == 0:
            print(f"  ... {total/1024:.1f} KB / {target_bytes/1024:.1f} KB", file=sys.stderr)
    return "\n".join(out)


def main():
    random.seed(42)
    target = 5 * 1024 * 1024
    print(f"Generating Logiko v2 corpus (~{target/1024/1024:.1f} MB)...")
    corpus = gen_corpus(target)
    out_path = "/home/z/my-project/download/logiko_corpus.txt"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(corpus)
    actual = os.path.getsize(out_path)
    print(f"Done. Wrote {actual} bytes ({actual/1024/1024:.2f} MB) to {out_path}")
    n_chars = len(corpus)
    n_words = len(corpus.split())
    n_lines = corpus.count("\n") + 1
    print(f"Stats: {n_chars} chars, {n_words} words, {n_lines} lines")


if __name__ == "__main__":
    main()
