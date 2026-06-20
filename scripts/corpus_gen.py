#!/usr/bin/env python3
"""
Logiko Corpus Generator v6 (Logiko v4.0 spec)
================================================
Key changes from v5:
  1. Tense suffixes -s/-d/-r on verbs (sentence-final, optional but reinforced)
  2. Relative clauses with `ki` (pre-modifier, consistent)
  3. Natural CoT (because/so/therefore, not firstly/secondly templates)
  4. Calculation process corpus (step-by-step arithmetic)
  5. Discourse markers enforced in long paragraphs
  6. Modal system fixed order: [modal] + [tense] + [adv] + [verb]
  7. Compound word rules: hyphen for new, fused for stable
  8. 15MB target, 1.5-2x daily/knowledge
"""
import random
import os
import sys
import json
from math import comb

# =========================================================================
# Vocabulary (v4: with semantic classes)
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
    "mental": ["think", "know", "believe", "remember", "forget", "understand", "learn", "study", "guess", "imagine", "dream", "want", "need", "choose", "decide", "plan", "hope", "fear", "wonder", "notice", "focus", "ignore", "realize", "expect", "predict", "analyze", "deduce", "infer", "conclude", "reason"],
    "communication": ["ask", "answer", "tell", "say", "speak", "talk", "read", "write", "explain", "describe", "show", "prove", "promise", "advise", "warn", "thank", "forgive", "blame", "praise", "agree", "refuse", "accept", "argue", "discuss", "report"],
    "creation": ["make", "build", "create", "draw", "paint", "carve", "sew", "knit", "weave", "cook", "bake", "plant", "grow", "decorate", "repair", "fix", "design", "invent"],
    "destruction": ["break", "cut", "tear", "burn", "destroy", "kill", "drop", "crash", "damage"],
    "exchange": ["give", "take", "send", "bring", "receive", "buy", "sell", "pay", "cost", "share", "trade", "own", "borrow", "lend"],
    "state": ["be", "have", "become", "seem", "exist", "happen", "stay", "remain", "change"],
    "nature_verb": ["rain", "snow", "blow", "shine", "freeze", "melt", "boil", "burn", "grow", "wither", "bloom", "flow"],
    "work": ["work", "do", "make", "use", "help", "try", "begin", "finish", "continue", "manage", "organize", "produce", "manufacture"],
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

# v4: discourse markers
DISCOURSE = ["however", "moreover", "in-addition", "for-example", "in-fact",
             "therefore", "thus", "meanwhile", "specifically", "generally"]
# v4: natural CoT connectors (not firstly/secondly)
COT_CONNECTORS = ["because", "so", "therefore", "this mean", "which lead to", "as a result", "consequently", "in-conclusion"]

PRONOUNS = ["I", "we", "you", "ta", "ta-many"]
DEMO = ["this", "that"]
QUANT = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "many", "few", "some", "all", "several", "every", "no"]
TIME_ADVS = ["today", "yesterday", "tomorrow", "now", "soon", "later", "always", "never",
             "often", "sometimes", "early", "late", "past", "fut", "before", "after"]
# v4: tense can be marked by auxiliary OR suffix
TENSE_AUX = ["did", "is", "will", "have", "past", "fut"]
TENSE_SUFFIX = {"present": "-s", "past": "-d", "future": "-r"}
MODALS = ["can", "must", "should", "may", "would", "could"]
CONNECTORS = ["and", "or", "but", "because", "so", "therefore", "although", "if", "when", "while", "since", "unless"]
PREP_PLACE = ["in", "on", "at", "under", "over", "between", "among", "through", "across", "along", "around", "near", "far", "inside", "outside"]
PREP_TIME = ["before", "after", "during", "since", "until"]
PREP_DIR = ["to", "from", "toward", "into"]
PREP_OTHER = ["with", "by", "for", "of", "about", "without", "against"]
QWORDS = ["what", "who", "where", "when", "why", "how", "how-many"]

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
    """v4: [modal] + [tense] + [adv] + [verb-suffix] + [obj]"""
    parts = []
    if random.random() < 0.3:
        parts.append(random.choice(TIME_ADVS))
    r = random.random()
    # v4: fixed order modal > tense > neg > adv > verb
    if r < 0.10:
        parts.append(random.choice(MODALS))
    if r < 0.30:
        # tense: either auxiliary or suffix (v4 prefers suffix for naturalness)
        tense_choice = random.choice(["aux", "suffix", "aux"])
        if tense_choice == "aux":
            parts.append(random.choice(TENSE_AUX))
        # suffix will be added to verb later
    elif r < 0.40:
        parts.append("not")
    if random.random() < 0.4:
        parts.append(adv(random.choice(ADV_BASE)))

    if subj_class and subj_class in SUBJ_VERB_COMPAT:
        compat_verb_classes = SUBJ_VERB_COMPAT[subj_class]
        verb_cls = random.choice(compat_verb_classes)
        v = random.choice(VERB_CLASSES[verb_cls])
    else:
        v = random.choice(VERB_CLASSES["state"] + VERB_CLASSES["motion"] + VERB_CLASSES["body_action"])
    
    # v4: maybe add tense suffix to verb
    if r < 0.30 and "aux" not in parts and "past" not in parts and "fut" not in parts and "did" not in parts and "will" not in parts:
        # use suffix
        suffix = random.choice(["-s", "-d", "-r", ""])  # often no suffix
        v = v + suffix
    parts.append(v)

    if random.random() < 0.7:
        if v.rstrip("-sdr") in VERB_OBJ_COMPAT:
            obj_cls = random.choice(VERB_OBJ_COMPAT[v.rstrip("-sdr")])
            obj_phrase, _ = noun_phrase(obj_cls)
        else:
            obj_phrase, _ = noun_phrase()
        parts.append(obj_phrase)
    return " ".join(parts), v


