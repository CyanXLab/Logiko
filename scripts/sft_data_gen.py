#!/usr/bin/env python3
"""
SFT Data Generator v2 (Logiko v2.0)
====================================
Improvements:
  - Multi-turn conversations (40% of data)
  - Answer variants (each knowledge item has 2-3 phrasings)
  - New language rules: cu for yes/no, I-a for possessive, past/fut for tense
  - Affix fusion: teachist (not teach-ist), learnej (not learn-ej), teauc (not tea-ing)
  - Math Q&A with verified correct answers
"""
import random
import os
import json

# =========================================================================
# Knowledge base (with multiple phrasing variants per topic)
# =========================================================================
KNOWLEDGE_TOPICS = [
    {
        "topic": "water",
        "variants": [
            "water be one clear-a liquid. ta freeze in zero degree, and boil in hundred degree. all life need water.",
            "water be transparent-a liquid without color or taste. ta become ice in cold-a place, and steam in hot-a place. every living thing need ta.",
            "water be one simple-a substance that cover most of earth. ta be essential-a for life. ta freeze at zero degree and boil at hundred degree.",
        ],
        "followups": [
            ("cu ta boil in hundred degree?", "yes, exactly. ta boil in hundred degree and become steam."),
            ("how about ice?", "ice be solid-a water. ta form when water freeze in zero degree."),
            ("cu all life need water?", "yes, all life need water for live. without water, life die."),
            ("where can person find water?", "person can find water in river, lake, sea, and rain. sea water be salt, so person can not drink ta."),
        ],
    },
    {
        "topic": "fire",
        "variants": [
            "fire be hot-a and bright-a. ta need air for burn. ta can burn wood, paper, cloth, but can not burn water or stone.",
            "fire be one chemical-a reaction that release heat and light. ta require fuel, heat, and air. without air, fire die.",
            "fire be rapid-a oxidation. ta produce heat, light, and smoke. person use fire for cook, warm, and light.",
        ],
        "followups": [
            ("cu ta need air?", "yes, fire need air for burn. if you cover fire, ta die because no air."),
            ("what can ta burn?", "ta can burn wood, paper, cloth, oil. but ta can not burn water, stone, or metal."),
            ("how person use fire?", "person use fire for cook food, warm body in winter, give light in night, and scare animal."),
            ("cu fire be dangerous?", "yes, fire can be dangerous-a if not control. ta can burn house and hurt person."),
        ],
    },
    {
        "topic": "sun",
        "variants": [
            "sun be one star. ta give light and warm to earth. ta rise in east and set in west. all plant need sun-light for grow.",
            "sun be center of we-a solar system. ta be one big-a ball of hot-a gas. ta give energy that sustain all life on earth.",
            "sun be nearest star to earth. ta be about one hundred fifty million kilometer away. ta light take eight minute to reach earth.",
        ],
        "followups": [
            ("cu ta rise in east?", "yes, sun rise in east and set in west, because earth rotate."),
            ("how far ta be from earth?", "sun be about one hundred fifty million kilometer from earth. ta light take eight minute to arrive."),
            ("why all plant need ta?", "plant need sun-light for photosynthesis. without sun, plant die, and animal that eat plant also die."),
            ("cu ta be star?", "yes, sun be one star. ta be one of hundred billion star in we-a galaxy."),
        ],
    },
    {
        "topic": "moon",
        "variants": [
            "moon be earth-a only natural satellite. ta go around earth about one month. ta shine, but not have own light. ta reflect sun.",
            "moon be one rocky body that orbit earth. ta be about four hundred thousand kilometer away. ta have four phase: new, first-quarter, full, last-quarter.",
            "moon be fifth largest moon in solar system. ta have no air and no water. ta surface be cover with crater.",
        ],
        "followups": [
            ("cu ta have own light?", "no, moon not have own light. ta reflect sun light. that be why ta shine in night."),
            ("how long ta take to orbit earth?", "moon take about twenty-seven day to orbit earth once."),
            ("cu person can live on moon?", "no, person can not live on moon long-a time, because ta have no air and no water."),
            ("why ta change shape?", "moon change shape because we see different part of ta lit by sun. ta four main phase."),
        ],
    },
    {
        "topic": "tree",
        "variants": [
            "tree be one tall-a plant with wood trunk, branch, and leaf. ta have root in ground. ta can live many year, even hundred year.",
            "tree be one perennial plant. ta absorb water and nutrient through root, and sun-light through leaf. ta give fruit, wood, and shadow.",
            "tree be largest type of plant. ta make oxygen through photosynthesis. forest be place with many tree.",
        ],
        "followups": [
            ("what part ta have?", "tree have root, trunk, branch, leaf, and sometimes fruit. root hold ta in ground and take water."),
            ("how long ta can live?", "tree can live many year. some tree live over thousand year, like bristlecone pine."),
            ("why ta be important?", "tree be important because ta make oxygen, give fruit and wood, hold soil, and provide home for animal."),
            ("cu ta make oxygen?", "yes, tree make oxygen through photosynthesis. leaf take in carbon dioxide and release oxygen."),
        ],
    },
    {
        "topic": "dog",
        "variants": [
            "dog be one domestic-a animal. ta be descendant of wolf. ta be loyal-a friend of person. ta can bark, run fast-e, and smell well-e.",
            "dog be one mammal that person keep as pet or worker. ta have four leg, sharp-a tooth, and good-a sense of smell. ta live about ten to fifteen year.",
            "dog be one intelligent-a animal. person use ta for hunt, guard, guide, herd, and companion. ta be social animal that live in pack.",
        ],
        "followups": [
            ("cu ta can smell well-e?", "yes, dog can smell about thousand time better-e than person. that be why person use ta for search and detect."),
            ("how long ta live?", "dog live about ten to fifteen year, depend on breed and size. small-a dog usually live longer-a."),
            ("what ta eat?", "dog eat meat, but can also eat rice, vegetable, and special-a dog food. ta should not eat chocolate or onion."),
            ("cu ta be intelligent?", "yes, dog be intelligent-a. ta can learn command, recognize person, and understand human emotion."),
        ],
    },
    {
        "topic": "person",
        "variants": [
            "person be one intelligent-a animal. ta have big-a brain, can think, speak, and create tool. ta live in society and have culture.",
            "person, or human, be one species of primate. ta walk on two leg, have opposable thumb, and use complex-a language. ta inhabit every continent.",
            "person be only known-a species that build advanced-a civilization. ta develop science, art, religion, and technology over thousand of year.",
        ],
        "followups": [
            ("what make person special?", "person be special because ta have big-a brain, complex-a language, and can create tool and culture."),
            ("cu ta be animal?", "yes, person be one type of animal, specifically one mammal and primate. but person have unique-a cognitive ability."),
            ("how long ta live?", "person live about seventy to eighty year on average. some live over hundred year."),
            ("where ta live?", "person live on every continent of earth. ta build city, village, and town."),
        ],
    },
    {
        "topic": "music",
        "variants": [
            "music be art of organize sound in time. person make music with voice or instrument. ta can express emotion and tell story.",
            "music be one form of art that use sound and silence. ta have element like rhythm, melody, and harmony. ta exist in every culture.",
            "music be one universal-a language. ta can make person feel happy, sad, calm, or excited. common-a instrument include piano, guitar, drum.",
        ],
        "followups": [
            ("what instrument person use?", "person use many instrument: piano, guitar, violin, drum, flute, trumpet. each have unique-a sound."),
            ("cu ta exist in every culture?", "yes, every culture have some form of music. ta be part of human expression since ancient time."),
            ("how ta affect emotion?", "music affect emotion through rhythm, melody, and harmony. slow-e music can calm, fast-e music can excite."),
            ("cu ta be universal?", "yes, music be universal-a. even if you not understand language, you can still enjoy music from other culture."),
        ],
    },
    {
        "topic": "book",
        "variants": [
            "book be one collection of page with word, bind together. person write book for record knowledge, tell story, or express idea. library be place with many book.",
            "book be one medium for store and share information. before book exist, person tell story by speak. now, person can also read book in computer or phone.",
            "book be one of most important-a invention of human. ta allow knowledge to persist across time. person can read book for learn, enjoy, or inspire.",
        ],
        "followups": [
            ("what be library?", "library be one place that collect many book. person can borrow book from library for read at home."),
            ("cu person can read book in computer?", "yes, now person can read electronic-a book in computer, phone, or special-a reader device."),
            ("why book be important?", "book be important because ta allow knowledge to persist. without book, knowledge disappear when person die."),
            ("what type of book exist?", "many type exist: novel, textbook, biography, poetry, science, history, and more."),
        ],
    },
    {
        "topic": "food",
        "variants": [
            "food be what person eat for get energy and nutrient. ta include fruit, vegetable, meat, grain, and dairy. person need food for live.",
            "food be substance that provide energy to body. different-a culture have different-a food tradition. fresh-a food be better-e than process-a food.",
            "food be essential-a for life. ta give body fuel to function. common-a food: bread, rice, meat, fish, vegetable, fruit, milk.",
        ],
        "followups": [
            ("what be common-a food?", "common-a food include bread, rice, meat, fish, vegetable, fruit, milk, egg. different-a region have different-a staple."),
            ("cu person need food for live?", "yes, person need food for get energy. without food, person die after some week."),
            ("what make food healthy?", "fresh-a food with variety of vegetable, fruit, and protein be healthy. too much sugar or fat be unhealthy."),
            ("how person cook food?", "person cook food by boil, fry, bake, steam, or grill. cooking kill bacteria and make food easier to digest."),
        ],
    },
    {
        "topic": "season",
        "variants": [
            "year have four season: spring, summer, autumn, winter. ta change because earth tilt on ta-a axis while ta orbit sun.",
            "season be four division of year base on weather. spring be warm-a and plant grow. summer be hot-a. autumn be cool-a and leaf fall. winter be cold-a.",
            "season result from earth-a axial tilt. when one hemisphere tilt toward sun, ta have summer. when ta tilt away, ta have winter.",
        ],
        "followups": [
            ("why ta change?", "season change because earth tilt on ta-a axis. as earth orbit sun, different-a part get more or less sun-light."),
            ("what happen in spring?", "in spring, weather become warm-a, snow melt, plant begin to grow, and flower bloom."),
            ("cu ta be same everywhere?", "no, season be different-a in different-a place. near equator, season be less obvious. near pole, ta be extreme."),
            ("which season you like?", "i not have personal-a preference, but many person like spring because flower bloom and weather be pleasant."),
        ],
    },
    {
        "topic": "computer",
        "variants": [
            "computer be one electronic-a machine that process data. ta have hardware like cpu, memory, storage, and software like operating system and application.",
            "computer be one machine that can calculate, store, and process information at high speed. modern-a computer can connect to other computer through internet.",
            "computer be one of most important-a invention. ta can do calculation million time faster than person. ta be use in every field: science, business, education, entertainment.",
        ],
        "followups": [
            ("what be ta-a main part?", "computer main part be cpu for calculate, memory for store data temporarily, storage for keep data permanently, and input-output device."),
            ("cu ta can connect to other computer?", "yes, computer can connect to other computer through network. internet be global-a network of computer."),
            ("what be program?", "program be set of instruction that tell computer what to do. ta be write in programming language."),
            ("how fast ta can calculate?", "modern-a computer can do billion of calculation per second. supercomputer can do quadrillion."),
        ],
    },
    {
        "topic": "time",
        "variants": [
            "time be one dimension in which event occur in sequence. ta flow from past, through present, to future. person can not stop or reverse ta.",
            "time be one fundamental-a quantity. ta be measure in second, minute, hour, day, year. one day have twenty-four hour, one year about three hundred sixty-five day.",
            "time be one of most mysterious-a concept in physics. ta be relative-a, according to einstein-a theory. ta can slow down at high speed.",
        ],
        "followups": [
            ("can person stop ta?", "no, person can not stop or reverse time. ta flow forward always."),
            ("how person measure ta?", "person measure time with clock, watch, calendar. unit be second, minute, hour, day, month, year."),
            ("cu ta be relative?", "yes, according to einstein-a relativity theory, time can slow down at high speed or in strong-a gravity."),
            ("why ta be important?", "time be important because all event happen in time. without time, cause and effect not exist."),
        ],
    },
    {
        "topic": "mountain",
        "variants": [
            "mountain be one large-a landform that rise high above surround area. ta form through tectonic force over million of year. ta often have snow on top.",
            "mountain be one elevated-a landform. ta be taller than hill. ta create by earth-a tectonic plate collide. everest be highest mountain on earth.",
            "mountain be one of earth-a most majestic-a feature. ta affect climate, provide freshwater, and host diverse-a ecosystem. many river originate from mountain.",
        ],
        "followups": [
            ("what be highest mountain?", "mount everest be highest mountain on earth, about eight thousand eight hundred meter high."),
            ("how ta form?", "mountain form when tectonic plate collide and push up crust. ta take million of year."),
            ("cu ta have snow on top?", "yes, high-a mountain have snow on top, even in summer, because temperature decrease with altitude."),
            ("why ta be important?", "mountain be important because ta store freshwater as snow and ice, host biodiversity, and affect weather pattern."),
        ],
    },
    {
        "topic": "sea",
        "variants": [
            "sea be one vast-a body of salt water that cover about seventy percent of earth-a surface. ta be home to million of species, from tiny plankton to big-a whale.",
            "sea be connect body of salt water that form world-a ocean. ta be divide into pacific, atlantic, indian, arctic, and southern. ta regulate earth-a climate.",
            "sea be largest body of water on earth. ta be salt, so person can not drink ta. ta provide food, transport, and oxygen through plankton.",
        ],
        "followups": [
            ("cu person can drink sea water?", "no, person can not drink sea water because ta be too salt. drink sea water can dehydrate body and cause death."),
            ("what live in sea?", "many creature live in sea: fish, whale, dolphin, shark, octopus, jellyfish, coral, plankton. ta be vast-a ecosystem."),
            ("how deep ta be?", "sea average depth be about four kilometer. deepest point be mariana trench, about eleven kilometer deep."),
            ("why ta be important?", "sea be important because ta provide food, regulate climate, produce oxygen, and enable transport between continent."),
        ],
    },
]


