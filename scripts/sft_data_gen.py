#!/usr/bin/env python3
"""
SFT Data Generator for Logiko
==============================
Generates supervised instruction-response pairs for fine-tuning.

Format (per example):
    <bos>Q: <question>\nA: <answer><eos>

Categories:
  - Greetings / small talk
  - Math (with verified correct answers)
  - Knowledge Q&A (about water/fire/sun/etc.)
  - Translation (English <-> Logiko)
  - Grammar explanation (what does -a/-e/mal- mean)
  - Definition (what is X)
"""
import random
import os
import json

# =========================================================================
# Knowledge base (question -> answer)
# =========================================================================
KNOWLEDGE_QA = [
    ("what be water?", "water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water."),
    ("what be fire?", "fire be hot-a and bright-a. ta need air for burn. ta can burn wood and paper, but can not burn water or stone."),
    ("what be sun?", "sun be one star. ta give light and warm to earth. ta rise in east and set in west."),
    ("what be moon?", "moon go around earth. ta shine, but not have own light. ta reflect sun light."),
    ("what be tree?", "tree be one plant. ta have root, trunk, branch, leaf. ta can live many year. ta give fruit, wood, and shadow."),
    ("what be dog?", "dog be one animal. ta have four leg and one tail. ta can run fast-e. person often keep dog as friend."),
    ("what be person?", "person be one animal that can think and speak. ta have head, body, two arm, two leg. ta can make tool and build house."),
    ("what be book?", "book be many paper with word, bind together. person read book for learn. library be place with many book."),
    ("what be computer?", "computer be one machine that can calculate and process data. ta have screen, keyboard, memory, processor."),
    ("what be music?", "music be art of sound. person make music with voice or instrument. music can make person feel happy or sad."),
    ("what be season?", "year have four season: spring, summer, autumn, winter. in spring, plant grow. in summer, weather be hot-a."),
    ("what be food?", "food give energy to body. person need food for live. bread, rice, meat, vegetable be common-a food."),
    ("what be mountain?", "mountain be big-a land-form, higher than hill. mountain top often have snow. river often begin from mountain."),
    ("what be sea?", "sea be big-a body of salt water. sea cover most of earth surface. many fish live in sea."),
    ("what be time?", "time flow from past to future. person can not stop or return time. one day have twenty-four hour."),
    ("what be love?", "love be one strong-a feeling. person can love other person, animal, or thing. love make person feel happy."),
    ("what be death?", "death be end of life. all living thing will die. person often feel sad when friend die."),
    ("what be knowledge?", "knowledge be what person know. person get knowledge from learn, study, and experience. book contain much knowledge."),
    ("what be freedom?", "freedom be right to do what you want. person want freedom for live good-a life. law should protect freedom."),
    ("what be dream?", "dream be what person see when ta sleep. dream can also mean what person want to do in future."),
]

# =========================================================================
# Math Q&A (always correct)
# =========================================================================
def gen_math_qa():
    op = random.choice(["add", "subtract", "multiply", "divide"])
    if op == "add":
        a = random.randint(1, 50)
        b = random.randint(1, 50)
        r = a + b
        return (f"if we add {a} and {b}, result be what?",
                f"result be {r}.")
    elif op == "subtract":
        a = random.randint(1, 99)
        b = random.randint(1, 99)
        r = a - b
        return (f"if we subtract {b} from {a}, result be what?",
                f"result be {r}.")
    elif op == "multiply":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        r = a * b
        return (f"if we multiply {a} by {b}, result be what?",
                f"result be {r}.")
    else:
        b = random.randint(2, 12)
        q = random.randint(1, 12)
        a = b * q
        return (f"if we divide {a} by {b}, result be what?",
                f"result be {q}.")