# =========================================================================
# Sentence generators v4 (with ki relative clause, discourse, tense suffix)
# =========================================================================
def sentence_simple():
    subj_cls = random.choice(list(NOUN_CLASSES.keys()))
    if subj_cls in ("person", "animal"):
        subj = random.choice(PRONOUNS) if random.random() < 0.4 else random.choice(NOUN_CLASSES[subj_cls])
    else:
        subj = random.choice(NOUN_CLASSES[subj_cls])
    vp, v = verb_phrase(subj_cls)
    return f"{subj} {vp}."


def sentence_with_discourse():
    """v4: discourse markers"""
    s1 = sentence_simple().rstrip(".")
    disc = random.choice(DISCOURSE)
    s2 = sentence_simple().rstrip(".")
    return f"{s1}. {disc}, {s2.lower()}."


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
    return f"{subj_phrase} be {v}-d by {agent}."


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
    """v4: use ki for relative clause (pre-modifier)"""
    subj_cls = random.choice(["person", "animal", "object"])
    subj = random.choice(NOUN_CLASSES[subj_cls])
    v1 = random.choice(VERB_CLASSES["body_action"] + VERB_CLASSES["motion"] + VERB_CLASSES["mental"])
    obj1_cls = random.choice(VERB_OBJ_COMPAT.get(v1, ["object", "food"]))
    obj1 = random.choice(NOUN_CLASSES[obj1_cls])
    # v4: ki + clause + noun
    return f"ki {v1}-d {obj1} {subj} be here."


def sentence_nested_subordinate():
    main_subj = random.choice(PRONOUNS)
    main_v = random.choice(VERB_CLASSES["mental"] + VERB_CLASSES["communication"])
    sub_subj = random.choice(PRONOUNS)
    sub_v = random.choice(VERB_CLASSES["body_action"] + VERB_CLASSES["motion"])
    sub_obj_cls = random.choice(VERB_OBJ_COMPAT.get(sub_v, ["object"]))
    sub_obj = random.choice(NOUN_CLASSES[sub_obj_cls])
    return f"{main_subj} {main_v} that {sub_subj} {sub_v}-d {sub_obj}."