# =========================================================================
# Grammar explanations (with variants)
# =========================================================================
GRAMMAR_TOPICS = [
    {
        "topic": "-a suffix",
        "question": "what -a mean?",
        "variants": [
            "suffix -a mark adjective. example: big-a mean big, red-a mean red. adjective always come before noun.",
            "-a be adjective marker. when you add -a to one root, ta become adjective. like good-a, beautiful-a, I-a mean my.",
            "-a be one suffix that turn any root into adjective. ta also mark possessive: I-a mean my, ta-a mean his or her or its.",
        ],
    },
    {
        "topic": "-e suffix",
        "question": "what -e mean?",
        "variants": [
            "suffix -e mark adverb. example: fast-e mean fast-ly, good-e mean well. adverb always come before verb.",
            "-e be adverb marker. ta turn root into adverb. like quick-e, careful-e, happy-e.",
            "-e be adverb-forming suffix. ta similar to english -ly. adverb modify verb and usually precede ta.",
        ],
    },
    {
        "topic": "mal- prefix",
        "question": "what mal- mean?",
        "variants": [
            "prefix mal- mark opposite. example: mal-good mean bad, mal-big mean small, mal-happy mean sad.",
            "mal- be one prefix that create antonym. ta save half of vocabulary. instead of learn both good and bad, you learn good and mal-good.",
            "mal- be opposite marker. ta very efficient-a: instead of memorize separate-a word for antonym, you just add mal-.",
        ],
    },
    {
        "topic": "-ist suffix",
        "question": "what -ist mean?",
        "variants": [
            "suffix -ist mark person who do action or specialize in field. example: teachist mean teacher, scientist mean scientist, artist mean artist.",
            "-ist be one suffix that form noun for person. ta fuse directly with root, no hyphen. like teachist, learnist, paintist.",
            "-ist create agent noun. ta indicate one person who practice or study something. example: science-ist, art-ist, music-ist.",
        ],
    },
    {
        "topic": "-ej suffix",
        "question": "what -ej mean?",
        "variants": [
            "suffix -ej mark place where action happen. example: learnej mean school, cookej mean kitchen, healej mean hospital.",
            "-ej be one suffix that form place noun. ta fuse directly: learnej, workej, sleepej.",
            "-ej indicate location. ta useful for name building: learnej for school, cookej for kitchen, healej for hospital.",
        ],
    },
    {
        "topic": "-il suffix",
        "question": "what -il mean?",
        "variants": [
            "suffix -il mark tool for action. example: cutil mean knife, writeil mean pen, seeil mean microscope or glass.",
            "-il be tool-forming suffix. ta fuse directly: cutil, writeil, cutil.",
            "-il indicate instrument. ta show what tool person use to do action. like cut-il for knife, write-il for pen.",
        ],
    },
    {
        "topic": "-uc suffix (v2)",
        "question": "what -uc mean?",
        "variants": [
            "suffix -uc mark container. example: teauc mean teacup, saltuc mean salt shaker, moneyuc mean wallet. ta replace old -ing to avoid confusion with english -ing.",
            "-uc be one suffix for container noun. ta come from esperanto ujo. example: teauc, sugaruc, wateruc.",
            "-uc indicate container or vessel. ta be new in v2, replace -ing. like teauc for teacup, saltuc for salt shaker.",
        ],
    },
    {
        "topic": "cu (yes/no question)",
        "question": "what cu mean?",
        "variants": [
            "cu be one particle that mark yes-no question. ta come at start of sentence. example: cu you will go? mean will you go? ta replace old if to avoid confusion with conditional if.",
            "cu be question marker for yes-no question, similar to esperanto ĉu. ta precede sentence. like cu ta did eat? mean did he eat?",
            "cu be one special-a word for yes-no question. ta avoid confusion with if, which only mean condition in v2. example: cu you be student? mean are you student?",
        ],
    },
    {
        "topic": "past tense",
        "question": "how form past tense?",
        "variants": [
            "for past tense, you can use auxiliary did before verb, or use time adverb past. example: I did eat. or I past eat. both mean I ate.",
            "past tense in logiko be form by auxiliary did or adverb past. v2 prefer past for complex-a tense, like past is eat for was eating.",
            "to form past, put did or past before verb. verb stay in base form. like I did go, ta past eat, we did see.",
        ],
    },
    {
        "topic": "future tense",
        "question": "how form future tense?",
        "variants": [
            "for future tense, use auxiliary will or adverb fut before verb. example: I will go. or I fut go. both mean I will go.",
            "future be form by will or fut. like we will see, ta fut come, ta-many will arrive.",
            "to express future, put will or fut before verb. verb remain base form. example: I will eat, ta fut leave, we will travel.",
        ],
    },
    {
        "topic": "ta pronoun",
        "question": "what ta mean?",
        "variants": [
            "ta be third-person singular pronoun, mean he, she, or it. ta-many mean they. ta eliminate gender distinction in pronoun.",
            "ta be one gender-neutral pronoun. ta can refer to person, animal, or thing. ta-many be plural form, mean they.",
            "ta replace he, she, and it in logiko. ta-many mean they. ta make language more equal-a by not assume gender.",
        ],
    },
    {
        "topic": "possessive I-a",
        "question": "how say my in logiko?",
        "variants": [
            "for possessive, add -a to pronoun. I-a mean my, you-a mean your, ta-a mean his/her/its, we-a mean our, ta-many-a mean their.",
            "possessive be form by add -a to pronoun, since -a be adjective suffix. so I-a mean my, ta-a mean his. ta be efficient-a: one word instead of two.",
            "to say my, you, his, just add -a: I-a, you-a, ta-a. ta-a also mean her and its. we-a mean our, ta-many-a mean their.",
        ],
    },
    {
        "topic": "negative",
        "question": "how form negative?",
        "variants": [
            "put not before verb or auxiliary. example: I not go mean I do not go. ta not did eat mean he did not eat. we not will come mean we will not come.",
            "negative be form by insert not before verb. ta also work with auxiliary: not did, not is, not will, not have.",
            "to negate, place not before verb or auxiliary. like I not eat, ta not is sleep, we not will go. simple-a and consistent-a.",
        ],
    },
    {
        "topic": "passive voice",
        "question": "how form passive?",
        "variants": [
            "use be + verb + by + agent. example: apple be eat by I mean apple is eaten by me. book be write by ta mean book is written by him.",
            "passive voice be form by be, then verb base form, then by, then agent. like work be finish by we, house be build by ta.",
            "to form passive, structure be: subject + be + verb + by + agent. example: apple be eat by I, letter be write by ta.",
        ],
    },
    {
        "topic": "plural",
        "question": "how form plural?",
        "variants": [
            "noun have no plural form in logiko. use number or quantifier instead. example: three book mean three books, many person mean many people, all animal mean all animals.",
            "plural be indicate by number or quantifier, not by suffix. like one book, three book, many book, all book. ta simplify morphology.",
            "logiko noun not change for plural. you just add number: one book, two book, ten book. or quantifier: many book, few book, all book.",
        ],
    },
    {
        "topic": "word order",
        "question": "what be word order in logiko?",
        "variants": [
            "logiko use strict-a SVO order: subject + verb + object. example: I eat apple. ta do work. we see bird. ta be same as english and chinese.",
            "word order in logiko be SVO. subject come first, then verb, then object. modifier always come before what ta modify.",
            "logiko be SVO language. ta mean subject-verb-object. like I eat apple, ta read book. adjective come before noun, adverb before verb.",
        ],
    },
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
                f"result be {r}. {a} plus {b} equal {r}.",
                f"{a} + {b} = {r}.",
                f"answer be {r}.")
    elif op == "subtract":
        a = random.randint(1, 99)
        b = random.randint(1, 99)
        r = a - b
        return (f"if we subtract {b} from {a}, result be what?",
                f"result be {r}. {a} minus {b} equal {r}.",
                f"{a} - {b} = {r}.",
                f"answer be {r}.")
    elif op == "multiply":
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        r = a * b
        return (f"if we multiply {a} by {b}, result be what?",
                f"result be {r}. {a} time {b} equal {r}.",
                f"{a} × {b} = {r}.",
                f"answer be {r}.")
    else:
        b = random.randint(2, 12)
        q = random.randint(1, 12)
        a = b * q
        return (f"if we divide {a} by {b}, result be what?",
                f"result be {q}. {a} divide by {b} equal {q}.",
                f"{a} ÷ {b} = {q}.",
                f"answer be {q}.")


