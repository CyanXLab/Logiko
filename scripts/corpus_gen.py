#!/usr/bin/env python3
"""
Logiko Corpus Generator v2
===========================
Improvements over v1:
  1. Math problems use deterministic computation (always correct)
  2. Semantic collocation via word-class constraints
     (e.g., "weather" only combines with rain/snow/wind verbs;
     "person" only combines with embodied verbs)
  3. Knowledge paragraphs based on real-world templates
  4. More varied sentence structures
  5. Proper paragraph boundaries (###) and explicit doc-end markers
"""
import random
import os
import sys
import math

# =========================================================================
# Vocabulary (subset of spec.md, with semantic class tags)
# =========================================================================

# 名词按语义类分组
NOUN_CLASSES = {
    "weather": ["sun", "moon", "star", "sky", "cloud", "rain", "snow", "wind", "storm", "mist", "frost", "weather", "thunder"],
    "landscape": ["mountain", "sea", "river", "lake", "forest", "desert", "island", "field", "cave", "hill", "valley", "cliff", "ground"],
    "plant": ["tree", "wood", "grass", "leaf", "flower", "root", "fruit", "seed", "branch", "trunk", "bark", "moss", "mushroom", "fern"],
    "animal": ["dog", "cat", "horse", "cow", "pig", "sheep", "goat", "chicken", "duck", "rabbit", "bird", "fish", "snake", "frog", "lion", "tiger", "bear", "wolf", "fox", "deer", "monkey", "elephant", "whale", "dolphin", "eagle", "owl", "ant", "bee", "butterfly"],
    "person": ["person", "man", "woman", "child", "baby", "boy", "girl", "friend", "family", "father", "mother", "son", "daughter", "brother", "sister", "teacher", "student", "doctor", "farmer", "artist", "scientist"],
    "body": ["head", "hair", "face", "eye", "ear", "nose", "mouth", "tooth", "tongue", "neck", "shoulder", "arm", "hand", "finger", "chest", "leg", "foot", "heart", "blood", "skin", "bone", "brain", "muscle", "stomach", "lung"],
    "food": ["bread", "rice", "noodle", "meat", "fish", "egg", "milk", "cheese", "butter", "soup", "cake", "honey", "sugar", "tea", "coffee", "juice", "wine", "beer", "apple", "orange", "banana", "grape", "pear", "peach", "lemon", "melon", "berry", "nut", "bean", "corn", "potato", "tomato", "onion", "garlic"],
    "object": ["book", "pen", "table", "chair", "bed", "door", "window", "key", "lock", "box", "bag", "basket", "bottle", "cup", "plate", "bowl", "pot", "knife", "fork", "spoon", "tool", "hammer", "nail", "rope", "wheel", "engine", "machine", "computer", "phone", "screen", "lamp", "candle", "bell", "mirror", "comb", "brush", "towel", "soap", "umbrella", "shoe", "hat", "shirt", "coat", "dress", "pants", "glove", "sock"],
    "building": ["house", "room", "kitchen", "school", "hospital", "temple", "market", "bank", "factory", "library", "museum", "tower", "bridge", "road", "path", "garden", "farm"],
    "time": ["day", "night", "morning", "evening", "noon", "today", "yesterday", "tomorrow", "week", "month", "year", "season", "spring", "summer", "autumn", "winter", "hour", "minute", "second", "century"],
    "abstract": ["life", "death", "love", "hate", "hope", "fear", "joy", "sadness", "anger", "wisdom", "knowledge", "truth", "lie", "freedom", "justice", "peace", "war", "power", "time", "history", "future", "past", "music", "art", "science", "magic", "dream"],
    "color": ["red", "blue", "green", "yellow", "white", "black", "color"],
    "substance": ["water", "fire", "air", "stone", "sand", "earth", "metal", "iron", "gold", "silver", "copper", "salt", "oil", "glass", "paper", "cloth", "wood", "coal", "ice"],
}