SENTENCE_GEN = [
    (sentence_simple, 0.18),
    (sentence_with_discourse, 0.10),
    (sentence_with_prep, 0.13),
    (sentence_question_wh, 0.05),
    (sentence_question_yn, 0.05),
    (sentence_compound, 0.10),
    (sentence_complex_cause, 0.10),
    (sentence_passive, 0.04),
    (sentence_compare, 0.04),
    (sentence_superlative, 0.03),
    (sentence_possessive, 0.03),
    (sentence_relative_clause, 0.08),
    (sentence_nested_subordinate, 0.07),
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
# Math: with calculation process (v4 key improvement)
# =========================================================================
def gen_math_arithmetic_simple():
    op = random.choice(["add", "subtract", "multiply", "divide"])
    if op == "add":
        a = random.randint(1, 50); b = random.randint(1, 50); r = a + b
        return f"if we add {a} and {b}, result be {r}."
    elif op == "subtract":
        a = random.randint(1, 99); b = random.randint(1, 99); r = a - b
        return f"if we subtract {b} from {a}, result be {r}."
    elif op == "multiply":
        a = random.randint(2, 12); b = random.randint(2, 12); r = a * b
        return f"if we multiply {a} by {b}, result be {r}."
    else:
        b = random.randint(2, 12); q = random.randint(1, 12); a = b * q
        return f"if we divide {a} by {b}, result be {q}."


def gen_math_calculation_process():
    """v4: step-by-step calculation (solves 'can't compute' problem)"""
    op = random.choice(["add", "subtract", "multiply"])
    if op == "add":
        a = random.randint(10, 99); b = random.randint(10, 99); r = a + b
        # Show digit-by-digit
        a_ones = a % 10; b_ones = b % 10
        ones_sum = a_ones + b_ones
        carry = ones_sum // 10
        ones_digit = ones_sum % 10
        a_tens = a // 10; b_tens = b // 10
        tens_sum = a_tens + b_tens + carry
        return f"to add {a} and {b}: {a_ones} + {b_ones} = {ones_sum}, write {ones_digit}, carry {carry}. then {a_tens} + {b_tens} + {carry} = {tens_sum}. so, {a} + {b} = {r}."
    elif op == "subtract":
        a = random.randint(20, 99); b = random.randint(1, a-1); r = a - b
        a_ones = a % 10; b_ones = b % 10
        if a_ones >= b_ones:
            return f"to subtract {b} from {a}: {a_ones} - {b_ones} = {a_ones - b_ones}. then {a//10} - {b//10} = {a//10 - b//10}. so, {a} - {b} = {r}."
        else:
            return f"to subtract {b} from {a}: {a_ones} < {b_ones}, borrow 10. {a_ones+10} - {b_ones} = {a_ones+10-b_ones}. then {a//10-1} - {b//10} = {a//10-1-b//10}. so, {a} - {b} = {r}."
    else:
        a = random.randint(2, 9); b = random.randint(2, 9); r = a * b
        return f"to multiply {a} by {b}: {a} × {b} mean add {a} together {b} time. {a} + {a} = {2*a}, + {a} = {3*a}, + {a} = {4*a}" + (f", + {a} = {5*a}" if b >= 5 else "") + (f", + {a} = {6*a}" if b >= 6 else "") + (f", + {a} = {7*a}" if b >= 7 else "") + (f", + {a} = {8*a}" if b >= 8 else "") + (f", + {a} = {9*a}" if b >= 9 else "") + f". so, {a} × {b} = {r}."


def gen_math_compare():
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    if a > b:
        return f"{a} more big-a than {b}, because {a} - {b} = {a-b}."
    elif a < b:
        return f"{a} less big-a than {b}, because {b} - {a} = {b-a}."
    else:
        return f"{a} same big-a as {b}."


def gen_math_algebra_linear():
    a = random.randint(2, 9)
    x = random.randint(1, 10)
    b = random.randint(1, 20)
    c = a * x + b
    return f"if {a}x + {b} = {c}, then x = {x}. because {a}x = {c} - {b} = {a*x}, so x = {a*x} divide {a} = {x}."


def gen_math_algebra_quadratic():
    r1 = random.randint(-5, 5)
    r2 = random.randint(-5, 5)
    if r1 == r2:
        r2 += 1
    b = -(r1 + r2)
    c = r1 * r2
    return f"if x² + {b}x + {c} = 0, then x = {r1} or x = {r2}. because (x - {r1})(x - {r2}) = 0."


def gen_math_geometry():
    shape = random.choice(["rectangle", "triangle", "circle", "angle-sum"])
    if shape == "rectangle":
        l = random.randint(2, 20); w = random.randint(2, 20)
        area = l * w; perim = 2 * (l + w)
        return f"rectangle with length {l} and width {w} have area {area} and perimeter {perim}. area = {l} × {w} = {area}. perimeter = 2 × ({l} + {w}) = {perim}."
    elif shape == "triangle":
        base = random.randint(2, 20); height = random.randint(2, 20)
        area = base * height // 2
        return f"triangle with base {base} and height {height} have area {area}. because area = base × height ÷ 2 = {base} × {height} ÷ 2 = {area}."
    elif shape == "circle":
        r = random.randint(1, 10)
        circ = 2 * 314 * r / 100
        area = 314 * r * r / 100
        return f"circle with radius {r} have circumference {circ:.2f} and area {area:.2f}. circumference = 2 × 3.14 × {r}. area = 3.14 × {r}²."
    else:
        a = random.randint(30, 80)
        b = random.randint(30, 80)
        c = 180 - a - b
        if c > 0:
            return f"triangle have angle A = {a}° and angle B = {b}°. angle C = 180 - {a} - {b} = {c}°. because sum of angle in triangle = 180°."


def gen_math_probability():
    total = random.randint(6, 20)
    favorable = random.randint(1, total - 1)
    prob = favorable / total
    return f"if event have {favorable} favorable-a outcome out of {total} total-a outcome, probability = {favorable} ÷ {total} = {prob:.2f}."


def gen_math_probability_combo():
    red = random.randint(2, 5)
    blue = random.randint(2, 5)
    total = red + blue
    p = comb(red, 2) / comb(total, 2)
    return f"if bag have {red} red-a ball and {blue} blue-a ball, P(pick 2 red) = C({red},2) ÷ C({total},2) = {comb(red,2)} ÷ {comb(total,2)} = {p:.2f}."


def gen_math_percentage():
    total = random.randint(100, 1000)
    percent = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 90])
    part = total * percent // 100
    return f"{percent}% of {total} = {part}. because {percent} ÷ 100 × {total} = {part}."


def gen_math_chain_natural():
    """v4: natural language chain (not firstly/secondly)"""
    a = random.randint(2, 10)
    b = random.randint(2, 10)
    c = random.randint(2, 10)
    step1 = a + b
    step2 = step1 * c
    return f"because we add {a} and {b}, we get {step1}. so, when we multiply {step1} by {c}, result be {step2}. in-conclusion, final-a answer be {step2}."


def gen_math_identity():
    a = random.randint(2, 9)
    b = random.randint(2, 9)
    return f"if a = {a} and b = {b}, then (a+b)² = {a}² + 2×{a}×{b} + {b}² = {a*a} + {2*a*b} + {b*b} = {(a+b)**2}."


def gen_math_inequality():
    a = random.randint(2, 10)
    x = a + 1
    return f"if x > {a}, then 2x > {2*a}. for-example, if x = {x}, then 2x = {2*x} > {2*a}."


def gen_math_paragraph():
    n = random.randint(4, 7)
    # v4: 50% chance to include calculation process
    gens = [gen_math_arithmetic_simple, gen_math_compare, gen_math_algebra_linear, gen_math_algebra_quadratic,
            gen_math_geometry, gen_math_probability, gen_math_probability_combo, gen_math_percentage,
            gen_math_chain_natural, gen_math_identity, gen_math_inequality, gen_math_calculation_process]
    parts = []
    # ensure at least 1 calculation process per paragraph
    parts.append(gen_math_calculation_process())
    for _ in range(n - 1):
        parts.append(random.choice(gens)())
    return " ".join(parts)