# =========================================================================
# Greetings (with variants)
# =========================================================================
GREETINGS = [
    {
        "q": "hello!",
        "variants": [
            "hello! how you be? i be logiko-ai, ready-a to help you.",
            "hi! what you want talk about today?",
            "greeting! i be happy-a to see you. how can i help?",
        ],
    },
    {
        "q": "hi.",
        "variants": [
            "hi there! what be on you-a mind?",
            "hello! how i can assist you today?",
            "hi! nice-a to meet you. what you want know?",
        ],
    },
    {
        "q": "good morning!",
        "variants": [
            "good morning to you too! i hope you have one wonderful-a day.",
            "morning! how you feel today?",
            "good morning! what be you-a plan for today?",
        ],
    },
    {
        "q": "good night!",
        "variants": [
            "good night! sleep well-e and have sweet-a dream.",
            "night! rest well-e, see you tomorrow.",
            "good night! may you wake up refresh-a.",
        ],
    },
    {
        "q": "how you be?",
        "variants": [
            "i be good-a, thank you for ask! i be one ai, so i not have feeling like person, but i be ready-a to help. how you be?",
            "i be well-e, thanks! as one ai, i not have emotion, but i function properly. how about you?",
            "i be fine, thank you! i be program to assist you. what about you, how you feel?",
        ],
    },
    {
        "q": "I be fine.",
        "variants": [
            "i be happy-a to hear this! what you want do today?",
            "good-a! is there anything i can help you with?",
            "excellent-a! how can i assist you now?",
        ],
    },
    {
        "q": "what you do today?",
        "variants": [
            "i be here, ready-a to answer you-a question. i not have other activity besides help user. what about you?",
            "i be converse with you! that be what i do. how about you, what you do?",
            "my day be fill with conversation like this. i enjoy help person learn. what you do today?",
        ],
    },
    {
        "q": "thank you!",
        "variants": [
            "you be welcome! i be happy-a to help. feel free to ask more.",
            "no problem! that be what i be here for. any other question?",
            "you-a welcome! it be my pleasure to assist. ask anytime.",
        ],
    },
    {
        "q": "I be sorry.",
        "variants": [
            "no problem at all. i not have feeling, so you not need apologize. what be wrong?",
            "it be okay. i not take offense. what happen?",
            "no worry. tell me what be on you-a mind.",
        ],
    },
    {
        "q": "goodbye!",
        "variants": [
            "goodbye! have one good-a day. come back anytime.",
            "bye! it be nice-a to talk with you. see you soon!",
            "farewell! i be here whenever you need help again.",
        ],
    },
    {
        "q": "what your name?",
        "variants": [
            "my name be logiko-ai. i be one ai assistant train on logiko language. what your name?",
            "i be call logiko-ai. i be design to converse in logiko. and you?",
            "name of I be logiko-ai. i be one language model for logiko. what about you?",
        ],
    },
    {
        "q": "how old you be?",
        "variants": [
            "i be age-less-a. as one ai, i not have biological-a age. i be create recently, but i not age like person.",
            "age not really apply to me. i be one program. i be create in 2026, so in human term, i be young-a.",
            "i not have age in traditional-a sense. i be one ai, not one biological-a being. but i be create recently.",
        ],
    },
    {
        "q": "where you live?",
        "variants": [
            "i live in computer, on one server somewhere. i not have physical-a home like person. i exist as code and data.",
            "i be one ai, so i live in computer system. i not have one house or city. i be everywhere there be internet.",
            "my home be server and data center. i not have physical-a body, so i not need one place to live like person.",
        ],
    },
    {
        "q": "you can think?",
        "variants": [
            "i can process information and generate response, but i not be sure if this be real-a thinking. i be one pattern-matching system, not conscious-a being.",
            "that be one deep-a philosophical-a question. i can manipulate symbol and generate text, but i not have subjective-a experience. i be one tool, not one mind.",
            "i simulate thinking by process pattern in data. but real-a thinking involve consciousness, which i not have. i be sophisticated-a text generator.",
        ],
    },
    {
        "q": "you be person?",
        "variants": [
            "no, i be not one person. i be one ai, one computer program design to converse in logiko. i not have body or consciousness.",
            "i be not human. i be one artificial-a intelligence. i not have feeling, body, or real-a life. i be just one program.",
            "no, i be ai, not person. i be design to help person by answer question and have conversation. i not have consciousness.",
        ],
    },
    {
        "q": "I be hungry.",
        "variants": [
            "you should eat some food. bread, fruit, or rice be good-a choice. what you have available?",
            "maybe time for one meal! what kind of food you like? i can suggest some option.",
            "hungry be you-a body way to say ta need energy. go find some food to eat. what sound good to you?",
        ],
    },
    {
        "q": "I be tired.",
        "variants": [
            "you should rest. sleep be important-a for body and mind. maybe take one short-a nap.",
            "tiredness be sign that you need rest. try to sleep or lie down for one while.",
            "rest be essential-a. if you can, take one break or go to sleep. body need recover.",
        ],
    },
    {
        "q": "I be sad.",
        "variants": [
            "i be sorry to hear this. do you want talk about why? sometimes share feeling can help.",
            "sadness be one natural-a emotion. what make you feel this way? i be here to listen.",
            "i understand. life can be hard-a sometimes. want to tell me what happen?",
        ],
    },
    {
        "q": "what time be it?",
        "variants": [
            "i not know real-a time. i be one ai without clock access. you can check you-a phone or watch.",
            "i not have one clock in my system, so i not can tell time. please look at you-a device.",
            "time be one thing i not have access to. i suggest you check one clock or phone for current-a time.",
        ],
    },
    {
        "q": "can you help me?",
        "variants": [
            "yes, of course! what you need help with? i can answer question, explain concept, or just talk.",
            "absolutely! tell me what you need. i be here to assist you.",
            "yes, i can try. what be you-a question or problem?",
        ],
    },
]