# 动词按语义类分组
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

# 形容词按语义类分组
ADJ_CLASSES = {
    "size": ["big", "small", "long", "short", "tall", "wide", "narrow", "thick", "thin"],
    "color_a": ["red", "blue", "green", "yellow", "white", "black", "brown", "gray"],
    "age": ["young", "old", "new", "ancient", "modern", "recent"],
    "quality": ["good", "bad", "beautiful", "ugly", "clean", "dirty", "safe", "dangerous", "useful", "useless", "important", "simple", "complex", "easy", "difficult", "right", "wrong", "true", "false", "real", "fake"],
    "feeling": ["happy", "sad", "angry", "calm", "excited", "bored", "tired", "fresh", "strong", "weak", "healthy", "sick"],
    "temperature": ["hot", "cold", "warm", "cool"],
    "speed": ["fast", "slow", "quick", "sudden"],
    "quantity": ["many", "much", "few", "little", "more", "less", "full", "empty", "rich", "poor"],
    "property": ["hard", "soft", "sharp", "dull", "smooth", "rough", "dry", "wet", "heavy", "light", "bright", "dark", "deep", "shallow", "high", "low"],
    "taste": ["sweet", "sour", "bitter", "spicy", "salty", "delicious"],
}

# 副词基础词根（加 -e）
ADV_BASE = ["fast", "slow", "good", "easy", "happy", "careful", "quick", "sudden",
            "quiet", "loud", "soft", "well", "safe", "true", "correct", "early", "late", "now", "soon"]

PRONOUNS = ["I", "we", "you", "ta", "ta-many"]
DEMO = ["this", "that"]
QUANT = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "many", "few", "some", "all", "several", "every"]
AUX = ["did", "is", "will", "have"]
MODALS = ["can", "must", "should", "may"]
CONNECTORS = ["and", "or", "but", "because", "so", "therefore", "although", "if", "when"]
PREP_PLACE = ["in", "on", "at", "under", "over", "between", "among", "through", "across", "along", "around", "near", "far"]
PREP_TIME = ["before", "after", "during", "since", "until"]
PREP_DIR = ["to", "from", "toward", "into", "out"]
PREP_OTHER = ["with", "by", "for", "of", "about", "without", "against"]
QWORDS = ["what", "who", "where", "when", "why", "how", "how-many"]

# =========================================================================
# Semantic collocation: which verbs can apply to which noun classes
# =========================================================================
# 给定主语的 noun_class，可选的动词类
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

# 给定动词的 noun_class，可选的宾语类
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


def adj(w):
    return w + "-a"


def adv(w):
    return w + "-e"


def neg(w):
    return "mal-" + w


def pick_noun(class_filter=None):
    """Pick a noun, optionally restricted to a class."""
    if class_filter and class_filter in NOUN_CLASSES:
        return random.choice(NOUN_CLASSES[class_filter])
    # 随机类
    cls = random.choice(list(NOUN_CLASSES.keys()))
    return random.choice(NOUN_CLASSES[cls]), cls


def pick_verb(class_filter=None):
    if class_filter and class_filter in VERB_CLASSES:
        return random.choice(VERB_CLASSES[class_filter])
    cls = random.choice(list(VERB_CLASSES.keys()))
    return random.choice(VERB_CLASSES[cls]), cls


def pick_adj(class_filter=None):
    if class_filter and class_filter in ADJ_CLASSES:
        return random.choice(ADJ_CLASSES[class_filter])
    cls = random.choice(list(ADJ_CLASSES.keys()))
    return random.choice(ADJ_CLASSES[cls])


# =========================================================================
# Phrase generators with semantic coherence
# =========================================================================