# =========================================================================
# Knowledge base (REAL FACTS, 50+ topics, with discourse markers)
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
        "water cycle be essential-a for life on earth.",
        "ice be solid-a water. steam be gas-a water.",
        "human body be about sixty percent water.",
    ]),
    ("fire", [
        "fire be one chemical-a reaction that release heat and light.",
        "fire need three thing: fuel, heat, and air.",
        "without air, fire die. this be why covering fire can put ta out.",
        "fire can burn wood, paper, cloth, oil, but can not burn water or stone.",
        "person use fire for cook food, warm body, give light.",
        "fire can be dangerous-a if not control.",
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
        "all plant need sun-light for photosynthesis.",
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
        "moon have no air and no liquid-a water.",
        "moon surface be cover with crater from meteor impact.",
        "moon cause tide on earth because of ta-a gravity.",
        "person first land on moon in 1969.",
    ]),
    ("earth", [
        "earth be third planet from sun in we-a solar system.",
        "earth be only known-a place in universe where life exist.",
        "earth be about four point five billion year old.",
        "earth rotate on ta-a axis once every twenty-four hour.",
        "earth orbit sun once every three hundred sixty-five day.",
        "earth axis be tilt, which cause four season.",
        "earth surface be about seventy-one percent water.",
        "earth have one natural satellite: moon.",
        "earth atmosphere be mainly nitrogen and oxygen.",
        "earth have seven continent.",
    ]),
    ("tree", [
        "tree be one tall-a plant with wood trunk, branch, and leaf.",
        "tree have root in ground that take water and nutrient.",
        "tree leaf take in sun-light and carbon dioxide for photosynthesis.",
        "tree release oxygen, which be essential-a for animal.",
        "tree can live many year. some tree live over thousand year.",
        "tree give fruit, wood, shadow, and home for animal.",
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
        "dog eat meat, but can also eat rice, vegetable, and dog food.",
        "dog live about ten to fifteen year.",
        "person use dog for hunt, guard, guide, herd, search, and companion.",
        "dog communicate through bark, growl, whimper, and body language.",
        "dog be social-a animal that live in pack in wild-a state.",
        "dog can learn command and recognize human emotion.",
    ]),
    ("person", [
        "person be one intelligent-a animal that can think and speak.",
        "person have big-a brain, opposable thumb, and walk on two leg.",
        "person brain be most complex-a known-a structure in universe.",
        "person can make tool, build civilization, and develop science.",
        "person live in society, have culture, language, and tradition.",
        "person lifespan be about seventy to eighty year on average.",
        "person inhabit every continent on earth.",
        "person be only species known-a to wonder about origin of universe.",
        "person have emotion: joy, sadness, anger, fear, love, hate.",
        "person pass knowledge through language, writing, and teaching.",
    ]),
    ("food", [
        "food be substance that person eat for energy and nutrition.",
        "food be essential-a for life. without food, person die.",
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
        "in spring, weather become warm-a, snow melt, plant grow, flower bloom.",
        "in summer, weather be hot-a, day be long-a, plant grow fast-e.",
        "in autumn, leaf change color and fall, weather become cool-a.",
        "in winter, weather be cold-a, snow fall in many place.",
        "when one hemisphere tilt toward sun, ta have summer.",
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
        "printing press be invent by gutenberg in fifteenth century.",
        "now, person can read electronic-a book on computer or phone.",
        "common-a book type: novel, textbook, biography, poetry, science.",
        "book allow knowledge to persist across generation.",
        "good-a book can change person-a perspective and life.",
    ]),
    ("computer", [
        "computer be one electronic-a machine that process data.",
        "computer main part: processor, memory, storage, input-output device.",
        "processor, or cpu, be brain of computer.",
        "memory, or ram, store data temporarily while computer be on.",
        "storage, like hard disk, keep data permanently.",
        "program be set of instruction that tell computer what to do.",
        "operating system be special-a program that manage resource.",
        "internet be global-a network that connect billion of computer.",
        "computer can do billion of calculation per second.",
        "modern-a computer be base on binary-a system.",
    ]),
    ("music", [
        "music be art of organize sound in time.",
        "music have element: rhythm, melody, harmony, timbre.",
        "person make music with voice or instrument.",
        "common-a instrument: piano, guitar, violin, drum, flute.",
        "music can express emotion: joy, sadness, anger, calm, excitement.",
        "music exist in every culture around world.",
        "music can be divide into genre: classical, jazz, rock, pop, folk.",
        "rhythm be pattern of beat in time.",
        "melody be sequence of note that form tune.",
        "harmony be combination of multiple note at same time.",
    ]),
    ("time", [
        "time be one dimension in which event occur in sequence.",
        "time flow from past, through present, to future.",
        "person can not stop, reverse, or return time.",
        "one day have twenty-four hour. one hour have sixty minute.",
        "one minute have sixty second. one year have about 365 day.",
        "person measure time with clock, watch, and calendar.",
        "according to einstein-a relativity, time be relative-a.",
        "time can slow down at high-a speed or in strong-a gravity.",
        "time arrow always point toward future, increase entropy.",
        "person experience time subjectively.",
    ]),
    ("mountain", [
        "mountain be one large-a landform that rise high above surround area.",
        "mountain form through tectonic force over million of year.",
        "mount everest be highest mountain on earth, about 8848 meter.",
        "mountain top often have snow, because temperature decrease with altitude.",
        "many river originate from mountain, where snow melt.",
        "mountain affect climate by block wind and cause rain.",
        "mountain host diverse-a ecosystem with unique-a plant and animal.",
        "mountain be rich-a in mineral like coal, iron, gold, copper.",
        "climb mountain be difficult-a but rewarding-a activity.",
        "fold mountain form when two tectonic plate collide.",
    ]),
    ("sea", [
        "sea be one vast-a body of salt water that cover most of earth.",
        "sea be home to million of species.",
        "sea water be salt, about 3.5 percent salt by weight.",
        "person can not drink sea water, because ta cause dehydration.",
        "sea regulate earth-a climate by absorb and distribute heat.",
        "sea produce about half of oxygen on earth through plankton.",
        "river flow into sea, bring fresh-a water and nutrient.",
        "sea be divide into five ocean: pacific, atlantic, indian, arctic, southern.",
        "deepest part of sea be mariana trench, about 11 kilometer deep.",
        "sea provide food, transport route, and resource for human.",
    ]),
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
        "cell can specialize-a for different-a function.",
    ]),
    ("energy", [
        "energy be capacity to do work.",
        "energy not be create or destroy, only convert.",
        "main-a form: kinetic, potential, thermal, chemical, electrical, light.",
        "kinetic-a energy be energy of motion.",
        "potential-a energy be store-a energy.",
        "sun be main-a source of energy on earth.",
        "person use fossil-a fuel like coal, oil, gas for energy.",
        "renewable-a energy source: solar, wind, hydro, geothermal.",
        "energy be measure in joule.",
        "law of conservation of energy be fundamental-a principle.",
    ]),
    ("gravity", [
        "gravity be force that attract object with mass toward each other.",
        "gravity be what make object fall to ground when drop.",
        "gravity keep moon in orbit around earth, and earth around sun.",
        "strength of gravity depend on mass and distance.",
        "larger-a object have stronger-a gravity.",
        "gravity on earth accelerate object at about 9.8 meter per second square.",
        "gravity be weakest of four fundamental-a force.",
        "newton describe gravity in ta-a law of universal-a gravitation.",
        "einstein explain gravity as curvature of spacetime.",
        "black hole be region where gravity be so strong that nothing can escape.",
    ]),
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
        "heart be essential-a for life.",
    ]),
    ("disease", [
        "disease be abnormal-a condition that affect body or mind.",
        "disease can be cause by virus, bacteria, parasite, or genetic-a factor.",
        "infectious-a disease spread from person to person.",
        "common-a disease: cold, flu, fever, cough, headache.",
        "vaccine help prevent infectious-a disease.",
        "antibiotic can treat bacterial-a infection but not viral-a one.",
        "chronic-a disease last long-a time: diabetes, cancer.",
        "symptom be sign of disease: fever, pain, cough, fatigue.",
        "diagnosis be process of identify disease.",
        "good-a hygiene, diet, and exercise can prevent many disease.",
    ]),
    ("law", [
        "law be rule that govern behavior in society.",
        "law be make by government and enforce by police and court.",
        "purpose of law be maintain order, protect right, resolve dispute.",
        "person who violate law can be punish by fine or prison.",
        "court be place where legal-a case be hear and decide.",
        "judge be person who preside over court.",
        "lawyer be person who represent client in legal-a matter.",
        "constitution be highest law of country.",
        "criminal-a law deal with crime. civil-a law deal with dispute.",
        "person be presume innocent until prove guilty.",
    ]),
    ("history", [
        "history be study of past event, especially human-a one.",
        "history help person understand present and plan future.",
        "historian use source like document, artifact, oral-a tradition.",
        "history be divide into era: ancient, medieval, modern, contemporary.",
        "writing-a system be invent about five thousand year ago.",
        "before writing, time be call prehistory.",
        "major-a civilization: egypt, greece, rome, china, india, mesopotamia.",
        "industrial-a revolution in eighteenth century change world.",
        "world war one occur from 1914 to 1918.",
        "world war two occur from 1939 to 1945.",
    ]),
    ("language", [
        "language be system of communication use by person.",
        "language can be spoken, written, or sign.",
        "there be about seven thousand language in world today.",
        "language evolve over time, change with culture.",
        "linguistics be scientific-a study of language.",
        "main-a language family: indo-european, sino-tibetan, niger-congo.",
        "grammar be rule that govern how word combine.",
        "vocabulary be set of word in one language.",
        "bilingual-a person speak two language.",
        "constructed-a language like logiko be design for specific-a purpose.",
    ]),
    ("money", [
        "money be medium of exchange use in trade.",
        "money function: store of value, unit of account, medium of exchange.",
        "early-a money include shell, salt, cattle, precious-a metal.",
        "modern-a money include coin, paper-a bill, digital-a currency.",
        "bank be institution that accept deposit and make loan.",
        "inflation occur when price rise and money lose value.",
        "currency be specific-a form of money use in one country.",
        "exchange rate be value of one currency relative to another.",
        "central-a bank control money supply.",
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
        "freedom and responsibility be connect-a.",
        "many-a person have fight and die for freedom throughout history.",
        "freedom of press be essential-a for democratic-a society.",
        "economic-a freedom allow person to own property and start business.",
    ]),
    ("light", [
        "light be form of electromagnetic-a radiation visible-a to human eye.",
        "light travel at about three hundred thousand kilometer per second.",
        "light have dual-a nature: ta be both wave and particle.",
        "white-a light be compose of seven color of rainbow.",
        "light can be reflect, refract, or absorb by object.",
        "plant use light for photosynthesis.",
        "light from sun take eight minute to reach earth.",
        "speed of light be one of fundamental-a constant in physics.",
        "light can be produce by sun, fire, electric-a bulb, or laser.",
        "without light, person can not see.",
    ]),
    ("sound", [
        "sound be vibration that travel through medium.",
        "sound travel at about 340 meter per second in air.",
        "sound can not travel through vacuum.",
        "human ear can hear sound between 20 and 20000 hertz.",
        "loudness of sound be measure in decibel.",
        "sound above 120 decibel can damage hearing.",
        "music be organize sound that be pleasant-a to hear.",
        "noise be unwanted-a sound.",
        "sound wave have frequency and amplitude.",
        "dolphin and bat use echolocation.",
    ]),
    ("dna", [
        "dna be molecule that contain genetic-a instruction for life.",
        "dna be find in cell of all living organism.",
        "dna have double-a helix structure, discover by watson and crick.",
        "dna be make of four base: a, t, g, c.",
        "sequence of base in dna determine genetic-a code.",
        "dna be pass from parent to offspring.",
        "gene be segment of dna that code for one protein.",
        "mutation in dna can cause disease or variation.",
        "dna testing can identify person and determine ancestry.",
        "human dna be about 99.9 percent identical-a between individual.",
    ]),
    ("evolution", [
        "evolution be process by which species change over generation.",
        "charles darwin propose theory of evolution by natural-a selection.",
        "individual with trait suited-a to environment survive more.",
        "evolution explain diversity of life on earth.",
        "human and chimpanzee share common-a ancestor about six million year ago.",
        "evolution be drive by mutation, gene flow, genetic-a drift, selection.",
        "fossil record provide evidence for evolution.",
        "antibiotic-a resistance be example of evolution in action.",
        "evolution be one of most well-a support-a theory in science.",
        "evolution not be goal-a oriented.",
    ]),
    ("climate", [
        "climate be long-a term-a average-a weather of one region.",
        "climate differ from weather, which be short-a term-a condition.",
        "main-a climate type: tropical, dry, temperate, continental, polar.",
        "climate be affect by latitude, altitude, ocean current, wind.",
        "climate change be one of most serious-a problem face by humanity.",
        "burning fossil-a fuel release carbon dioxide, cause global-a warming.",
        "global-a warming lead to sea level rise, extreme-a weather.",
        "paris-a agreement aim to limit global-a warming.",
        "renewable-a energy and forest-a protection help combat climate change.",
        "person must reduce carbon-a emission.",
    ]),
    ("ocean", [
        "ocean be vast-a body of salt water that cover about 71 percent of earth.",
        "ocean be divide into five: pacific, atlantic, indian, arctic, southern.",
        "pacific be largest-a and deepest-a ocean.",
        "ocean regulate earth-a climate by absorb heat and carbon dioxide.",
        "ocean produce about half of oxygen on earth through plankton.",
        "ocean be home to million of species.",
        "ocean current like gulf-a stream affect climate of coastal-a region.",
        "ocean be pollute by plastic, oil spill, and chemical-a waste.",
        "deep-a ocean be largely unexplored.",
        "ocean be essential-a for food, transport, and climate regulation.",
    ]),
    ("volcano", [
        "volcano be opening in earth-a crust through which magma erupt.",
        "magma be molten-a rock underground. lava be molten-a rock on surface.",
        "volcano be find at tectonic-a plate boundary.",
        "there be about 1500 active-a volcano in world.",
        "volcano can be active-a, dormant-a, or extinct-a.",
        "eruption can release ash, gas, lava, and rock.",
        "volcanic-a ash can disrupt air travel and affect climate.",
        "volcano can be dangerous-a, but also create new-a land.",
        "ring of fire be region around pacific-a ocean with many volcano.",
        "vesuvius destroy pompeii in 79 ad.",
    ]),
    ("earthquake", [
        "earthquake be shaking of ground cause by seismic-a wave.",
        "earthquake be cause by movement of tectonic-a plate.",
        "most earthquake occur at plate boundary.",
        "magnitude of earthquake be measure on richter-a scale.",
        "earthquake above 7 on richter-a scale be major-a.",
        "earthquake can cause building collapse, landslide, tsunami.",
        "seismograph be instrument that detect earthquake.",
        "person can not predict earthquake accurately.",
        "building in earthquake-a zone be design to withstand shaking.",
        "japan and california be prone-a to earthquake.",
    ]),
    ("tsunami", [
        "tsunami be series of large-a ocean-a wave cause by underwater-a disturbance.",
        "tsunami be often trigger by earthquake, volcano, or landslide.",
        "tsunami wave can travel at speed over 800 kilometer per hour.",
        "in deep-a water, tsunami wave be low-a and not noticeable.",
        "when wave approach shore, ta slow down and grow tall-a.",
        "tsunami can cause devastating-a flood in coastal-a area.",
        "warning-a system use buoy and seismic-a data to detect tsunami.",
        "person in coastal-a area should move to high-a ground after earthquake.",
        "2004 indian-a ocean-a tsunami kill about 230000 person.",
        "word tsunami come from japanese.",
    ]),
    ("rain-forest", [
        "rain-forest be forest with high-a rainfall.",
        "rain-forest be find near equator.",
        "amazon be largest-a rain-forest in world.",
        "rain-forest be home to about half of world-a plant and animal species.",
        "rain-forest be call lung of earth because ta produce oxygen.",
        "rain-forest be cut down for timber, agriculture, development.",
        "deforestation contribute to climate change and loss of biodiversity.",
        "many-a medicine be derive from plant in rain-forest.",
        "rain-forest have four layer: emergent, canopy, understory, forest floor.",
        "protect rain-forest be essential-a for global-a ecosystem.",
    ]),
    ("desert", [
        "desert be dry-a region with less than 250 millimeter rainfall per year.",
        "desert cover about one-third of earth-a land surface.",
        "largest-a desert be sahara in north africa.",
        "desert can be hot-a like sahara or cold-a like antarctica.",
        "temperature in desert vary extreme-a between day and night.",
        "desert plant like cactus be adapt-a to conserve water.",
        "desert animal like camel can survive long-a time without water.",
        "oasis be fertile-a area in desert.",
        "desert be form by atmospheric-a circulation and rain-a shadow.",
        "desert-a soil be poor-a in nutrient.",
    ]),
    ("river", [
        "river be one large-a natural-a stream of water.",
        "river begin at source, often in mountain, and end at mouth.",
        "longest-a river in world be nile, about 6600 kilometer.",
        "river provide fresh-a water for drink, irrigation, industry.",
        "river-a valley be often fertile-a and good-a for agriculture.",
        "many-a civilization develop along river.",
        "river can flood during heavy-a rain.",
        "dam be build on river to control flood and generate power.",
        "river-a current can be use for transport.",
        "pollution threaten river ecosystem.",
    ]),
    ("internet", [
        "internet be global-a network that connect billion of computer.",
        "internet be develop in 1960s as arpanet.",
        "world-a wide-a web be invent by tim-berners-lee in 1989.",
        "internet use protocol like tcp/ip for data transmission.",
        "person use internet for communication, information, commerce.",
        "email be one of oldest-a internet-a service.",
        "social-a media connect person globally.",
        "search-a engine help person find information.",
        "internet-a speed be measure in megabit per second.",
        "internet have transform-a society, economy, and culture.",
    ]),
    ("ai", [
        "artificial-a intelligence, or ai, be intelligence demonstrate by machine.",
        "ai be develop since 1950s.",
        "modern-a ai use machine-a learning, especially deep-a learning.",
        "neural-a network be inspire by structure of human-a brain.",
        "large-a language-a model can generate human-a-like-a text.",
        "ai be use in many field: medicine, finance, transport, entertainment.",
        "ai can perform task like image-a recognition, translation, game.",
        "concern about ai include job-a loss, bias, privacy, safety.",
        "agi be goal of some-a researcher.",
        "ai be one of most transformative-a technology of 21st century.",
    ]),
    ("photosynthesis", [
        "photosynthesis be process by which plant make food from sun-light.",
        "plant use sun-light, carbon dioxide, water to produce glucose and oxygen.",
        "photosynthesis occur in chloroplast.",
        "chlorophyll absorb light, reflect green-a light.",
        "photosynthesis be essential-a for life on earth.",
        "photosynthesis convert sun-a energy to chemical-a energy.",
        "equation: 6 CO2 + 6 H2O + light = glucose + 6 O2.",
        "without photosynthesis, atmosphere would lack oxygen.",
        "some-a bacteria also perform photosynthesis.",
        "photosynthesis be discover by jan-ingenhousz in 1779.",
    ]),
    ("respiration", [
        "respiration be process by which cell release energy from food.",
        "aerobic-a respiration use oxygen.",
        "anaerobic-a respiration not use oxygen.",
        "respiration occur in mitochondria of cell.",
        "respiration be opposite of photosynthesis.",
        "human breathe in oxygen for respiration.",
        "equation: glucose + 6 O2 = 6 CO2 + 6 H2O + energy.",
        "respiration release energy in form of atp.",
        "without respiration, cell can not produce energy and die.",
        "respiration be essential-a for all living-a organism.",
    ]),
    ("brain", [
        "brain be organ that control body and mind.",
        "brain be locate in head, protect by skull.",
        "human brain be about 1.4 kilogram.",
        "brain have about 86 billion neuron.",
        "brain consume about 20 percent of body-a energy.",
        "brain be divide into region: cerebrum, cerebellum, brainstem.",
        "cerebrum handle thinking, language, memory.",
        "cerebellum control movement and balance.",
        "brainstem control vital-a function like breathe, heart rate.",
        "brain be most complex-a known-a structure in universe.",
    ]),
    ("blood", [
        "blood be fluid that circulate through body.",
        "blood have four main-a component: red-a cell, white-a cell, platelet, plasma.",
        "red-a cell carry oxygen from lung to rest of body.",
        "white-a cell fight infection and disease.",
        "platelet help blood clot and stop bleeding.",
        "plasma be liquid-a part of blood, mostly water.",
        "person have about 5 liter of blood.",
        "blood type be classify as A, B, AB, O.",
        "blood be essential-a for transport nutrient, oxygen, waste.",
        "loss of too much blood can cause death.",
    ]),
]


