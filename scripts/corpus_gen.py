#!/usr/bin/env python3
"""
Logiko Corpus Generator v4 (Logiko v2.0 spec)
================================================
Major improvements over v3:
  1. Knowledge-base driven: all knowledge paragraphs use REAL fact templates (30+ topics)
  2. Semantic collocation: verb-object compatibility table prevents nonsense like "mountain warn particle"
  3. Math: elementary to high school (arithmetic + algebra + geometry + probability)
  4. Reasoning corpus: multi-step causal chains with real logic
  5. Multi-domain coverage: daily life, science, medicine, law, engineering, history, etc.
  6. No translation tasks (to avoid Logiko spelling interference)
  7. Long complex sentences with subordinate clauses
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
    # 专业领域
    "science": ["atom", "molecule", "cell", "gene", "virus", "bacteria", "energy", "force", "mass", "speed", "gravity", "magnet", "wave", "frequency", "radiation", "particle", "field", "dimension", "light", "sound"],
    "medicine": ["disease", "cure", "drug", "surgery", "patient", "health", "symptom", "diagnosis", "fever", "cough", "wound", "infection", "vaccine", "vitamin", "hormone"],
    "law": ["law", "rule", "right", "duty", "court", "judge", "crime", "punish", "contract", "property", "witness", "evidence", "verdict", "appeal"],
    "tech": ["computer", "program", "code", "data", "network", "server", "algorithm", "memory", "processor", "screen", "keyboard", "internet", "software", "hardware"],
    "math": ["number", "digit", "fraction", "equation", "function", "variable", "constant", "graph", "angle", "triangle", "circle", "square", "sum", "product", "ratio", "proportion"],
    "finance": ["money", "bank", "market", "trade", "cost", "price", "profit", "loss", "investment", "loan", "interest", "tax", "salary", "budget"],
    "transport": ["car", "train", "plane", "ship", "boat", "bike", "road", "bridge", "airport", "station", "wheel", "engine"],
    "art": ["music", "paint", "draw", "sculpt", "dance", "sing", "story", "poem", "novel", "film", "theater", "instrument"],
}

VERB_CLASSES = {
    "motion": ["go", "come", "arrive", "leave", "return", "enter", "travel", "visit", "walk", "run", "jump", "climb", "swim", "fly", "ride", "drive", "fall", "rise", "move", "stop", "turn", "follow", "lead"],
    "body_action": ["eat", "drink", "sleep", "wake", "breathe", "see", "look", "hear", "smell", "taste", "touch", "feel", "speak", "talk", "say", "tell", "sing", "dance", "laugh", "cry", "smile", "sit", "stand", "lie"],
    "mental": ["think", "know", "believe", "remember", "forget", "understand", "learn", "study", "guess", "imagine", "dream", "want", "need", "choose", "decide", "plan", "hope", "fear", "wonder", "notice", "focus", "ignore", "realize", "expect", "predict", "analyze", "deduce", "infer", "conclude"],
    "communication": ["ask", "answer", "tell", "say", "speak", "talk", "read", "write", "explain", "describe", "show", "prove", "promise", "advise", "warn", "thank", "forgive", "blame", "praise", "agree", "refuse", "accept", "argue", "discuss", "report"],
    "creation": ["make", "build", "create", "draw", "paint", "carve", "sew", "knit", "weave", "cook", "bake", "plant", "grow", "decorate", "repair", "fix", "design", "invent"],
    "destruction": ["break", "cut", "tear", "burn", "destroy", "kill", "drop", "crash", "damage"],
    "exchange": ["give", "take", "send", "bring", "receive", "buy", "sell", "pay", "cost", "share", "trade", "own", "borrow", "lend"],
    "state": ["be", "have", "become", "seem", "exist", "happen", "stay", "remain", "change"],
    "nature_verb": ["rain", "snow", "blow", "shine", "freeze", "melt", "boil", "burn", "grow", "wither", "bloom", "flow"],
    "work": ["work", "do", "make", "use", "help", "try", "begin", "finish", "continue", "manage", "organize", "produce", "manufacture"],
    # 专业动词
    "science_verb": ["observe", "experiment", "measure", "calculate", "hypothesize", "test", "verify", "discover", "invent", "analyze"],
    "medical_verb": ["heal", "treat", "diagnose", "prescribe", "operate", "examine", "recover", "suffer", "cure", "vaccinate"],
    "legal_verb": ["judge", "sentence", "defend", "prosecute", "sue", "appeal", "legislate", "enforce", "violate", "comply"],
}

ADJ_CLASSES = {
    "size": ["big", "small", "long", "short", "tall", "wide", "narrow", "thick", "thin"],
    "color_a": ["red", "blue", "green", "yellow", "white", "black", "brown", "gray"],
    "age": ["young", "old", "new", "ancient", "modern", "recent"],
    "quality": ["good", "bad", "beautiful", "ugly", "clean", "dirty", "safe", "dangerous", "useful", "useless", "important", "simple", "complex", "easy", "difficult", "right", "wrong", "true", "false", "real", "fake", "perfect", "imperfect"],
    "feeling": ["happy", "sad", "angry", "calm", "excited", "bored", "tired", "fresh", "strong", "weak", "healthy", "sick", "proud", "humble"],
    "temperature": ["hot", "cold", "warm", "cool"],
    "speed": ["fast", "slow", "quick", "sudden", "gradual"],
    "quantity": ["many", "much", "few", "little", "more", "less", "full", "empty", "rich", "poor", "abundant", "scarce"],
    "property": ["hard", "soft", "sharp", "dull", "smooth", "rough", "dry", "wet", "heavy", "light", "bright", "dark", "deep", "shallow", "high", "low"],
    "taste": ["sweet", "sour", "bitter", "spicy", "salty", "delicious"],
    "logical": ["certain", "possible", "impossible", "necessary", "sufficient", "consistent", "contradictory", "valid", "sound"],
}

ADV_BASE = ["fast", "slow", "good", "easy", "happy", "careful", "quick", "sudden",
            "quiet", "loud", "soft", "well", "safe", "true", "correct", "early", "late", "soon",
            "clear", "exact", "precise", "thorough"]

PRONOUNS = ["I", "we", "you", "ta", "ta-many"]
DEMO = ["this", "that"]
QUANT = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "many", "few", "some", "all", "several", "every", "no"]
TIME_ADVS = ["today", "yesterday", "tomorrow", "now", "soon", "later", "always", "never",
             "often", "sometimes", "early", "late", "past", "fut", "before", "after"]
AUX = ["did", "is", "will", "have"]
MODALS = ["can", "must", "should", "may", "would", "could"]
CONNECTORS = ["and", "or", "but", "because", "so", "therefore", "although", "if", "when", "while", "since", "unless"]
PREP_PLACE = ["in", "on", "at", "under", "over", "between", "among", "through", "across", "along", "around", "near", "far", "inside", "outside"]
PREP_TIME = ["before", "after", "during", "since", "until"]
PREP_DIR = ["to", "from", "toward", "into", "out"]
PREP_OTHER = ["with", "by", "for", "of", "about", "without", "against", "according"]
QWORDS = ["what", "who", "where", "when", "why", "how", "how-many"]

# 语义搭配表：主语类 → 兼容的动词类
SUBJ_VERB_COMPAT = {
    "person": ["body_action", "mental", "communication", "creation", "motion", "exchange", "work", "state", "science_verb", "medical_verb", "legal_verb"],
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
    "science": ["state"],
    "medicine": ["state"],
    "law": ["state"],
    "tech": ["state"],
    "math": ["state"],
    "finance": ["state"],
    "transport": ["motion", "state"],
    "art": ["state"],
}

# 动词 → 兼容的宾语类
VERB_OBJ_COMPAT = {
    "eat": ["food"], "drink": ["food"], "read": ["object", "abstract"], "write": ["object"],
    "buy": ["object", "food"], "sell": ["object", "food"], "build": ["building", "object"],
    "plant": ["plant"], "grow": ["plant", "food"], "cook": ["food"], "bake": ["food"],
    "see": ["animal", "person", "object", "landscape", "plant", "weather", "building", "abstract"],
    "hear": ["abstract", "animal", "person"],
    "smell": ["food", "plant", "substance"],
    "taste": ["food"], "touch": ["object", "body", "substance"], "feel": ["abstract", "body"],
    "love": ["person", "animal", "abstract", "food"],
    "hate": ["person", "abstract", "food"],
    "give": ["object", "food"], "take": ["object", "food"], "send": ["object"], "bring": ["object", "food"],
    "make": ["object", "food", "abstract"], "create": ["object", "abstract", "art"], "build": ["building", "object"],
    "use": ["object", "tech"],
    "open": ["object", "building"], "close": ["object", "building"],
    "wash": ["object", "body", "food"], "wear": ["object"], "ride": ["animal", "transport"],
    "feed": ["animal", "person"], "teach": ["person"], "help": ["person", "animal"], "heal": ["person", "animal"],
    "visit": ["person", "building", "landscape"], "find": ["object", "person", "animal", "abstract"],
    "want": ["object", "food", "abstract"], "need": ["object", "food", "abstract"],
    "study": ["abstract", "science", "math", "medicine", "law"], "learn": ["abstract", "science"],
    "explain": ["abstract", "science"], "describe": ["object", "person", "landscape", "abstract"],
    "remember": ["abstract", "person"], "forget": ["abstract", "person"], "understand": ["abstract"],
    "analyze": ["abstract", "science", "math"], "solve": ["math", "abstract", "law"],
    "design": ["object", "building", "tech"], "invent": ["object", "tech"],
    "observe": ["science", "animal", "person"], "measure": ["science", "object", "math"],
    "calculate": ["math", "science"], "test": ["object", "science", "medicine"],
    "diagnose": ["medicine"], "treat": ["medicine"], "prescribe": ["medicine"],
    "judge": ["law", "person"], "defend": ["law", "person"], "violate": ["law"],
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
    """[指示] + [数量] + [形容词]* + [名词]"""
    parts = []
    if random.random() < 0.4:
        parts.append(random.choice(DEMO))
    if random.random() < 0.6:
        parts.append(random.choice(QUANT))
    if allow_adj:
        n_adj = random.randint(0, 2)
        for _ in range(n_adj):
            # 选与名词类相关的形容词
            if noun_class == "person" and random.random() < 0.5:
                a = pick_adj("feeling") if random.random() < 0.5 else pick_adj("age")
            elif noun_class == "food" and random.random() < 0.5:
                a = pick_adj("taste") if random.random() < 0.5 else pick_adj("temperature")
            elif noun_class == "weather" and random.random() < 0.5:
                a = pick_adj("temperature")
            elif noun_class in ("science", "math") and random.random() < 0.4:
                a = pick_adj("logical") if random.random() < 0.5 else pick_adj("property")
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
    """[时间] + [助] + [副词]* + [动词] + [宾语?]"""
    parts = []
    if random.random() < 0.3:
        parts.append(random.choice(TIME_ADVS))
    r = random.random()
    if r < 0.20:
        parts.append(random.choice(["past", "fut", "did", "will"]))
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


# =========================================================================
# Sentence generators (with semantic coherence)
# =========================================================================
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
    pron = random.choice(PRONOUNS)
    a = pick_adj("size") if random.random() < 0.4 else pick_adj("quality")
    n_cls = random.choice(["object", "animal", "person"])
    n = random.choice(NOUN_CLASSES[n_cls])
    return f"{pron}-a {adj(a)} {n} be here."


def sentence_relative_clause():
    """长难句：含关系从句"""
    subj_cls = random.choice(["person", "animal", "object"])
    subj = random.choice(NOUN_CLASSES[subj_cls])
    v1 = random.choice(VERB_CLASSES["body_action"] + VERB_CLASSES["motion"] + VERB_CLASSES["mental"])
    obj1_cls = random.choice(VERB_OBJ_COMPAT.get(v1, ["object", "food"]))
    obj1 = random.choice(NOUN_CLASSES[obj1_cls])
    v2 = random.choice(VERB_CLASSES["body_action"] + VERB_CLASSES["motion"])
    obj2_cls = random.choice(VERB_OBJ_COMPAT.get(v2, ["object", "food"]))
    obj2 = random.choice(NOUN_CLASSES[obj2_cls])
    return f"{subj} who did {v1} {obj1} past {v2} {obj2}."


def sentence_nested_subordinate():
    """长难句：嵌套从句"""
    main_subj = random.choice(PRONOUNS)
    main_v = random.choice(VERB_CLASSES["mental"] + VERB_CLASSES["communication"])
    sub_subj = random.choice(PRONOUNS)
    sub_v = random.choice(VERB_CLASSES["body_action"] + VERB_CLASSES["motion"])
    sub_obj_cls = random.choice(VERB_OBJ_COMPAT.get(sub_v, ["object"]))
    sub_obj = random.choice(NOUN_CLASSES[sub_obj_cls])
    return f"{main_subj} {main_v} that {sub_subj} past {sub_v} {sub_obj}."


SENTENCE_GEN = [
    (sentence_simple, 0.20),
    (sentence_with_prep, 0.15),
    (sentence_question_wh, 0.06),
    (sentence_question_yn, 0.06),
    (sentence_compound, 0.12),
    (sentence_complex_cause, 0.10),
    (sentence_passive, 0.04),
    (sentence_compare, 0.04),
    (sentence_superlative, 0.03),
    (sentence_possessive, 0.03),
    (sentence_relative_clause, 0.09),
    (sentence_nested_subordinate, 0.08),
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
# Math (deterministic, elementary to high school)
# =========================================================================
def gen_math_arithmetic():
    """基础四则运算"""
    op = random.choice(["add", "subtract", "multiply", "divide"])
    if op == "add":
        a = random.randint(1, 99); b = random.randint(1, 99); r = a + b
        return f"if we add {a} and {b}, result be {r}."
    elif op == "subtract":
        a = random.randint(1, 99); b = random.randint(1, 99); r = a - b
        return f"if we subtract {b} from {a}, result be {r}."
    elif op == "multiply":
        a = random.randint(2, 15); b = random.randint(2, 15); r = a * b
        return f"if we multiply {a} by {b}, result be {r}."
    else:
        b = random.randint(2, 12); q = random.randint(1, 15); a = b * q
        return f"if we divide {a} by {b}, result be {q}."


def gen_math_compare():
    """大小比较"""
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    if a > b:
        return f"{a} more big-a than {b}."
    elif a < b:
        return f"{a} less big-a than {b}."
    else:
        return f"{a} same big-a as {b}."


def gen_math_algebra():
    """一元一次方程：ax + b = c, 求 x"""
    a = random.randint(2, 9)
    x = random.randint(1, 10)
    b = random.randint(1, 20)
    c = a * x + b
    return f"if {a}x + {b} = {c}, then x = {x}. because {a} time {x} = {a*x}, and {a*x} + {b} = {c}."


def gen_math_geometry():
    """几何：面积、周长"""
    shape = random.choice(["rectangle", "triangle", "circle"])
    if shape == "rectangle":
        l = random.randint(2, 20); w = random.randint(2, 20)
        area = l * w
        perimeter = 2 * (l + w)
        return f"rectangle with length {l} and width {w} have area {area} and perimeter {perimeter}."
    elif shape == "triangle":
        base = random.randint(2, 20); height = random.randint(2, 20)
        area = base * height // 2
        return f"triangle with base {base} and height {height} have area {area}. because area of triangle = base time height divide 2."
    else:
        r = random.randint(1, 10)
        # use pi = 3.14
        circumference = 2 * 314 * r / 100
        area = 314 * r * r / 100
        return f"circle with radius {r} have circumference about {circumference:.2f} and area about {area:.2f}. we use pi = 3.14."


def gen_math_probability():
    """概率"""
    total = random.randint(6, 20)
    favorable = random.randint(1, total - 1)
    prob = favorable / total
    return f"if one event have {favorable} favorable-a outcome out of {total} total-a outcome, probability be {favorable} divide {total} = {prob:.2f}."


def gen_math_percentage():
    """百分比"""
    total = random.randint(100, 1000)
    percent = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 90])
    part = total * percent // 100
    return f"{percent} percent of {total} be {part}. because {percent} divide 100 time {total} = {part}."


def gen_math_chain():
    """多步计算"""
    a = random.randint(2, 10)
    b = random.randint(2, 10)
    c = random.randint(2, 10)
    step1 = a + b
    step2 = step1 * c
    return f"first, we add {a} and {b}, get {step1}. then, we multiply {step1} by {c}, get {step2}. so, final-a result be {step2}."


def gen_math_paragraph():
    n = random.randint(4, 8)
    gens = [gen_math_arithmetic, gen_math_compare, gen_math_algebra, gen_math_geometry,
            gen_math_probability, gen_math_percentage, gen_math_chain]
    return " ".join(random.choice(gens)() for _ in range(n))


# =========================================================================
# Knowledge base (REAL FACTS, 30+ topics)
# =========================================================================
KNOWLEDGE_TEMPLATES = [
    ("water", [
        "water be one clear-a liquid without color or taste.",
        "water freeze at zero degree celsius, and become ice.",
        "water boil at hundred degree celsius, and become steam.",
        "all life need water for live. without water, life die.",
        "water cover about seventy-one percent of earth surface.",
        "sea water be salt, so person can not drink ta.",
        "river and lake have fresh-a water that person can drink.",
        "water cycle: water evaporate from sea, form cloud, fall as rain, flow back to sea.",
        "ice be solid-a water. steam be gas-a water. both be same substance.",
        "human body be about sixty percent water.",
    ]),
    ("fire", [
        "fire be one chemical-a reaction that release heat and light.",
        "fire need three thing: fuel, heat, and air.",
        "without air, fire die. this be why covering fire can put ta out.",
        "fire can burn wood, paper, cloth, oil, but can not burn water or stone.",
        "person use fire for cook food, warm body, give light, and scare animal.",
        "fire can be dangerous-a if not control. ta can destroy house and forest.",
        "flame be visible-a part of fire. ta be hot-a gas that glow.",
        "smoke be product of incomplete-a combustion. ta be harmful-a to lung.",
    ]),
    ("sun", [
        "sun be one star at center of we-a solar system.",
        "sun be one big-a ball of hot-a gas, mainly hydrogen and helium.",
        "sun give light and heat to earth. without sun, life not be possible.",
        "sun rise in east and set in west, because earth rotate.",
        "sun light take about eight minute to reach earth.",
        "sun be about one hundred fifty million kilometer from earth.",
        "all plant need sun-light for photosynthesis. ta convert sun energy to food.",
        "sun have surface temperature about five thousand five hundred degree celsius.",
        "sun be about four point six billion year old.",
        "sun will continue to shine for about five billion more year.",
    ]),
    ("moon", [
        "moon be earth-a only natural satellite.",
        "moon go around earth about every twenty-seven day.",
        "moon shine, but moon not have own light. ta reflect sun light.",
        "moon have four main phase: new, first-quarter, full, last-quarter.",
        "moon be about three hundred eighty-four thousand kilometer from earth.",
        "moon be much smaller than earth. ta diameter be about one-quarter of earth.",
        "moon have no air and no liquid-a water, so person can not live there long-a.",
        "moon surface be cover with crater from meteor impact.",
        "moon cause tide on earth because of ta-a gravity.",
        "person first land on moon in 1969.",
    ]),
    ("earth", [
        "earth be third planet from sun in we-a solar system.",
        "earth be only known-a place in universe where life exist.",
        "earth be about four point five billion year old.",
        "earth rotate on ta-a axis once every twenty-four hour, make day and night.",
        "earth orbit sun once every three hundred sixty-five day, make one year.",
        "earth axis be tilt, which cause four season.",
        "earth surface be about seventy-one percent water and twenty-nine percent land.",
        "earth have one natural satellite: moon.",
        "earth atmosphere be mainly nitrogen and oxygen.",
        "earth have seven continent: asia, africa, north america, south america, antarctica, europe, australia.",
    ]),
    ("tree", [
        "tree be one tall-a plant with wood trunk, branch, and leaf.",
        "tree have root in ground that take water and nutrient from soil.",
        "tree leaf take in sun-light and carbon dioxide for photosynthesis.",
        "tree release oxygen, which be essential-a for animal and person.",
        "tree can live many year. some tree live over thousand year.",
        "tree give fruit, wood, shadow, and home for many animal.",
        "forest be place with many tree. ta be called lung of earth.",
        "tree help prevent soil erosion and regulate climate.",
        "tree absorb carbon dioxide, help reduce global-a warming.",
        "tree reproduce through seed, often inside fruit.",
    ]),
    ("dog", [
        "dog be one domestic-a animal, descendant of wolf.",
        "dog be loyal-a friend of person for thousand of year.",
        "dog have four leg, one tail, sharp-a tooth, and excellent-a sense of smell.",
        "dog can run fast-a, hear well-e, and smell thousand time better-e than person.",
        "dog eat meat, but can also eat rice, vegetable, and special-a dog food.",
        "dog live about ten to fifteen year, depend on breed and size.",
        "person use dog for hunt, guard, guide, herd, search, and companion.",
        "dog communicate through bark, growl, whimper, and body language.",
        "dog be social-a animal that live in pack in wild-a state.",
        "dog can learn command and recognize human emotion.",
    ]),
    ("person", [
        "person, or human, be one intelligent-a animal that can think and speak.",
        "person have big-a brain, opposable thumb, and walk on two leg.",
        "person brain be most complex-a known-a structure in universe.",
        "person can make tool, build civilization, and develop science and art.",
        "person live in society, have culture, language, and tradition.",
        "person lifespan be about seventy to eighty year on average.",
        "person inhabit every continent on earth.",
        "person be only species known-a to wonder about origin of universe.",
        "person have emotion: joy, sadness, anger, fear, love, hate.",
        "person pass knowledge through language, writing, and teaching.",
    ]),
    ("food", [
        "food be substance that person eat for energy and nutrition.",
        "food be essential-a for life. without food, person die after some week.",
        "main-a food type: carbohydrate, protein, fat, vitamin, mineral.",
        "bread, rice, noodle be rich-a in carbohydrate.",
        "meat, fish, egg, bean be rich-a in protein.",
        "fruit and vegetable be rich-a in vitamin and fiber.",
        "fresh-a food be healthier-e than process-a food.",
        "person should eat balance-a diet with variety of food.",
        "cooking kill bacteria and make food easier to digest.",
        "if food be old or dirty, ta can cause food poisoning.",
    ]),
    ("season", [
        "year have four season: spring, summer, autumn, winter.",
        "season change because earth axis be tilt at about twenty-three degree.",
        "in spring, weather become warm-a, snow melt, plant begin to grow, flower bloom.",
        "in summer, weather be hot-a, day be long-a, plant grow fast-e.",
        "in autumn, leaf change color and fall, weather become cool-a.",
        "in winter, weather be cold-a, snow fall in many place, plant become dormant.",
        "when one hemisphere tilt toward sun, ta have summer; other have winter.",
        "near equator, season be less obvious. near pole, ta be extreme.",
        "many animal hibernate in winter and become active in spring.",
        "season affect agriculture, clothing, and human activity.",
    ]),
    ("book", [
        "book be one collection of page with word, bind together.",
        "person write book for record knowledge, tell story, express idea.",
        "person read book for learn, enjoy, and inspire.",
        "library be place that collect many book for public-a use.",
        "before book exist, person tell story by speak from memory.",
        "printing press be invent by gutenberg in fifteenth century, make book cheaper.",
        "now, person can read electronic-a book on computer, phone, or e-reader.",
        "common-a book type: novel, textbook, biography, poetry, science, history.",
        "book allow knowledge to persist across generation and time.",
        "good-a book can change person-a perspective and life.",
    ]),
    ("computer", [
        "computer be one electronic-a machine that process data according to instruction.",
        "computer main part: processor, memory, storage, input-output device.",
        "processor, or cpu, be brain of computer. ta execute calculation.",
        "memory, or ram, store data temporarily while computer be on.",
        "storage, like hard disk, keep data permanently even when computer be off.",
        "program be set of instruction that tell computer what to do.",
        "operating system be special-a program that manage computer resource.",
        "internet be global-a network that connect billion of computer.",
        "computer can do billion of calculation per second.",
        "modern-a computer be base on binary-a system, using zero and one.",
    ]),
    ("music", [
        "music be art of organize sound in time.",
        "music have element: rhythm, melody, harmony, timbre.",
        "person make music with voice or instrument.",
        "common-a instrument: piano, guitar, violin, drum, flute, trumpet.",
        "music can express emotion: joy, sadness, anger, calm, excitement.",
        "music exist in every culture around world.",
        "music can be divide into genre: classical, jazz, rock, pop, folk, electronic.",
        "rhythm be pattern of beat in time.",
        "melody be sequence of note that form tune.",
        "harmony be combination of multiple note at same time.",
    ]),
    ("time", [
        "time be one dimension in which event occur in sequence.",
        "time flow from past, through present, to future.",
        "person can not stop, reverse, or return time. ta be one-way.",
        "one day have twenty-four hour. one hour have sixty minute.",
        "one minute have sixty second. one year have about three hundred sixty-five day.",
        "person measure time with clock, watch, and calendar.",
        "according to einstein-a relativity, time be relative-a, not absolute-a.",
        "time can slow down at high-a speed or in strong-a gravity.",
        "time arrow always point toward future, increase entropy.",
        "person experience time subjectively: fun-a time seem short-a, boring-a time seem long-a.",
    ]),
    ("mountain", [
        "mountain be one large-a landform that rise high above surround area.",
        "mountain form through tectonic force over million of year.",
        "mount everest be highest mountain on earth, about eight thousand eight hundred meter.",
        "mountain top often have snow, because temperature decrease with altitude.",
        "many river originate from mountain, where snow melt and form stream.",
        "mountain affect climate by block wind and cause rain on one side.",
        "mountain host diverse-a ecosystem with unique-a plant and animal.",
        "mountain be rich-a in mineral like coal, iron, gold, copper.",
        "climb mountain be difficult-a but rewarding-a activity.",
        "fold mountain form when two tectonic plate collide and push up crust.",
    ]),
    ("sea", [
        "sea be one vast-a body of salt water that cover most of earth surface.",
        "sea be home to million of species, from tiny plankton to big-a whale.",
        "sea water be salt, about three point five percent salt by weight.",
        "person can not drink sea water, because ta cause dehydration.",
        "sea regulate earth-a climate by absorb and distribute heat.",
        "sea produce about half of oxygen on earth, mainly through plankton.",
        "river flow into sea, bring fresh-a water and nutrient.",
        "sea be divide into five ocean: pacific, atlantic, indian, arctic, southern.",
        "deepest part of sea be mariana trench, about eleven kilometer deep.",
        "sea provide food, transport route, and resource for human.",
    ]),
    ("teachist", [
        "teachist be one person who teach, usually in learnej.",
        "teachist help student learn knowledge, skill, and value.",
        "good-a teachist be patient-a, kind-a, wise-a, and clear-a.",
        "teachist explain concept, give exercise, and correct mistake.",
        "teachist shape future by educate next generation.",
        "teachist use method like lecture, discussion, demonstration, practice.",
        "teachist assess student through test, homework, and observation.",
        "teachist need to understand both subject and student.",
        "teachist inspire curiosity and love of learning.",
        "good-a teachist can change student-a life direction.",
    ]),
    ("learnej", [
        "learnej be one place where person learn, also call school.",
        "in learnej, teachist teach student various-a subject.",
        "learnej have classroom, library, laboratory, and play ground.",
        "person usually start learnej at age six, continue for about twelve year.",
        "learnej be divide into elementary, middle, and high level.",
        "learnej be important-a for society because ta spread knowledge.",
        "learnej teach not only fact, but also social-a skill.",
        "learnej can be public-a or private-a.",
        "learnerj prepare person for work and citizen life.",
        "learnerj can be physical-a or online-a, especially after 2020.",
    ]),
    ("cutil", [
        "cutil be one tool for cut, also call knife.",
        "cutil have sharp-a blade and handle.",
        "person use cutil in cookej for cut food.",
        "different-a cutil exist for different-a purpose: meat, vegetable, bread, fruit.",
        "person should use cutil careful-e, because ta can hurt.",
        "if cutil be dull, person should sharpen ta.",
        "sharp-a cutil be safer than dull-a one, because ta require less force.",
        "cutil be one of oldest human tool, make of stone, bone, or metal.",
        "modern-a cutil be usually make of stainless-a steel.",
        "person should wash cutil after use and store ta safe-e.",
    ]),
    ("cookej", [
        "cookej be one place where person cook food, also call kitchen.",
        "cookej have stove, oven, sink, refrigerator, and counter.",
        "cookej be center of home, where food be prepare and family gather.",
        "cookej should be clean-a, because food be prepare there.",
        "in cookej, person can boil, fry, bake, steam, grill food.",
        "cookej need good-a ventilation to remove smoke and smell.",
        "cookej should have proper-a storage for food and tool.",
        "cookej can be dangerous-a for child, so ta need supervision.",
        "modern-a cookej often have dishwasher and microwave.",
        "cookej design reflect culture and cooking style of region.",
    ]),
    # 科学类
    ("atom", [
        "atom be smallest unit of matter that retain property of element.",
        "atom have nucleus with proton and neutron, surround by electron.",
        "proton have positive-a charge, electron have negative-a charge.",
        "neutron have no charge, ta be neutral-a.",
        "atom be extremely small-a, about one ten-billionth of meter.",
        "different-a element have different-a number of proton.",
        "hydrogen be simplest-a atom, with one proton and one electron.",
        "atom combine to form molecule through chemical-a bond.",
        "atom be mostly empty-a space, with dense-a nucleus in center.",
        "energy in atom can be release through nuclear-a reaction.",
    ]),
    ("cell", [
        "cell be basic-a unit of life.",
        "all living thing be make of cell.",
        "cell have membrane, cytoplasm, and genetic-a material.",
        "plant cell have cell wall and chloroplast, animal cell do not.",
        "cell reproduce through division: one cell become two.",
        "human body have about thirty-seven trillion cell.",
        "cell take in nutrient, produce energy, and remove waste.",
        "cell contain organelle like mitochondria, ribosome, nucleus.",
        "dna in nucleus contain genetic-a instruction for cell.",
        "cell can specialize-a for different-a function: muscle, nerve, blood.",
    ]),
    ("energy", [
        "energy be capacity to do work.",
        "energy not be create or destroy, only convert from one form to another.",
        "main-a form of energy: kinetic, potential, thermal, chemical, electrical, light.",
        "kinetic-a energy be energy of motion.",
        "potential-a energy be store-a energy, like water behind dam.",
        "sun be main-a source of energy on earth.",
        "person use fossil-a fuel like coal, oil, gas for energy.",
        "renewable-a energy source: solar, wind, hydro, geothermal.",
        "energy be measure in joule in si unit.",
        "law of conservation of energy be fundamental-a principle of physics.",
    ]),
    ("gravity", [
        "gravity be force that attract object with mass toward each other.",
        "gravity be what make object fall to ground when drop.",
        "gravity keep moon in orbit around earth, and earth around sun.",
        "strength of gravity depend on mass and distance.",
        "larger-a object have stronger-a gravity.",
        "gravity on earth accelerate object at about nine point eight meter per second square.",
        "gravity be weakest of four fundamental-a force.",
        "newton describe gravity in ta-a law of universal-a gravitation.",
        "einstein explain gravity as curvature of spacetime in general-a relativity.",
        "black hole be region where gravity be so strong that nothing can escape.",
    ]),
    # 医学类
    ("heart", [
        "heart be organ that pump blood through body.",
        "heart be about size of fist, locate in chest.",
        "heart beat about seventy time per minute in adult.",
        "heart have four chamber: two atrium and two ventricle.",
        "blood carry oxygen and nutrient to cell, remove waste.",
        "heart-a disease be leading cause of death worldwide.",
        "person can keep heart healthy-e through exercise and good-a diet.",
        "blood pressure measure force of blood against vessel wall.",
        "heart attack occur when blood flow to heart be block.",
        "heart be essential-a for life. without heart, person die within minute.",
    ]),
    ("disease", [
        "disease be abnormal-a condition that affect body or mind.",
        "disease can be cause by virus, bacteria, parasite, or genetic-a factor.",
        "infectious-a disease spread from person to person.",
        "common-a disease: cold, flu, fever, cough, headache.",
        "vaccine help prevent infectious-a disease by train immune-a system.",
        "antibiotic can treat bacterial-a infection but not viral-a one.",
        "chronic-a disease last long-a time: diabetes, heart-a disease, cancer.",
        "symptom be sign of disease: fever, pain, cough, fatigue.",
        "diagnosis be process of identify disease base on symptom and test.",
        "good-a hygiene, diet, and exercise can prevent many disease.",
    ]),
    # 法律类
    ("law", [
        "law be rule that govern behavior in society.",
        "law be make by government and enforce by police and court.",
        "purpose of law be maintain order, protect right, and resolve dispute.",
        "person who violate law can be punish by fine or prison.",
        "court be place where legal-a case be hear and decide.",
        "judge be person who preside over court and make decision.",
        "lawyer be person who represent client in legal-a matter.",
        "constitution be highest law of country.",
        "criminal-a law deal with crime. civil-a law deal with dispute.",
        "person be presume innocent until prove guilty.",
    ]),
    ("justice", [
        "justice be principle of fair-a treatment under law.",
        "justice require that all person be equal-a before law.",
        "justice include both procedural-a and substantive-a aspect.",
        "procedural-a justice mean fair-a process. substantive-a justice mean fair-a outcome.",
        "injustice occur when person be treat unfair-e or discriminate.",
        "justice system include police, court, and prison.",
        "judge-a role be to interpret law and ensure justice.",
        "justice be balance-a between individual-a right and society-a need.",
        "restorative-a justice focus on repair harm, not just punish.",
        "justice be foundation of stable-a and peaceful-a society.",
    ]),
    # 工程类
    ("bridge", [
        "bridge be structure that span obstacle, usually river or valley.",
        "bridge allow transport across obstacle.",
        "main-a bridge type: beam, arch, suspension, cable-stay.",
        "beam bridge be simplest-a type, use rigid-a horizontal-a beam.",
        "arch bridge use curve-a structure to transfer load.",
        "suspension bridge use cable hang from tower.",
        "bridge must support ta-a own weight plus traffic load.",
        "engineer design bridge base on span length, material, and load.",
        "common-a bridge material: steel, concrete, wood.",
        "bridge be essential-a for transportation network.",
    ]),
    ("engine", [
        "engine be machine that convert energy to motion.",
        "combustion-a engine burn fuel to generate power.",
        "electric-a engine use electricity to produce motion.",
        "steam-a engine use steam pressure to drive piston.",
        "car usually have internal-a combustion-a engine.",
        "engine efficiency be ratio of useful-a output to input energy.",
        "engine have moving-a part like piston, crankshaft, valve.",
        "jet-a engine propel airplane by expel hot-a gas.",
        "rocket-a engine work in space by carry both fuel and oxidizer.",
        "engine be essential-a for modern-a transport and industry.",
    ]),
    # 历史类
    ("history", [
        "history be study of past event, especially human-a one.",
        "history help person understand present and plan future.",
        "historian use source like document, artifact, oral-a tradition.",
        "history be divide into era: ancient, medieval, modern, contemporary.",
        "writing-a system be invent about five thousand year ago, mark start of history.",
        "before writing, time be call prehistory.",
        "major-a civilization: egypt, greece, rome, china, india, mesopotamia.",
        "industrial-a revolution in eighteenth century change world dramatically.",
        "world war one occur from 1914 to 1918.",
        "world war two occur from 1939 to 1945, be deadliest-a conflict in history.",
    ]),
    ("language", [
        "language be system of communication use by person.",
        "language can be spoken, written, or sign.",
        "there be about seven thousand language in world today.",
        "language evolve over time, change with culture.",
        "linguistics be scientific-a study of language.",
        "main-a language family: indo-european, sino-tibetan, niger-congo, afro-asiatic.",
        "grammar be rule that govern how word combine.",
        "vocabulary be set of word in one language.",
        "bilingual-a person speak two language.",
        "constructed-a language like logiko be design for specific-a purpose.",
    ]),
    ("money", [
        "money be medium of exchange use in trade.",
        "money function: store of value, unit of account, medium of exchange.",
        "early-a money include shell, salt, cattle, precious-a metal.",
        "modern-a money include coin, paper-a bill, and digital-a currency.",
        "bank be institution that accept deposit and make loan.",
        "inflation occur when price rise and money lose value.",
        "currency be specific-a form of money use in one country.",
        "exchange rate be value of one currency relative to another.",
        "central-a bank, like federal-a reserve, control money supply.",
        "cryptocurrency like bitcoin be new-a form of digital-a money.",
    ]),
    ("dream", [
        "dream be mental-a experience during sleep.",
        "person dream mainly during rem sleep stage.",
        "dream can be vivid-a, emotional-a, and sometimes bizarre-a.",
        "average-a person dream about two hour per night.",
        "dream content can reflect daily-a experience and concern.",
        "nightmare be unpleasant-a or frightening-a dream.",
        "lucid-a dream be dream where dreamer be aware ta be dreaming.",
        "some-a culture believe dream have spiritual-a meaning.",
        "scientist not fully-e understand function of dream.",
        "dream may help process emotion and consolidate memory.",
    ]),
    ("freedom", [
        "freedom be ability to act, speak, or think without restriction.",
        "freedom be fundamental-a human right.",
        "political-a freedom include right to vote and express opinion.",
        "personal-a freedom include choice of religion, partner, career.",
        "freedom of speech be protect in many democratic-a country.",
        "freedom not be absolute-a; ta be limit by law and right of other.",
        "freedom and responsibility be connect-a: more freedom require more responsibility.",
        "many-a person have fight and die for freedom throughout history.",
        "freedom of press be essential-a for democratic-a society.",
        "economic-a freedom allow person to own property and start business.",
    ]),
]


def gen_knowledge_paragraph():
    topic, facts = random.choice(KNOWLEDGE_TEMPLATES)
    first = facts[0]
    rest = facts[1:]
    random.shuffle(rest)
    selected = [first] + rest[:random.randint(3, len(rest))]
    return " ".join(selected)


# =========================================================================
# Reasoning corpus (multi-step causal chains with real logic)
# =========================================================================
REASONING_TEMPLATES = [
    # 物理因果
    "because sun rise, earth surface become warm-a. therefore, water evaporate from sea and form cloud. when cloud become heavy-a, water fall as rain. this be water cycle.",
    "if you heat ice, ta melt and become water. if you continue to heat water, ta boil and become steam. this be because heat increase molecular-a motion.",
    "because earth rotate on ta-a axis, sun appear to rise in east and set in west. this rotation take twenty-four hour, make one day.",
    "when object fall, gravity pull ta toward earth center. ta accelerate at nine point eight meter per second square. so, after one second, speed be nine point eight meter per second.",
    "because metal be good-a conductor, ta allow electricity to flow. however, plastic be insulator, so ta block electricity. this be why electric-a wire have metal inside and plastic outside.",
    
    # 生物因果
    "because plant need sun-light for photosynthesis, ta grow toward sun. if plant not receive enough light, ta become weak-a and yellow. this process be call phototropism.",
    "when person eat food, body digest ta and convert to glucose. glucose enter bloodstream, and insulin help cell absorb ta. if insulin not work, person develop diabetes.",
    "because heart pump blood, oxygen reach every cell. cell use oxygen to produce energy through respiration. without oxygen, cell die within minute.",
    "vaccine contain weaken-a or dead-a pathogen. when inject into body, immune-a system learn to recognize ta. so, when real-a pathogen enter, body can fight ta quickly.",
    
    # 社会因果
    "because education improve person-a skill, ta can find better-e job. with better-e job, ta earn more money. with more money, ta can afford better-e health and housing. so, education reduce poverty.",
    "if government build more road, more person buy car. more car mean more traffic and more pollution. so, simply-e build road not solve traffic problem. public-a transport be better-e solution.",
    "because internet connect person globally, information spread fast-e. this help learning and business, but also spread false-a information. so, person need critical-a thinking to evaluate source.",
    
    # 逻辑推理
    "all human be mortal. socrates be human. therefore, socrates be mortal. this be classic-a syllogism that demonstrate deductive-a reasoning.",
    "if a be greater than b, and b be greater than c, then a be greater than c. this be transitive-a property of inequality.",
    "if today be monday, then tomorrow be tuesday. today be monday. therefore, tomorrow be tuesday. this be modus ponens, valid-a logical-a form.",
    
    # 数学推理
    "if x + 5 = 12, then x = 12 - 5 = 7. we can verify: 7 + 5 = 12. so, x = 7 be correct-a solution.",
    "if one triangle have three side equal-a, then ta be equilateral. all angle of equilateral triangle be sixty degree. so, each angle be sixty degree.",
    "if one number be even, then ta be divisible by 2. 8 be even. therefore, 8 be divisible by 2. indeed, 8 divide by 2 equal 4.",
    
    # 历史/社会
    "because printing press be invent in fifteenth century, book become cheaper. more person learn to read. this lead to spread of new idea, including scientific-a revolution and enlightenment.",
    "because industrial-a revolution, factory replace hand-a work. many person move from country to city. this cause urban-a growth and change social-a structure.",
]


def gen_reasoning_paragraph():
    return random.choice(REASONING_TEMPLATES)


# =========================================================================
# Multi-turn Q&A from SFT data
# =========================================================================
def gen_qa_paragraph():
    """Generate a multi-turn Q&A paragraph from SFT data."""
    sft_path = "/home/z/my-project/logiko/sft_data.jsonl"
    if not os.path.exists(sft_path):
        return gen_knowledge_paragraph()
    with open(sft_path) as f:
        lines = f.readlines()
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
        ("cook", "rice", ["wash rice clean-e", "put rice in pot", "add water, about twice amount of rice", "boil on high-a heat", "when water boil, lower heat", "cover pot and wait fifteen minute", "rice be ready"]),
        ("build", "house", ["find flat-a ground", "dig hole for foundation", "put stone in hole", "build wall with wood or brick", "put roof on wall", "make door and window", "paint and decorate"]),
        ("plant", "tree", ["choose good-a location with sun", "dig hole twice size of root", "put tree in hole careful-e", "fill hole with earth", "water tree thorough-e", "add mulch around base", "water regular-e for first year"]),
        ("write", "letter", ["take one clean-a paper", "take one pen", "write date at top", "write greeting like dear friend", "write you-a message clear-e", "end with closing like sincerely", "sign you-a name at bottom", "put letter in envelope and send"]),
        ("learn", "logiko", ["read spec first for understand grammar", "memorize core root word", "learn suffix and prefix", "read example text in corpus", "write simple-a sentence yourself", "speak with other person in logiko", "practice regular-e every day"]),
        ("cook", "soup", ["prepare vegetable: wash and cut", "put water in pot and boil", "add vegetable to boiling water", "add salt and spice for taste", "cook on low-a heat for twenty minute", "taste and adjust seasoning", "serve hot-a in bowl"]),
    ]
    verb, obj, steps = random.choice(topics)
    intro = f"if you want {verb} {obj}, you can follow this method:"
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


# =========================================================================
# Main generator
# =========================================================================
GENRES = [
    (gen_knowledge_paragraph, 0.25),  # 知识段落（25%）
    (gen_reasoning_paragraph, 0.12),  # 推理段落（12%）
    (gen_math_paragraph, 0.15),       # 数学（15%）
    (gen_qa_paragraph, 0.12),         # Q&A（12%）
    (gen_dialogue, 0.08),
    (gen_narrative, 0.10),
    (gen_instruction, 0.07),
    (gen_news, 0.06),
    (gen_poem, 0.05),
]


def gen_paragraph():
    r = random.random()
    acc = 0
    for gen, p in GENRES:
        acc += p
        if r < acc:
            return gen()
    return gen_knowledge_paragraph()


def gen_corpus(target_bytes=10 * 1024 * 1024):
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
        if para_id % 1000 == 0:
            print(f"  ... {total/1024:.1f} KB / {target_bytes/1024:.1f} KB", file=sys.stderr)
    return "\n".join(out)


def main():
    random.seed(42)
    target = 10 * 1024 * 1024  # 10 MB
    print(f"Generating Logiko v4 corpus (~{target/1024/1024:.1f} MB)...")
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