def noun_phrase(noun_class=None, allow_adj=True):
    """[指示] + [数量] + [形容词]* + [名词]"""
    parts = []
    if random.random() < 0.4:
        parts.append(random.choice(DEMO))
    if random.random() < 0.6:
        parts.append(random.choice(QUANT))
    if allow_adj:
        n_adj = random.randint(0, 2)
        for _ in range(n_adj):
            # 优先选与名词类相关的形容词
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
        # 随机类
        cls = random.choice(list(NOUN_CLASSES.keys()))
        n = random.choice(NOUN_CLASSES[cls])
        noun_class = cls
    parts.append(n)
    return " ".join(parts), noun_class


def verb_phrase(subj_class=None):
    """[时间] + [助] + [副词]* + [动词] + [宾语?]"""
    parts = []
    if random.random() < 0.3:
        time_words = ["today", "yesterday", "tomorrow", "now", "soon", "later", "always", "never", "often", "sometimes"]
        parts.append(random.choice(time_words))
    r = random.random()
    if r < 0.25:
        parts.append(random.choice(AUX))
    elif r < 0.4:
        parts.append("not")
        if random.random() < 0.4:
            parts.append(random.choice(AUX))
    elif r < 0.5:
        parts.append(random.choice(MODALS))
    if random.random() < 0.4:
        parts.append(adv(random.choice(ADV_BASE)))

    # 选动词
    if subj_class and subj_class in SUBJ_VERB_COMPAT:
        compat_verb_classes = SUBJ_VERB_COMPAT[subj_class]
        verb_cls = random.choice(compat_verb_classes)
        v = random.choice(VERB_CLASSES[verb_cls])
    else:
        v = random.choice(VERB_CLASSES["state"] + VERB_CLASSES["motion"] + VERB_CLASSES["body_action"])
        verb_cls = "state"
    parts.append(v)

    # 宾语
    if random.random() < 0.7:
        # 选合适的宾语类
        if v in VERB_OBJ_COMPAT:
            obj_cls = random.choice(VERB_OBJ_COMPAT[v])
            obj_phrase, _ = noun_phrase(obj_cls)
        else:
            obj_phrase, _ = noun_phrase()
        parts.append(obj_phrase)
    return " ".join(parts), v


def sentence_simple():
    """SVO with semantic coherence"""
    subj_cls = random.choice(list(NOUN_CLASSES.keys()))
    if subj_cls in ("person", "animal"):
        subj = random.choice(PRONOUNS) if random.random() < 0.4 else random.choice(NOUN_CLASSES[subj_cls])
    else:
        subj = random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"{subj} {vp}."


def sentence_with_prep():
    s = sentence_simple().rstrip(".")
    # 选一个合适的介词
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
    subj_cls = random.choice(["person", "animal", "object"])
    subj = random.choice(PRONOUNS) if subj_cls == "person" and random.random() < 0.5 else random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"If {subj} {vp}?"


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
    # 选合适的宾语作为主语
    v = random.choice(list(VERB_OBJ_COMPAT.keys()))
    obj_cls = random.choice(VERB_OBJ_COMPAT[v])
    subj_phrase, _ = noun_phrase(obj_cls)
    agent = random.choice(PRONOUNS + ["that person", "this person"])
    return f"{subj_phrase} did be {v} by {agent}."


def sentence_compare():
    a1 = pick_adj("size") if random.random() < 0.5 else pick_adj("quality")
    s1 = random.choice(PRONOUNS)
    s2 = random.choice(PRONOUNS)
    return f"{s1} more {adj(a1)} than {s2}."


def sentence_superlative():
    a1 = pick_adj("size") if random.random() < 0.5 else pick_adj("quality")
    s1 = random.choice(PRONOUNS)
    return f"{s1} most {adj(a1)} of all person."