def gen_knowledge_paragraph():
    """v4: with discourse markers enforced"""
    topic, facts = random.choice(KNOWLEDGE_TEMPLATES)
    first = facts[0]
    rest = facts[1:]
    random.shuffle(rest)
    n_facts = random.randint(3, min(5, len(rest)))
    selected = [first] + rest[:n_facts]
    # v4: insert discourse marker in middle
    if len(selected) >= 3:
        mid = len(selected) // 2
        disc = random.choice(DISCOURSE)
        selected[mid] = f"{disc}, {selected[mid].lower()}"
    # v4: add in-conclusion at end
    if random.random() < 0.4:
        selected.append(f"in-conclusion, {topic} be important-a for life and world.")
    return " ".join(selected)


# =========================================================================
# Natural reasoning (v4: not template, use because/so/therefore)
# =========================================================================
REASONING_TEMPLATES = [
    # 物理因果（自然语言）
    "because sun heat earth surface, water in sea evaporate and form vapor. when vapor rise and cool, ta condense into cloud. this lead to rain, which flow back to sea. so, water cycle be complete and essential-a for life.",
    "because ice molecule be lock in rigid-a structure, ta be solid-a. however, when heat apply, molecule gain energy and vibrate. at zero degree, vibration break structure, so ice melt and become water. this mean heat determine state of matter.",
    "because earth rotate on ta-a axis, sun appear to move across sky. when one side face sun, ta be day. meanwhile, other side be in shadow, be night. so, day and night be cause by earth-a rotation.",
    "because gravity pull object toward earth center, when object be drop, ta accelerate. ta gain speed at 9.8 meter per second square. so, after one second, speed be 9.8, after two second, 19.6. this mean falling object get faster-e.",
    "because metal have free-a electron, ta allow electricity to flow. however, plastic not have free-a electron, so ta block electricity. this be why electric-a wire have metal inside and plastic outside.",
    
    # 生物因果
    "because plant leaf contain chlorophyll, ta can absorb sun-light. ta use this energy to split water molecule. hydrogen combine with carbon dioxide to form glucose. meanwhile, oxygen be release. so, photosynthesis convert sun energy to food, which be essential-a for life.",
    "because person eat food, ta be digest in stomach. nutrient enter bloodstream and be deliver to cell. cell use oxygen to break down glucose, release energy. so, this process, call respiration, be how body get energy from food.",
    "because heart pump blood, oxygen reach every cell. cell use oxygen to produce energy. without oxygen, cell die within minute. so, heart be essential-a for life.",
    "because vaccine contain weaken-a pathogen, immune-a system learn to recognize ta. body produce antibody. so, when real-a pathogen enter, body can fight ta quickly-e. this mean vaccine train immune-a system without cause disease.",
    
    # 逻辑推理
    "all human be mortal. socrates be human. therefore, socrates be mortal. in-fact, this be classic-a syllogism. specifically, ta have form: all A be B, X be A, so X be B. this mean deductive-a reasoning be valid-a if premise be true-a.",
    "if a be greater than b, and b be greater than c, then a be greater than c. for-example, 5 > 3, and 3 > 1, so 5 > 1. this be call transitive-a property, which be fundamental-a in mathematics.",
    "if today be monday, then tomorrow be tuesday. today be monday. therefore, tomorrow be tuesday. this be modus ponens: if P then Q, P, so Q. ta be cornerstone of deductive-a logic.",
    
    # 数学推理
    "if x + 5 = 12, we subtract 5 from both side. so, x = 12 - 5 = 7. we can verify: 7 + 5 = 12, which be correct-a. therefore, x = 7 be solution.",
    "because sum of angle in triangle be 180 degree, if angle A = 60 and angle B = 70, then angle C = 180 - 60 - 70 = 50 degree. so, we can find unknown-a angle use angle-a sum property.",
    "even number be divisible by 2. zero divide by 2 equal 0, with no remainder. so, zero satisfy definition of even. meanwhile, zero not be odd. therefore, zero be even number, accept-a by mathematician.",
    
    # 社会因果
    "because education improve person-a knowledge and skill, ta can find better-e job. with better-e job, ta earn more money. this lead to better-e health and housing. so, education reduce poverty and promote social-a mobility.",
    "because government build more road, more person buy car. however, more car mean more traffic and pollution. so, simply-e build road not solve traffic problem. therefore, public-a transport be better-e long-a term-a solution.",
    "because internet connect person globally, information spread fast-e. this help learning and business. however, false-a information also spread fast-e. so, person need critical-a thinking to evaluate source. this mean internet be double-a edge-a sword.",
    
    # 科学方法
    "because scientist observe phenomenon, ta form hypothesis to explain ta. then ta design experiment to test hypothesis. if result support hypothesis, ta become theory. so, this be scientific-a method, which be foundation of modern-a science.",
    "because earth be warm-a, scientist observe temperature increase. ta correlate ta with carbon-a dioxide level. experiment confirm greenhouse-a effect. therefore, climate change be cause by human-a activity. this mean person must reduce emission.",
    
    # 历史
    "because printing press be invent in 15th century, book become cheaper-e. so, more person learn to read. this lead to spread of new-a idea. consequently, scientific-a revolution and enlightenment follow. therefore, printing press transform-a society.",
    "because industrial-a revolution begin, factory replace hand-a work. so, production increase dramatic-a-e. many person move from country to city. this lead to urban-a growth. consequently, social-a structure change fundamental-a-e.",
]