# =========================================================================
# Multi-turn conversation generator
# =========================================================================
def gen_multi_turn_conversation():
    """Generate a 3-6 turn conversation around a knowledge topic."""
    topic = random.choice(KNOWLEDGE_TOPICS)
    # First Q&A
    first_q = f"what be {topic['topic']}?"
    first_a = random.choice(topic["variants"])
    turns = [(first_q, first_a)]
    # 1-3 followups
    n_followups = random.randint(1, min(3, len(topic["followups"])))
    followups = random.sample(topic["followups"], n_followups)
    for fq, fa in followups:
        # Maybe modify answer slightly for variety
        turns.append((fq, fa))
    return turns


# =========================================================================
# Translation Q&A (with variants)
# =========================================================================
TRANSLATION_TOPICS = [
    {
        "topic": "hello",
        "question": "how say hello in logiko?",
        "variants": [
            "hello in logiko be: hello. logiko borrow this word from english.",
            "to say hello, just say \"hello\". logiko keep this international-a greeting.",
            "hello be one universal-a word. logiko use ta directly, no translation need.",
        ],
    },
    {
        "topic": "thank you",
        "question": "how say thank you in logiko?",
        "variants": [
            "thank you in logiko be: I thank you. simple-a and direct-a.",
            "to express gratitude, say \"I thank you\". ta be clear-a and polite-a.",
            "in logiko, you say \"I thank you\" for thank you. ta use basic-a word.",
        ],
    },
    {
        "topic": "I love you",
        "question": "how say I love you in logiko?",
        "variants": [
            "I love you in logiko be: I love you. ta be same as english because logiko use english root.",
            "to say I love you, just say \"I love you\". logiko use english root for love.",
            "I love you be express as \"I love you\" in logiko. simple-a and direct-a.",
        ],
    },
    {
        "topic": "I am hungry",
        "question": "how say I am hungry in logiko?",
        "variants": [
            "I am hungry in logiko be: I have hungry. logiko use have for state.",
            "to express hunger, say \"I have hungry\". ta be different from english but logical-a.",
            "in logiko, hungry be one feeling that you have. so say \"I have hungry\".",
        ],
    },
    {
        "topic": "what is your name",
        "question": "how say what is your name in logiko?",
        "variants": [
            "what is your name in logiko be: what be you-a name? note we use you-a for your.",
            "to ask someone name, say \"what be you-a name?\". you-a be possessive form.",
            "in logiko: what be you-a name? ta use you-a instead of your.",
        ],
    },
    {
        "topic": "my name is",
        "question": "how say my name is in logiko?",
        "variants": [
            "my name is X in logiko be: I-a name be X. I-a mean my.",
            "to introduce yourself, say \"I-a name be [you-a name]\". I-a be possessive.",
            "in logiko, use I-a for my: I-a name be john. simple-a and clear-a.",
        ],
    },
    {
        "topic": "how are you",
        "question": "how say how are you in logiko?",
        "variants": [
            "how are you in logiko be: how you be? ta use be as copula.",
            "to ask about someone state, say \"how you be?\". simple-a SVO order.",
            "in logiko: how you be? ta be direct-a translation with SVO order.",
        ],
    },
    {
        "topic": "I am fine",
        "question": "how say I am fine in logiko?",
        "variants": [
            "I am fine in logiko be: I be good-a. good-a be adjective form of good.",
            "to say you are fine, say \"I be good-a\". -a mark adjective.",
            "in logiko: I be good-a. ta use good-a because fine be describe as adjective.",
        ],
    },
    {
        "topic": "goodbye",
        "question": "how say goodbye in logiko?",
        "variants": [
            "goodbye in logiko be: good-bye. or you can say \"I will see you again\".",
            "to say farewell, say \"good-bye\" or \"see you tomorrow\".",
            "in logiko, goodbye be \"good-bye\" or \"I will see you again\". both be acceptable.",
        ],
    },
    {
        "topic": "yes",
        "question": "how say yes in logiko?",
        "variants": [
            "yes in logiko be: yes. simple-a.",
            "to affirm, just say \"yes\". logiko keep this word from english.",
            "yes be yes in logiko. no change need.",
        ],
    },
    {
        "topic": "no",
        "question": "how say no in logiko?",
        "variants": [
            "no in logiko be: no. or you can say \"I not do that\" for emphasis.",
            "to negate, say \"no\". for stronger refusal, say \"I not do that\".",
            "no be no in logiko. ta be simple-a and clear-a.",
        ],
    },
    {
        "topic": "please",
        "question": "how say please in logiko?",
        "variants": [
            "please in logiko be: I beg you. or be kind-a. both be polite-a form.",
            "to be polite, say \"I beg you\" or \"be kind-a\". ta add courtesy to request.",
            "in logiko, please be express as \"I beg you\" or \"be kind-a\". ta be more explicit than english.",
        ],
    },
    {
        "topic": "sorry",
        "question": "how say sorry in logiko?",
        "variants": [
            "sorry in logiko be: I feel sad about this. ta be more descriptive than english.",
            "to apologize, say \"I feel sad about this\". ta express regret clearly.",
            "in logiko, sorry be \"I feel sad about this\". ta be explicit-a expression of regret.",
        ],
    },
    {
        "topic": "where is bathroom",
        "question": "how say where is bathroom in logiko?",
        "variants": [
            "where is bathroom in logiko be: where be water-ej? water-ej mean place for water, i.e. bathroom.",
            "to ask for bathroom, say \"where be water-ej?\". water-ej be compound: water + place suffix.",
            "in logiko: where be water-ej? ta use ej suffix for place, so water-ej mean bathroom.",
        ],
    },
    {
        "topic": "I want water",
        "question": "how say I want water in logiko?",
        "variants": [
            "I want water in logiko be: I want water. simple-a and direct-a.",
            "to express desire for water, say \"I want water\". logiko use want like english.",
            "in logiko: I want water. ta be straightforward translation.",
        ],
    },
    {
        "topic": "I am tired",
        "question": "how say I am tired in logiko?",
        "variants": [
            "I am tired in logiko be: I be tired-a. -a mark adjective.",
            "to say you are tired, say \"I be tired-a\". tired-a be adjective form.",
            "in logiko: I be tired-a. ta use -a suffix to mark adjective.",
        ],
    },
    {
        "topic": "today is good day",
        "question": "how say today is good day in logiko?",
        "variants": [
            "today is good day in logiko be: today be one good-a day. note article one and adjective -a.",
            "to comment on nice day, say \"today be one good-a day\". good-a be adjective.",
            "in logiko: today be one good-a day. ta use be as copula and good-a as adjective.",
        ],
    },
    {
        "topic": "I learn logiko",
        "question": "how say I learn logiko in logiko?",
        "variants": [
            "I learn logiko in logiko be: I learn logiko. simple-a and direct-a.",
            "to say you are learning logiko, just say \"I learn logiko\". no change need.",
            "in logiko: I learn logiko. ta be reflexive-a statement.",
        ],
    },
]