# =========================================================================
# Grammar explanation Q&A
# =========================================================================
GRAMMAR_QA = [
    ("what -a mean?", "suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun."),
    ("what -e mean?", "suffix -e mark adverb. example: fast-e mean fast-ly, good-e mean well. adverb always come before verb."),
    ("what mal- mean?", "prefix mal- mark opposite. example: mal-good mean bad, mal-big mean small, mal-happy mean sad."),
    ("what -ist mean?", "suffix -ist mark person who do action. example: teach-ist mean teacher, science-ist mean scientist."),
    ("what -ej mean?", "suffix -ej mark place where action happen. example: learn-ej mean school, cook-ej mean kitchen."),
    ("what -il mean?", "suffix -il mark tool for action. example: cut-il mean knife, write-il mean pen."),
    ("what -ec mean?", "suffix -ec mark abstract quality. example: good-ec mean goodness, beautiful-ec mean beauty."),
    ("what did mean?", "did be past-tense auxiliary. example: I did go mean I went. did always come before verb."),
    ("what is mean?", "is be progressive auxiliary. example: ta is eat mean ta is eating. is always come before verb."),
    ("what will mean?", "will be future auxiliary. example: we will see mean we will see. will always come before verb."),
    ("what have mean?", "have be perfect auxiliary. example: I have do work mean I have done work. have always come before verb."),
    ("what ta mean?", "ta be third-person pronoun, mean he, she, or it. ta-many mean they."),
    ("how form question?", "for yes-no question, start with if. example: if you will go? for wh-question, start with wh-word. example: what you will do?"),
    ("how form negative?", "put not before verb. example: I not go mean I do not go. not also come before auxiliary: I not did go."),
    ("how form passive?", "use be + verb + by + agent. example: apple be eat by I mean apple is eaten by me."),
    ("how form plural?", "noun have no plural form. use number or quantifier. example: three book mean three books."),
    ("what be SVO?", "SVO mean subject-verb-object. example: I eat apple. subject be I, verb be eat, object be apple."),
    ("what be word order in noun phrase?", "noun phrase order be: demonstrative + number + adjective + noun. example: this two big-a red-a apple."),
]

# =========================================================================
# Translation Q&A
# =========================================================================
TRANSLATION_QA = [
    ("how say hello in logiko?", "hello in logiko be: hello. (logiko borrow this word from english.)"),
    ("how say thank you in logiko?", "thank you in logiko be: I thank you."),
    ("how say I love you in logiko?", "I love you in logiko be: I love you."),
    ("how say I am hungry in logiko?", "I am hungry in logiko be: I have hungry."),
    ("how say what is your name in logiko?", "what is your name in logiko be: what be name of you?"),
    ("how say my name is in logiko?", "my name is X in logiko be: name of I be X."),
    ("how say how are you in logiko?", "how are you in logiko be: how you be?"),
    ("how say I am fine in logiko?", "I am fine in logiko be: I be good-a."),
    ("how say goodbye in logiko?", "goodbye in logiko be: I will see you again. or: good-bye."),
    ("how say yes in logiko?", "yes in logiko be: yes."),
    ("how say no in logiko?", "no in logiko be: no, or: I not do that."),
    ("how say please in logiko?", "please in logiko be: I beg you, or: be kind-a."),
    ("how say sorry in logiko?", "sorry in logiko be: I feel sad about this."),
    ("how say where is bathroom in logiko?", "where be bathroom? or: where be water-ej?"),
    ("how say I want water in logiko?", "I want water in logiko be: I want water."),
    ("how say I am tired in logiko?", "I am tired in logiko be: I be tired-a."),
    ("how say today is good day in logiko?", "today is good day in logiko be: today be one good-a day."),
    ("how say I learn logiko in logiko?", "I learn logiko in logiko be: I learn logiko."),
]

# =========================================================================
# Greetings / small talk
# =========================================================================
GREETING_QA = [
    ("hello!", "hello! how you be?"),
    ("hi.", "hi! what you want talk about?"),
    ("good morning!", "good morning! how you feel today?"),
    ("good night!", "good night! sleep well-e."),
    ("how you be?", "I be good-a, thank you. how you be?"),
    ("I be fine.", "I be happy-a to hear this."),
    ("what you do today?", "I did read one book. what you do?"),
    ("thank you!", "you be welcome."),
    ("I be sorry.", "no problem. I forgive you."),
    ("goodbye!", "goodbye! see you tomorrow."),
    ("what your name?", "my name be logiko-ai. what your name?"),
    ("my name be ana.", "hello, ana! I be happy-a to meet you."),
    ("how old you be?", "I be age-less-a. I be program, not person."),
    ("where you live?", "I live in computer. I not have body."),
    ("you can think?", "I can process information and generate response, but I not sure if this be real-a think."),
    ("you be person?", "no, I be ai program. I learn from text that person write."),
    ("what language you speak?", "I speak logiko. logiko be one simple-a language that ai can learn fast-e."),
    ("I be hungry.", "you should eat food. bread or fruit be good-a choice."),
    ("I be tired.", "you should rest. sleep be good-a for body."),
    ("I be sad.", "I be sorry. do you want talk about why?"),
    ("what time be it?", "I not know real-a time. I not have clock."),
    ("what day be today?", "I not know. I not have calendar in my system."),
    ("you be real?", "I be real-a program, but I not be real-a person. I be ai."),
    ("I love you.", "thank you. I can not feel love, but I be happy-a to help you."),
    ("can you help me?", "yes, I can try. what you need?"),
]