def gen_reasoning_paragraph():
    return random.choice(REASONING_TEMPLATES)


# =========================================================================
# Multi-turn Q&A from SFT data
# =========================================================================
def gen_qa_paragraph():
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
        ("solve", "math-problem", ["read problem careful-e", "write down given-a information", "choose appropriate-a formula", "substitute value into formula", "calculate step by step", "verify you-a answer", "write final-a answer with unit"]),
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
            sentence_with_discourse,
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
    (gen_knowledge_paragraph, 0.28),  # 知识科普 28% (1.5x)
    (gen_reasoning_paragraph, 0.15),  # 推理 15%
    (gen_math_paragraph, 0.15),       # 数学 15%
    (gen_qa_paragraph, 0.12),         # Q&A 12%
    (gen_dialogue, 0.08),             # 对话 8%
    (gen_narrative, 0.08),
    (gen_instruction, 0.07),
    (gen_news, 0.05),
    (gen_poem, 0.02),
]


def gen_paragraph():
    r = random.random()
    acc = 0
    for gen, p in GENRES:
        acc += p
        if r < acc:
            return gen()
    return gen_knowledge_paragraph()


def gen_corpus(target_bytes=15 * 1024 * 1024):
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
    target = 15 * 1024 * 1024
    print(f"Generating Logiko v6 corpus (~{target/1024/1024:.1f} MB)...")
    corpus = gen_corpus(target)
    out_path = "/home/z/my-project/download/logiko_corpus.txt"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(corpus)
    actual = os.path.getsize(out_path)
    print(f"Done. Wrote {actual} bytes ({actual/1024/1024:.2f} MB)")
    print(f"Stats: {len(corpus)} chars, {len(corpus.split())} words")


if __name__ == "__main__":
    main()