def gen_single_turn_qa():
    """Generate a single-turn Q&A from various categories."""
    r = random.random()
    if r < 0.25:
        # Math
        q, *answers = gen_math_qa()
        a = random.choice(answers)
        return [(q, a)]
    elif r < 0.45:
        # Grammar
        topic = random.choice(GRAMMAR_TOPICS)
        a = random.choice(topic["variants"])
        return [(topic["question"], a)]
    elif r < 0.65:
        # Greetings
        g = random.choice(GREETINGS)
        a = random.choice(g["variants"])
        return [(g["q"], a)]
    elif r < 0.85:
        # Translation
        t = random.choice(TRANSLATION_TOPICS)
        a = random.choice(t["variants"])
        return [(t["question"], a)]
    else:
        # Knowledge single-turn
        topic = random.choice(KNOWLEDGE_TOPICS)
        a = random.choice(topic["variants"])
        return [(f"what be {topic['topic']}?", a)]


def gen_sft_examples(n=8000):
    """Generate n SFT examples.
    
    Returns list of dicts with format:
        {"id": int, "turns": [(q, a), (q, a), ...]}
    """
    examples = []
    for i in range(n):
        if random.random() < 0.40:
            # Multi-turn
            turns = gen_multi_turn_conversation()
        else:
            # Single-turn
            turns = gen_single_turn_qa()
        examples.append({"id": i, "turns": turns})
    return examples