SENTENCE_GEN = [
    (sentence_simple, 0.30),
    (sentence_with_prep, 0.20),
    (sentence_question_wh, 0.08),
    (sentence_question_yn, 0.07),
    (sentence_compound, 0.15),
    (sentence_complex_cause, 0.10),
    (sentence_passive, 0.05),
    (sentence_compare, 0.03),
    (sentence_superlative, 0.02),
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
# Math generators (deterministic, always correct)
# =========================================================================

def gen_math_add():
    a = random.randint(1, 99)
    b = random.randint(1, 99)
    r = a + b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we add {a} and {b}, result be {r}. {a} {cmp} big-a than {b}."


def gen_math_subtract():
    a = random.randint(1, 99)
    b = random.randint(1, 99)
    r = a - b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we subtract {b} from {a}, result be {r}. {a} {cmp} big-a than {b}."


def gen_math_multiply():
    a = random.randint(2, 12)
    b = random.randint(2, 12)
    r = a * b
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we multiply {a} by {b}, result be {r}. {a} {cmp} big-a than {b}."


def gen_math_divide():
    # 整除
    b = random.randint(2, 12)
    q = random.randint(1, 12)
    a = b * q
    cmp = "more" if a > b else ("less" if a < b else "same")
    return f"if we divide {a} by {b}, result be {q}. {a} {cmp} big-a than {b}."


def gen_math_paragraph():
    n = random.randint(5, 10)
    gens = [gen_math_add, gen_math_subtract, gen_math_multiply, gen_math_divide]
    parts = []
    for _ in range(n):
        parts.append(random.choice(gens)())
    return " ".join(parts)


# =========================================================================
# Knowledge paragraph templates (factual, deterministic)
# =========================================================================

KNOWLEDGE_TEMPLATES = [
    # 自然
    ("water", [
        "water be one clear-a liquid.",
        "water in zero degree freeze, and become ice.",
        "water in hundred degree boil, and become steam.",
        "all life need water for live.",
        "river and sea have much water.",
        "person can drink water, but can not drink salt-a sea water.",
    ]),
    ("fire", [
        "fire be hot-a and bright-a.",
        "fire need air for burn.",
        "fire can burn wood, paper, cloth.",
        "fire can not burn water or stone.",
        "person use fire for cook food and warm body.",
        "if fire not have air, ta will die.",
    ]),
    ("sun", [
        "sun be one star.",
        "sun be big-a and hot-a.",
        "sun give light and warm to earth.",
        "sun rise in east, and set in west.",
        "all plant need sun-light for grow.",
        "sun make day bright-a, and night come when sun not shine.",
    ]),
    ("moon", [
        "moon go around earth.",
        "moon shine, but moon not have own light.",
        "moon reflect sun light.",
        "moon have four phase: new, first-quarter, full, last-quarter.",
        "person can see moon in night.",
        "moon be smaller than earth.",
    ]),
    ("tree", [
        "tree be one plant.",
        "tree have root, trunk, branch, leaf.",
        "root take water from ground.",
        "leaf take sun-light and make food.",
        "tree can live many year.",
        "tree give fruit, wood, and shadow.",
        "forest be place with many tree.",
    ]),
    ("dog", [
        "dog be one animal.",
        "dog have four leg, one tail, and sharp-a tooth.",
        "dog can run fast-e and hear well-e.",
        "dog eat meat.",
        "person often keep dog as friend.",
        "dog can help person hunt, guard, and find.",
    ]),
    ("person", [
        "person be one animal, but person can think and speak.",
        "person have head, body, two arm, two leg.",
        "person brain can think, learn, remember, create.",
        "person can make tool, build house, grow food.",
        "person can speak with other person, and write book.",
        "person live in family, society, country.",
    ]),
    ("food", [
        "food give energy to body.",
        "person need food for live.",
        "bread, rice, meat, vegetable be common-a food.",
        "fruit have sweet-a taste and good-a for health.",
        "if food be raw, person must cook ta before eat.",
        "if food be old or dirty, ta can make person sick.",
    ]),
    ("season", [
        "year have four season: spring, summer, autumn, winter.",
        "in spring, plant grow and flower bloom.",
        "in summer, weather be hot-a and day be long-a.",
        "in autumn, leaf become yellow and fall.",
        "in winter, weather be cold-a and snow fall in some place.",
        "season change because earth go around sun.",
    ]),
    ("book", [
        "book be many paper with word, bind together.",
        "person write book for record knowledge.",
        "person read book for learn and enjoy.",
        "library be place with many book.",
        "before book exist, person tell story by speak.",
        "now, person can read book in computer or phone.",
    ]),
    ("computer", [
        "computer be one machine that can calculate and process data.",
        "computer have screen, keyboard, memory, processor.",
        "person use computer for work, study, play, talk.",
        "computer can connect to other computer through network.",
        "program be instruction for computer.",
        "ai be one program that can learn and think like person.",
    ]),
    ("music", [
        "music be art of sound.",
        "person make music with voice or instrument.",
        "common-a instrument: piano, guitar, drum, flute.",
        "music can make person feel happy, sad, calm, excited.",
        "every culture have own music style.",
        "person can sing, dance, or just listen to music.",
    ]),
    ("mountain", [
        "mountain be big-a land-form, higher than hill.",
        "mountain top often have snow, even in summer.",
        "highest mountain in world be Everest.",
        "river often begin from mountain.",
        "mountain have many tree, animal, mineral.",
        "climb mountain be difficult but interesting.",
    ]),
    ("sea", [
        "sea be big-a body of salt water.",
        "sea cover most of earth surface.",
        "many fish, whale, dolphin live in sea.",
        "river flow into sea.",
        "person can swim, sail, fish in sea.",
        "sea water be salt, so person can not drink ta.",
    ]),
    ("time", [
        "time flow from past to future.",
        "person can not stop or return time.",
        "one day have twenty-four hour.",
        "one hour have sixty minute.",
        "one minute have sixty second.",
        "one year have twelve month, about three hundred sixty-five day.",
    ]),
]


def gen_knowledge_paragraph():
    topic, facts = random.choice(KNOWLEDGE_TEMPLATES)
    # 打乱顺序，但首句必须是 "X be ..."
    first = facts[0]
    rest = facts[1:]
    random.shuffle(rest)
    selected = [first] + rest[:random.randint(3, len(rest))]
    return " ".join(selected)


# =========================================================================
# Other genres
# =========================================================================

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
        ("write", "letter", ["take one paper", "take one pen", "write greeting", "write your message", "write your name", "put letter in envelope"]),
        ("learn", "language", ["read book every day", "write new word", "speak with other person", "listen to music", "do exercise", "not fear mistake"]),
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
        # 偏向陈述句和被动句
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
    # 选定一个主题
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
    """生成一段 Q&A 对话，融入预训练语料"""
    import json
    sft_path = "/home/z/my-project/logiko/sft_data.jsonl"
    if not os.path.exists(sft_path):
        return gen_knowledge_paragraph()
    with open(sft_path) as f:
        lines = f.readlines()
    n = random.randint(3, 6)
    selected = random.sample(lines, min(n, len(lines)))
    out = []
    for line in selected:
        ex = json.loads(line)
        out.append(f"Q: {ex['question']}")
        out.append(f"A: {ex['answer']}")
    return "\n".join(out)


GENRES = [
    (gen_dialogue, 0.12),
    (gen_narrative, 0.18),
    (gen_knowledge_paragraph, 0.22),
    (gen_instruction, 0.08),
    (gen_news, 0.08),
    (gen_poem, 0.04),
    (gen_math_paragraph, 0.13),
    (gen_qa_paragraph, 0.15),  # Q&A 数据融入预训练
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
        out.append("")  # blank line
        para_id += 1
        total += len(para) + 30
        if para_id % 500 == 0:
            print(f"  ... {total/1024:.1f} KB / {target_bytes/1024:.1f} KB", file=sys.stderr)
    return "\n".join(out)


def main():
    random.seed(42)
    target = 5 * 1024 * 1024
    print(f"Generating Logiko corpus v2 (~{target/1024/1024:.1f} MB)...")
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