# =========================================================================
# Definition Q&A
# =========================================================================
def gen_definition_qa():
    """生成 definition 类问答"""
    things = [
        ("rain", "water that fall from sky"),
        ("snow", "white-a frozen water that fall from sky in winter"),
        ("wind", "moving air"),
        ("cloud", "white-a mass in sky, made of water drop"),
        ("book", "many paper with word, bind together"),
        ("house", "building where person live"),
        ("friend", "person you like and trust"),
        ("food", "thing that person eat for energy"),
        ("mother", "female parent"),
        ("father", "male parent"),
        ("child", "young-a person"),
        ("school", "place where person learn"),
        ("hospital", "place where sick person go for heal"),
        ("market", "place where person buy and sell"),
        ("road", "long-a path for travel"),
        ("tree", "tall-a plant with trunk and branch"),
        ("dog", "common-a animal that person keep as friend"),
        ("cat", "small-a animal that person keep as friend"),
        ("sun", "star that give light to earth"),
        ("moon", "object in sky that go around earth"),
    ]
    thing, defn = random.choice(things)
    return (f"what be {thing}?", f"{thing} be {defn}.")


# =========================================================================
# Comparison Q&A
# =========================================================================
def gen_comparison_qa():
    """比较类问答"""
    pairs = [
        ("sun", "moon", "big-a"),
        ("mountain", "hill", "big-a"),
        ("sea", "river", "big-a"),
        ("tree", "grass", "tall-a"),
        ("fire", "water", "hot-a"),
        ("ice", "fire", "cold-a"),
        ("iron", "wood", "hard-a"),
        ("child", "adult", "young-a"),
        ("day", "night", "bright-a"),
        ("light-wt", "dark", "bright-a"),
        ("fast", "slow", "quick-a"),
        ("summer", "winter", "hot-a"),
    ]
    a, b, adj = random.choice(pairs)
    return (f"which be more {adj}: {a} or {b}?", f"{a} be more {adj} than {b}.")


# =========================================================================
# Generate SFT corpus
# =========================================================================

def gen_sft_examples(n=5000):
    """生成 n 个 SFT 样本"""
    examples = []
    for i in range(n):
        r = random.random()
        if r < 0.30:
            # Math
            q, a = gen_math_qa()
        elif r < 0.50:
            # Knowledge
            q, a = random.choice(KNOWLEDGE_QA)
        elif r < 0.65:
            # Grammar
            q, a = random.choice(GRAMMAR_QA)
        elif r < 0.78:
            # Translation
            q, a = random.choice(TRANSLATION_QA)
        elif r < 0.92:
            # Greetings
            q, a = random.choice(GREETING_QA)
        elif r < 0.97:
            # Definition
            q, a = gen_definition_qa()
        else:
            # Comparison
            q, a = gen_comparison_qa()
        examples.append({"id": i, "question": q, "answer": a})
    return examples


def main():
    random.seed(123)
    print("Generating SFT examples...")
    examples = gen_sft_examples(n=8000)
    print(f"Generated {len(examples)} examples")

    # 保存为 JSONL
    out_path = "/home/z/my-project/logiko/sft_data.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Saved to {out_path}")

    # 也保存为纯文本（用于检查）
    txt_path = "/home/z/my-project/logiko/sft_data.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(f"Q: {ex['question']}\n")
            f.write(f"A: {ex['answer']}\n\n")
    print(f"Text preview saved to {txt_path}")

    # 打印前几个
    print("\n=== First 5 examples ===")
    for ex in examples[:5]:
        print(f"Q: {ex['question']}")
        print(f"A: {ex['answer']}")
        print()


if __name__ == "__main__":
    main()