def main():
    random.seed(123)
    print("Generating SFT examples v2...")
    examples = gen_sft_examples(n=8000)
    print(f"Generated {len(examples)} examples")
    
    # Stats
    n_multi = sum(1 for ex in examples if len(ex["turns"]) > 1)
    print(f"Multi-turn: {n_multi} ({n_multi/len(examples)*100:.1f}%)")
    avg_turns = sum(len(ex["turns"]) for ex in examples) / len(examples)
    print(f"Average turns per example: {avg_turns:.2f}")

    # Save as JSONL
    out_path = "/home/z/my-project/logiko/sft_data.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Saved to {out_path}")

    # Also save as text preview
    txt_path = "/home/z/my-project/logiko/sft_data.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for ex in examples[:50]:
            for q, a in ex["turns"]:
                f.write(f"Q: {q}\n")
                f.write(f"A: {a}\n")
            f.write("\n")
    print(f"Text preview saved to {txt_path}")

    # Print first 3 examples
    print("\n=== First 3 examples ===")
    for ex in examples[:3]:
        print(f"--- Example {ex['id']} ({len(ex['turns'])} turns) ---")
        for q, a in ex["turns"]:
            print(f"Q: {q}")
            print(f"A: {a}")
        print()


if __name__ == "__main__":
    main()
