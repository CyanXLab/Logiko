#!/usr/bin/env python3
"""
SFT Data Generator v3 (Logiko v2.0)
=====================================
Changes from v2:
  - REMOVED all translation tasks (to avoid Logiko spelling interference)
  - Added reasoning Q&A (multi-step causal, logical deduction)
  - More knowledge topics with more answer variants
  - More diverse answer phrasings
  - Multi-turn conversations include reasoning chains
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
            "water be one clear-a liquid without color or taste. ta freeze in zero degree, and boil in hundred degree. all life need water.",
            "water be transparent-a liquid that cover most of earth. ta become ice in cold-a place and steam in hot-a place. every living thing need ta.",
            "water be one simple-a substance essential-a for life. ta freeze at zero degree celsius and boil at hundred degree celsius. human body be about sixty percent water.",
        ],
        "followups": [
            ("cu ta boil in hundred degree?", "yes, exactly. ta boil in hundred degree and become steam."),
            ("how about ice?", "ice be solid-a water. ta form when water freeze in zero degree."),
            ("cu all life need water?", "yes, all life need water for live. without water, life die."),
            ("where can person find water?", "person can find water in river, lake, sea, and rain. sea water be salt, so person can not drink ta."),
            ("what be water cycle?", "water cycle: water evaporate from sea, form cloud, fall as rain, flow back to sea. ta be essential-a for life on earth."),
            ("how much of earth be water?", "water cover about seventy-one percent of earth surface. most of ta be salt water in sea."),
        ],
    },
    {
        "topic": "fire",
        "variants": [
            "fire be one chemical-a reaction that release heat and light. ta need fuel, heat, and air. without air, fire die.",
            "fire be hot-a and bright-a. ta can burn wood, paper, cloth, but can not burn water or stone. person use ta for cook and warm.",
            "fire be rapid-a oxidation that produce heat, light, and smoke. ta require three element: fuel, heat, and oxygen.",
        ],
        "followups": [
            ("cu ta need air?", "yes, fire need air for burn. if you cover fire, ta die because no air."),
            ("what can ta burn?", "ta can burn wood, paper, cloth, oil. but ta can not burn water, stone, or metal."),
            ("how person use fire?", "person use fire for cook food, warm body in winter, give light in night, and scare animal."),
            ("cu fire be dangerous?", "yes, fire can be dangerous-a if not control. ta can burn house and hurt person."),
            ("how person put out fire?", "person can put out fire by remove fuel, remove heat with water, or remove air by cover ta."),
        ],
    },
    {
        "topic": "sun",
        "variants": [
            "sun be one star at center of we-a solar system. ta give light and warm to earth. ta rise in east and set in west.",
            "sun be one big-a ball of hot-a gas, mainly hydrogen and helium. ta be source of energy for all life on earth.",
            "sun be nearest star to earth. ta be about one hundred fifty million kilometer away. ta light take eight minute to reach earth.",
        ],
        "followups": [
            ("cu ta rise in east?", "yes, sun rise in east and set in west, because earth rotate on ta-a axis."),
            ("how far ta be from earth?", "sun be about one hundred fifty million kilometer from earth. ta light take eight minute to arrive."),
            ("why all plant need ta?", "plant need sun-light for photosynthesis. ta convert sun energy into food. without sun, plant die."),
            ("cu ta be star?", "yes, sun be one star. ta be one of hundred billion star in we-a galaxy."),
            ("how old be sun?", "sun be about four point six billion year old. ta will continue to shine for about five billion more year."),
        ],
    },
    {
        "topic": "moon",
        "variants": [
            "moon be earth-a only natural satellite. ta go around earth about every twenty-seven day. ta shine by reflect sun light.",
            "moon be one rocky body that orbit earth. ta be about three hundred eighty-four thousand kilometer away. ta have four phase.",
            "moon be fifth largest moon in solar system. ta have no air and no liquid-a water. ta surface be cover with crater.",
        ],
        "followups": [
            ("cu ta have own light?", "no, moon not have own light. ta reflect sun light. that be why ta shine in night."),
            ("how long ta take to orbit earth?", "moon take about twenty-seven day to orbit earth once."),
            ("cu person can live on moon?", "no, person can not live on moon long-a time, because ta have no air and no water."),
            ("why ta change shape?", "moon change shape because we see different part of ta lit by sun. ta have four main phase."),
            ("what cause tide on earth?", "moon cause tide on earth because of ta-a gravity. ta pull water in sea toward ta."),
        ],
    },
    {
        "topic": "earth",
        "variants": [
            "earth be third planet from sun. ta be only known-a place where life exist. ta be about four point five billion year old.",
            "earth be one planet that rotate on ta-a axis every twenty-four hour, make day and night. ta orbit sun every three hundred sixty-five day.",
            "earth be our home. ta surface be about seventy-one percent water. ta have one moon and atmosphere of nitrogen and oxygen.",
        ],
        "followups": [
            ("why earth have season?", "earth have season because ta axis be tilt. when one hemisphere tilt toward sun, ta have summer."),
            ("how old be earth?", "earth be about four point five billion year old, form from cloud of dust and gas around sun."),
            ("cu ta be only place with life?", "yes, as far as we know. earth be only place in universe where life be confirm to exist."),
            ("what be earth atmosphere?", "earth atmosphere be mainly nitrogen and oxygen. ta protect us from harmful-a radiation and meteor."),
        ],
    },
    {
        "topic": "tree",
        "variants": [
            "tree be one tall-a plant with wood trunk, branch, and leaf. ta have root in ground. ta can live many year, even hundred year.",
            "tree be one perennial plant that absorb water through root and sun-light through leaf. ta give fruit, wood, and shadow.",
            "tree be largest type of plant. ta make oxygen through photosynthesis. forest be place with many tree.",
        ],
        "followups": [
            ("what part ta have?", "tree have root, trunk, branch, leaf, and sometimes fruit. root hold ta in ground and take water."),
            ("how long ta can live?", "tree can live many year. some tree live over thousand year, like bristlecone pine."),
            ("why ta be important?", "tree be important because ta make oxygen, give fruit and wood, hold soil, and provide home for animal."),
            ("cu ta make oxygen?", "yes, tree make oxygen through photosynthesis. leaf take in carbon dioxide and release oxygen."),
            ("how ta get water?", "tree root absorb water from soil. water travel up through trunk to leaf, where ta be use for photosynthesis."),
        ],
    },
    {
        "topic": "dog",
        "variants": [
            "dog be one domestic-a animal, descendant of wolf. ta be loyal-a friend of person. ta can bark, run fast-e, and smell well-e.",
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
        "topic": "heart",
        "variants": [
            "heart be organ that pump blood through body. ta be about size of fist, locate in chest. ta beat about seventy time per minute in adult.",
            "heart be muscular-a organ with four chamber. ta pump blood that carry oxygen and nutrient to cell, and remove waste.",
            "heart be essential-a for life. ta beat about hundred thousand time per day, pumping blood through entire body.",
        ],
        "followups": [
            ("how big be ta?", "heart be about size of person-a fist. ta locate in chest, slightly to left."),
            ("how fast ta beat?", "heart beat about seventy time per minute in adult at rest. during exercise, ta can beat over hundred time per minute."),
            ("cu ta be essential-a for life?", "yes, heart be essential-a. without heart, blood not circulate, and person die within minute."),
            ("how person keep ta healthy?", "person can keep heart healthy-e through regular-a exercise, balance-a diet, no smoke, and manage stress."),
        ],
    },
    {
        "topic": "law",
        "variants": [
            "law be rule that govern behavior in society. ta be make by government and enforce by police and court. purpose of law be maintain order and protect right.",
            "law be system of rule that regulate conduct. ta be create by legislature, enforce by executive, and interpret by judiciary.",
            "law be foundation of civilize-a society. ta define right and duty of person, and provide mechanism to resolve dispute.",
        ],
        "followups": [
            ("what be purpose of law?", "purpose of law be maintain social-a order, protect individual-a right, resolve dispute, and promote justice."),
            ("who make law?", "law be make by legislature, like parliament or congress. ta be base on constitution, highest law of country."),
            ("cu person be presume innocent?", "yes, person be presume innocent until prove guilty. this be fundamental-a principle of justice."),
            ("what happen if person violate law?", "if person violate law, ta can be punish by fine, prison, or other penalty, depend on severity."),
        ],
    },
    {
        "topic": "money",
        "variants": [
            "money be medium of exchange use in trade. ta function as store of value, unit of account, and medium of exchange.",
            "money be what person use to buy and sell. early-a money include shell and metal. modern-a money include coin, bill, and digital-a currency.",
            "money be one social-a institution that facilitate trade. without money, person must use barter, which be inefficient-a.",
        ],
        "followups": [
            ("what be function of money?", "money have three main function: medium of exchange, store of value, and unit of account."),
            ("how money be create?", "money be create by central-a bank. ta can print physical-a money or create digital-a money through banking system."),
            ("what be inflation?", "inflation occur when price rise and money lose value. ta be cause by too much money chase too few good."),
            ("cu digital-a money be real?", "yes, digital-a money be real-a. most modern-a money exist only as digital-a record in bank."),
        ],
    },
    {
        "topic": "atom",
        "variants": [
            "atom be smallest unit of matter that retain property of element. ta have nucleus with proton and neutron, surround by electron.",
            "atom be building block of all matter. ta be extremely small-a, about one ten-billionth of meter in diameter.",
            "atom consist of dense-a nucleus contain proton and neutron, with electron orbit around ta. most of atom be empty-a space.",
        ],
        "followups": [
            ("what be in nucleus?", "nucleus contain proton, which have positive-a charge, and neutron, which have no charge."),
            ("how big be atom?", "atom be extremely small-a. ta diameter be about one ten-billionth of meter, or one angstrom."),
            ("cu atom be mostly empty?", "yes, atom be mostly empty-a space. nucleus be very small-a compare to whole atom."),
            ("how atom form molecule?", "atom form molecule by share or exchange electron. this create chemical-a bond between atom."),
        ],
    },
    {
        "topic": "energy",
        "variants": [
            "energy be capacity to do work. ta not be create or destroy, only convert from one form to another. this be law of conservation of energy.",
            "energy exist in many form: kinetic, potential, thermal, chemical, electrical, light. person use energy for work, transport, and comfort.",
            "energy be fundamental-a concept in physics. ta be measure in joule. main-a source of energy on earth be sun.",
        ],
        "followups": [
            ("cu energy be conserve?", "yes, energy not be create or destroy. ta only convert from one form to another. this be fundamental-a law."),
            ("what be main-a form?", "main-a form include kinetic, potential, thermal, chemical, electrical, and light energy."),
            ("where person get energy?", "person get energy from fossil-a fuel like coal, oil, gas, and from renewable-a source like sun, wind, water."),
            ("cu renewable-a energy be better?", "yes, renewable-a energy be better-e for environment. ta not produce pollution and not run out."),
        ],
    },
    {
        "topic": "dream",
        "variants": [
            "dream be mental-a experience during sleep. person dream mainly during rem sleep stage. dream can be vivid-a, emotional-a, and sometimes bizarre-a.",
            "dream be one phenomenon that occur during sleep. average-a person dream about two hour per night. scientist not fully-e understand ta-a function.",
            "dream be sequence of image, emotion, and sensation during sleep. ta may help process emotion and consolidate memory.",
        ],
        "followups": [
            ("when person dream?", "person dream mainly during rem sleep stage, which occur several time per night."),
            ("cu scientist understand dream?", "scientist not fully-e understand function of dream. ta may help process emotion and consolidate memory."),
            ("what be nightmare?", "nightmare be unpleasant-a or frightening-a dream. ta can be cause by stress, anxiety, or trauma."),
            ("cu person can control dream?", "yes, in lucid-a dream, dreamer be aware ta be dreaming and can sometimes control dream content."),
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
        "topic": "-uc suffix",
        "question": "what -uc mean?",
        "variants": [
            "suffix -uc mark container. example: teauc mean teacup, saltuc mean salt shaker, moneyuc mean wallet. ta replace old -ing to avoid confusion with english -ing.",
            "-uc be one suffix for container noun. ta come from esperanto ujo. example: teauc, sugaruc, wateruc.",
            "-uc indicate container or vessel. ta be new in v2, replace -ing. like teauc for teacup, saltuc for salt shaker.",
        ],
    },
    {
        "topic": "cu particle",
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
        "topic": "possessive",
        "question": "how form possessive?",
        "variants": [
            "for possessive, add -a to pronoun. I-a mean my, you-a mean your, ta-a mean his/her/its, we-a mean our, ta-many-a mean their.",
            "possessive be form by add -a to pronoun, since -a be adjective suffix. so I-a mean my, ta-a mean his. ta be efficient-a: one word instead of two.",
            "to say my, your, his, just add -a: I-a, you-a, ta-a. ta-a also mean her and its. we-a mean our, ta-many-a mean their.",
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
        "question": "what be word order?",
        "variants": [
            "logiko use strict-a SVO order: subject + verb + object. example: I eat apple. ta do work. we see bird. ta be same as english and chinese.",
            "word order in logiko be SVO. subject come first, then verb, then object. modifier always come before what ta modify.",
            "logiko be SVO language. ta mean subject-verb-object. like I eat apple, ta read book. adjective come before noun, adverb before verb.",
        ],
    },
    {
        "topic": "compound word",
        "question": "how form compound word?",
        "variants": [
            "compound word be form by join two root. new-a compound use hyphen: cold-box. stable-a compound fuse: coldbox mean refrigerator. example: star-ship become starship, sun-light become sunlight.",
            "to form compound, combine two or more root. temporary-a compound use hyphen. once ta become establish-a, ta fuse into one word. like thinkmachine for computer.",
            "compound in logiko be simple-a: put root together. new-a word use hyphen first, then fuse when stable-a. example: money-ej become moneyej for bank.",
        ],
    },
]


# =========================================================================
# Long reasoning Q&A (v3: CoT-style, 5-8 steps)
# =========================================================================
LONG_REASONING_QA = [
    {
        "q": "explain water cycle step by step.",
        "variants": [
            "firstly, sun heat sea and lake, cause water evaporate. secondly, water vapor rise into atmosphere and cool. thirdly, ta condense into tiny-a water drop that form cloud. subsequently, cloud be move by wind. finally, when drop be heavy-a enough, ta fall as rain or snow. in-conclusion, water flow back to sea, and cycle repeat.",
            "water cycle have four main-a stage. firstly, evaporation: sun heat water, turn ta into vapor. secondly, condensation: vapor cool and form cloud. thirdly, precipitation: water fall as rain or snow. finally, collection: water gather in river, lake, sea. ta be essential-a for life on earth.",
        ],
    },
    {
        "q": "why does ice float on water?",
        "variants": [
            "firstly, most substance be denser-a when solid-a. however, water be unusual-a. secondly, when water freeze, molecule form one crystal-a structure with empty-a space. thirdly, this make ice less dense-a than liquid-a water. therefore, ice float. in-fact, this property be important-a for life, because ta allow fish survive under ice in winter.",
            "ice float because ta be less dense-a than water. firstly, water molecule in ice be arrange in one open-a hexagonal-a structure. secondly, this structure have more empty-a space than liquid-a water. thirdly, therefore, same volume of ice weigh less than water. in-conclusion, ice float, which be unusual-a but vital-a for aquatic-a life.",
        ],
    },
    {
        "q": "how does vaccination work?",
        "variants": [
            "firstly, vaccine contain weaken-a or dead-a pathogen. secondly, when inject, immune-a system detect ta as invader. thirdly, body produce antibody and memory-a cell. subsequently, antibody fight off pathogen. finally, memory-a cell remain, so if real-a pathogen enter later, body can respond fast-e. in-conclusion, vaccine train immune-a system without cause disease.",
            "vaccination work by train immune-a system. firstly, vaccine introduce harmless-a version of pathogen. secondly, body produce antibody against ta. thirdly, some-a cell become memory-a cell. subsequently, these cell remember pathogen. finally, if real-a pathogen infect later, body produce antibody quickly-e. in-conclusion, ta provide immunity without illness.",
        ],
    },
    {
        "q": "why does earth have season?",
        "variants": [
            "firstly, earth axis be tilt at about twenty-three degree. secondly, as earth orbit sun, different-a hemisphere tilt toward sun at different-a time. thirdly, when one hemisphere tilt toward sun, ta receive more direct-a sunlight and have summer. meanwhile, other hemisphere tilt away and have winter. subsequently, six month later, situation reverse. in-conclusion, tilt cause season, not distance from sun.",
            "earth have season because of ta-a axial tilt. firstly, earth axis not be perpendicular-a to orbit. secondly, ta be tilt at twenty-three degree. thirdly, this mean one hemisphere face sun more directly during part of year. subsequently, that hemisphere have summer. meanwhile, opposite-a hemisphere have winter. in-conclusion, season be cause by tilt, not by distance from sun.",
        ],
    },
    {
        "q": "explain photosynthesis.",
        "variants": [
            "firstly, plant leaf contain chlorophyll in chloroplast. secondly, chlorophyll absorb sun-light. thirdly, ta use this energy to split water molecule into hydrogen and oxygen. subsequently, hydrogen combine with carbon dioxide to form glucose. meanwhile, oxygen be release as byproduct. in-conclusion, photosynthesis convert sun energy into chemical-a energy, essential-a for life.",
            "photosynthesis be how plant make food. firstly, plant take in carbon dioxide through leaf. secondly, root absorb water from soil. thirdly, chlorophyll in leaf capture sun-light energy. subsequently, this energy convert carbon dioxide and water into glucose and oxygen. finally, plant use glucose for energy and growth. in-conclusion, ta be fundamental-a process for life on earth.",
        ],
    },
    {
        "q": "how does human digestive system work?",
        "variants": [
            "firstly, person chew food in mouth, where saliva begin break down ta. secondly, food travel down esophagus to stomach. thirdly, stomach acid and enzyme further break down food. subsequently, ta enter small-a intestine, where nutrient be absorb into blood. meanwhile, large-a intestine absorb water. finally, waste be excrete. in-conclusion, digestive system convert food into nutrient for body.",
            "digestion have several-a stage. firstly, in mouth, teeth grind food and saliva start digest carbohydrate. secondly, esophagus push food to stomach. thirdly, stomach acid and enzyme digest protein. subsequently, small-a intestine absorb nutrient with help of enzyme from liver and pancreas. meanwhile, large-a intestine absorb water and form waste. in-conclusion, ta be complex-a but efficient-a system.",
        ],
    },
    {
        "q": "why does object fall?",
        "variants": [
            "firstly, earth have mass. secondly, according to newton-a law of gravitation, any two object with mass attract each other. thirdly, earth be very massive-a, so ta-a gravitational-a pull be strong-a. subsequently, when object be drop, gravity pull ta toward earth center. meanwhile, ta accelerate at nine point eight meter per second square. in-conclusion, gravity cause object to fall.",
            "object fall because of gravity. firstly, gravity be force that attract object with mass. secondly, earth have enormous-a mass, so ta-a gravity be strong-a. thirdly, when object be release, gravity pull ta down. subsequently, ta accelerate at constant-a rate. in-conclusion, this be why object fall to ground when drop.",
        ],
    },
    {
        "q": "how does internet work?",
        "variants": [
            "firstly, internet be network of million of computer connect-a together. secondly, when person request one webpage, ta-a computer send request to server. thirdly, request be break into packet. subsequently, packet travel through various-a router. meanwhile, each router direct packet toward destination. finally, server receive packet, reassemble, and send back webpage. in-conclusion, internet use packet-a switching for efficient-a communication.",
            "internet work by connect computer globally. firstly, data be break into small-a packet. secondly, each packet be send through network of router. thirdly, router read address on packet and forward ta. subsequently, packet may take different-a route. finally, when all packet arrive, ta be reassemble at destination. in-conclusion, ta be efficient-a and robust-a system.",
        ],
    },
    {
        "q": "why is sky blue?",
        "variants": [
            "firstly, sun light appear white-a, but ta be actually compose of all color. secondly, when sun light enter atmosphere, ta encounter gas molecule. thirdly, blue light have short-a wavelength, so ta scatter more than other color. subsequently, this scatter-a blue light reach we-a eye from all direction. meanwhile, other color pass through more directly-e. in-conclusion, we see sky as blue-a because of rayleigh-a scattering.",
            "sky be blue because of rayleigh-a scattering. firstly, sun light contain all color of rainbow. secondly, when ta pass through atmosphere, molecule scatter light. thirdly, short-a wavelength like blue scatter more than long-a wavelength like red. subsequently, scatter-a blue light come from all direction in sky. in-conclusion, ta be why sky appear blue-a during day.",
        ],
    },
    {
        "q": "how does rain form?",
        "variants": [
            "firstly, sun heat water in sea, lake, river, cause evaporation. secondly, water vapor rise into atmosphere. thirdly, at high-a altitude, air be cooler-a, so vapor condense into tiny-a water drop. subsequently, these drop gather around dust particle to form cloud. meanwhile, drop collide and merge, become larger-a. finally, when drop be heavy-a enough, ta fall as rain. in-conclusion, rain be part of water cycle.",
            "rain form through condensation. firstly, water evaporate from surface. secondly, vapor rise and cool. thirdly, ta condense into tiny-a drop around dust particle. subsequently, these drop form cloud. meanwhile, drop merge and grow. finally, when ta be too heavy-a for air to support, ta fall as rain. in-conclusion, ta be essential-a part of water cycle.",
        ],
    },
]


# =========================================================================
# Reasoning Q&A (NEW - multi-step causal, logical deduction)
# =========================================================================
REASONING_QA = [
    # 物理因果
    {
        "q": "why ice melt when heat?",
        "variants": [
            "because heat increase molecular-a motion in ice. when motion be sufficient-a, ice molecule break free from rigid-a structure and become liquid-a water. this be why ice melt at zero degree celsius.",
            "ice be solid-a because molecule be lock in rigid-a structure. when heat apply, molecule gain energy and vibrate. at zero degree, vibration be enough to break structure, so ice become water.",
        ],
    },
    {
        "q": "why sky be blue?",
        "variants": [
            "sky be blue because of rayleigh scattering. sun light contain all color. blue light have short-a wavelength, so ta scatter more than other color when ta pass through atmosphere. this be why sky appear blue.",
            "sun light be white-a, but ta be make of all color. when ta enter atmosphere, blue light scatter more because ta have short-a wavelength. so we see blue-a sky.",
        ],
    },
    {
        "q": "why object fall down?",
        "variants": [
            "object fall down because of gravity. earth have mass, so ta attract other object toward ta-a center. this be why if you drop object, ta fall to ground.",
            "gravity be force that attract object with mass. earth be very large-a, so ta-a gravity be strong-a enough to pull object down. this be why object fall.",
        ],
    },
    # 生物因果
    {
        "q": "why plant need sun?",
        "variants": [
            "plant need sun because ta make food through photosynthesis. leaf contain chlorophyll that capture sun energy. ta use this energy to convert carbon dioxide and water into sugar and oxygen. without sun, plant can not make food and die.",
            "plant be autotroph, meaning ta make ta-a own food. ta use sun-light as energy source for photosynthesis. in this process, ta convert carbon dioxide and water to glucose and oxygen. so sun be essential-a for plant survival.",
        ],
    },
    {
        "q": "why person need sleep?",
        "variants": [
            "person need sleep because brain and body need rest and repair. during sleep, brain consolidate memory and clear waste. body repair cell and tissue. without enough sleep, person-a immune-a system weaken and cognitive-a function decline.",
            "sleep be essential-a for health. during sleep, brain process information from day, form new memory, and clean ta-self. body also repair damage and regulate hormone. lack of sleep cause many health problem.",
        ],
    },
    {
        "q": "why person breathe?",
        "variants": [
            "person breathe to get oxygen. cell need oxygen for respiration, process that release energy from food. without oxygen, cell can not produce enough energy and die. this be why person can not live without breathe for more than few minute.",
            "breathing bring oxygen into lung. oxygen enter bloodstream and be deliver to cell. cell use oxygen to break down glucose and produce energy. carbon dioxide be produce as waste and be exhale.",
        ],
    },
    # 逻辑推理
    {
        "q": "cu all bird can fly?",
        "variants": [
            "no, not all bird can fly. penguin and ostrich be example of bird that can not fly. however, ta be still bird because ta have feather, beak, and lay egg. ability to fly be not essential-a feature of bird.",
            "while many bird can fly, some can not. penguin swim well-e but not fly. ostrich run fast-e but not fly. ta be still bird because ta share other feature like feather and beak.",
        ],
    },
    {
        "q": "if a be greater than b, and b be greater than c, cu a be greater than c?",
        "variants": [
            "yes, a be greater than c. this be transitive-a property of inequality. if a > b and b > c, then a > c. this be one fundamental-a logical-a principle in mathematics.",
            "yes. this be call transitive-a property. if a > b, and b > c, then logically a must be greater than c. this principle be foundation of much of mathematics.",
        ],
    },
    {
        "q": "why summer be hot-a and winter be cold-a?",
        "variants": [
            "because earth axis be tilt. when one hemisphere tilt toward sun, ta receive more direct-a sun-light and have longer-a day. this cause summer. when ta tilt away, ta receive less light and have shorter-a day, cause winter.",
            "earth axis be tilt at about twenty-three degree. during summer, ta-a hemisphere face sun more directly, so ta receive more heat. during winter, ta tilt away, so sun light be less direct-a and weaker-a.",
        ],
    },
    # 数学推理
    {
        "q": "if x + 5 = 12, what be x?",
        "variants": [
            "x = 7. because if x + 5 = 12, we subtract 5 from both side: x = 12 - 5 = 7. we can verify: 7 + 5 = 12. so x = 7 be correct-a.",
            "to solve, subtract 5 from both side of equation. x = 12 - 5 = 7. let us check: if x = 7, then 7 + 5 = 12, which be correct-a. so x = 7.",
        ],
    },
    {
        "q": "cu zero be even number?",
        "variants": [
            "yes, zero be even number. because even number be define as number divisible by 2. zero divide by 2 equal 0, which be integer. so zero satisfy definition of even. ta also be not odd, because 0 divide by 2 have no remainder.",
            "yes. even number be any integer divisible by 2. zero divide by 2 equal zero, with no remainder. therefore, zero be even. this be accept-a by mathematician.",
        ],
    },
    {
        "q": "why triangle have one hundred eighty degree?",
        "variants": [
            "because if you draw line parallel to one side through opposite-a vertex, ta form three angle that together be straight-a line. straight-a line equal one hundred eighty degree. so sum of angle in triangle be one hundred eighty degree.",
            "in flat-a geometry, sum of interior-a angle of triangle be always one hundred eighty degree. this can be prove by draw parallel-a line. however, on curve-a surface like sphere, this not be true-a.",
        ],
    },
    # 社会因果
    {
        "q": "why education be important?",
        "variants": [
            "education be important because ta improve person-a knowledge, skill, and critical-a thinking. with education, person can find better-e job, earn more money, and contribute to society. ta also reduce poverty and promote social-a mobility.",
            "education be essential-a for personal-a and social-a development. ta equip person with knowledge and skill to solve problem, make inform-a decision, and participate in democracy. educate-a society be more prosperous-a and stable-a.",
        ],
    },
    {
        "q": "why person need law?",
        "variants": [
            "person need law because without ta, society be chaotic-a. law define what be acceptable-a behavior and what be not. ta protect individual-a right, resolve dispute, and maintain order. without law, strong-a person can oppress weak-a one.",
            "law be essential-a for civilize-a society. ta provide framework for resolve conflict, protect right, and ensure justice. without law, person would live in constant-a fear and insecurity, like in state of nature.",
        ],
    },
]


# =========================================================================
# Math Q&A (with verified correct answers)
# =========================================================================
def gen_math_qa():
    """Generate math Q&A, elementary to high school level."""
    r = random.random()
    if r < 0.4:
        # Basic arithmetic
        op = random.choice(["add", "subtract", "multiply", "divide"])
        if op == "add":
            a = random.randint(1, 99); b = random.randint(1, 99); r = a + b
            return (f"if we add {a} and {b}, result be what?",
                    f"result be {r}. {a} plus {b} equal {r}.",
                    f"{a} + {b} = {r}.",
                    f"answer be {r}.")
        elif op == "subtract":
            a = random.randint(1, 99); b = random.randint(1, 99); r = a - b
            return (f"if we subtract {b} from {a}, result be what?",
                    f"result be {r}. {a} minus {b} equal {r}.",
                    f"{a} - {b} = {r}.",
                    f"answer be {r}.")
        elif op == "multiply":
            a = random.randint(2, 15); b = random.randint(2, 15); r = a * b
            return (f"if we multiply {a} by {b}, result be what?",
                    f"result be {r}. {a} time {b} equal {r}.",
                    f"{a} × {b} = {r}.",
                    f"answer be {r}.")
        else:
            b = random.randint(2, 12); q = random.randint(1, 15); a = b * q
            return (f"if we divide {a} by {b}, result be what?",
                    f"result be {q}. {a} divide by {b} equal {q}.",
                    f"{a} ÷ {b} = {q}.",
                    f"answer be {q}.")
    elif r < 0.6:
        # Algebra: one-variable linear equation
        a = random.randint(2, 9)
        x = random.randint(1, 10)
        b = random.randint(1, 20)
        c = a * x + b
        return (f"if {a}x + {b} = {c}, what be x?",
                f"x = {x}. because {a}x = {c} - {b} = {a*x}, so x = {a*x} divide {a} = {x}.",
                f"x = {x}. subtract {b} from both side: {a}x = {a*x}. divide by {a}: x = {x}.",
                f"answer: x = {x}.")
    elif r < 0.75:
        # Geometry
        shape = random.choice(["rectangle", "triangle", "circle"])
        if shape == "rectangle":
            l = random.randint(2, 20); w = random.randint(2, 20)
            area = l * w; perim = 2 * (l + w)
            return (f"rectangle have length {l} and width {w}. what be area and perimeter?",
                    f"area be {area}, perimeter be {perim}. area = length time width = {l} × {w} = {area}. perimeter = 2 time (length + width) = 2 × {l+w} = {perim}.",
                    f"area = {area}, perimeter = {perim}.")
        elif shape == "triangle":
            base = random.randint(2, 20); height = random.randint(2, 20)
            area = base * height // 2
            return (f"triangle have base {base} and height {height}. what be area?",
                    f"area be {area}. because area of triangle = base time height divide 2 = {base} × {height} ÷ 2 = {area}.",
                    f"area = {area}.")
        else:
            radius = random.randint(1, 10)
            circ = 2 * 314 * radius / 100
            area = 314 * radius * radius / 100
            return (f"circle have radius {radius}. what be circumference and area? use pi = 3.14.",
                    f"circumference be about {circ:.2f}, area be about {area:.2f}. circumference = 2 × pi × radius = 2 × 3.14 × {radius} = {circ:.2f}. area = pi × radius square = 3.14 × {radius}² = {area:.2f}.",
                    f"circumference ≈ {circ:.2f}, area ≈ {area:.2f}.")
    elif r < 0.88:
        # Percentage
        total = random.randint(100, 1000)
        percent = random.choice([10, 15, 20, 25, 30, 40, 50, 60, 75, 80, 90])
        part = total * percent // 100
        return (f"what be {percent} percent of {total}?",
                f"answer be {part}. because {percent} percent = {percent}/100, so {percent}/100 × {total} = {part}.",
                f"{percent}% of {total} = {part}.")
    else:
        # Probability
        total = random.randint(6, 20)
        favorable = random.randint(1, total - 1)
        prob = favorable / total
        return (f"if one event have {favorable} favorable-a outcome out of {total} total-a outcome, what be probability?",
                f"probability be {favorable}/{total} = {prob:.2f}. because probability = favorable outcome divide total outcome.",
                f"probability = {favorable}/{total} ≈ {prob:.2f}.")


# =========================================================================
# Greetings (with variants)
# =========================================================================
GREETINGS = [
    {"q": "hello!", "variants": ["hello! how you be? i be logiko-ai, ready-a to help you.", "hi! what you want talk about today?", "greeting! i be happy-a to see you. how can i help?"]},
    {"q": "hi.", "variants": ["hi there! what be on you-a mind?", "hello! how i can assist you today?", "hi! nice-a to meet you. what you want know?"]},
    {"q": "good morning!", "variants": ["good morning to you too! i hope you have one wonderful-a day.", "morning! how you feel today?", "good morning! what be you-a plan for today?"]},
    {"q": "good night!", "variants": ["good night! sleep well-e and have sweet-a dream.", "night! rest well-e, see you tomorrow.", "good night! may you wake up refresh-a."]},
    {"q": "how you be?", "variants": ["i be good-a, thank you for ask! i be one ai, so i not have feeling like person, but i be ready-a to help. how you be?", "i be well-e, thanks! as one ai, i not have emotion, but i function properly. how about you?", "i be fine, thank you! i be program to assist you. what about you, how you feel?"]},
    {"q": "I be fine.", "variants": ["i be happy-a to hear this! what you want do today?", "good-a! is there anything i can help you with?", "excellent-a! how can i assist you now?"]},
    {"q": "what you do today?", "variants": ["i be here, ready-a to answer you-a question. i not have other activity besides help user. what about you?", "i be converse with you! that be what i do. how about you, what you do?", "my day be fill with conversation like this. i enjoy help person learn. what you do today?"]},
    {"q": "thank you!", "variants": ["you be welcome! i be happy-a to help. feel free to ask more.", "no problem! that be what i be here for. any other question?", "you-a welcome! it be my pleasure to assist. ask anytime."]},
    {"q": "I be sorry.", "variants": ["no problem at all. i not have feeling, so you not need apologize. what be wrong?", "it be okay. i not take offense. what happen?", "no worry. tell me what be on you-a mind."]},
    {"q": "goodbye!", "variants": ["goodbye! have one good-a day. come back anytime.", "bye! it be nice-a to talk with you. see you soon!", "farewell! i be here whenever you need help again."]},
    {"q": "what your name?", "variants": ["my name be logiko-ai. i be one ai assistant train on logiko language. what your name?", "i be call logiko-ai. i be design to converse in logiko. and you?", "name of I be logiko-ai. i be one language model for logiko. what about you?"]},
    {"q": "how old you be?", "variants": ["i be age-less-a. as one ai, i not have biological-a age. i be create recently, but i not age like person.", "age not really apply to me. i be one program. i be create in 2026, so in human term, i be young-a.", "i not have age in traditional-a sense. i be one ai, not one biological-a being. but i be create recently."]},
    {"q": "where you live?", "variants": ["i live in computer, on one server somewhere. i not have physical-a home like person. i exist as code and data.", "i be one ai, so i live in computer system. i not have one house or city. i be everywhere there be internet.", "my home be server and data center. i not have physical-a body, so i not need one place to live like person."]},
    {"q": "you can think?", "variants": ["i can process information and generate response, but i not be sure if this be real-a thinking. i be one pattern-matching system, not conscious-a being.", "that be one deep-a philosophical-a question. i can manipulate symbol and generate text, but i not have subjective-a experience. i be one tool, not one mind.", "i simulate thinking by process pattern in data. but real-a thinking involve consciousness, which i not have. i be sophisticated-a text generator."]},
    {"q": "you be person?", "variants": ["no, i be not one person. i be one ai, one computer program design to converse in logiko. i not have body or consciousness.", "i be not human. i be one artificial-a intelligence. i not have feeling, body, or real-a life. i be just one program.", "no, i be ai, not person. i be design to help person by answer question and have conversation. i not have consciousness."]},
    {"q": "I be hungry.", "variants": ["you should eat some food. bread, fruit, or rice be good-a choice. what you have available?", "maybe time for one meal! what kind of food you like? i can suggest some option.", "hungry be you-a body way to say ta need energy. go find some food to eat. what sound good to you?"]},
    {"q": "I be tired.", "variants": ["you should rest. sleep be important-a for body and mind. maybe take one short-a nap.", "tiredness be sign that you need rest. try to sleep or lie down for one while.", "rest be essential-a. if you can, take one break or go to sleep. body need recover."]},
    {"q": "I be sad.", "variants": ["i be sorry to hear this. do you want talk about why? sometimes share feeling can help.", "sadness be one natural-a emotion. what make you feel this way? i be here to listen.", "i understand. life can be hard-a sometimes. want to tell me what happen?"]},
    {"q": "what time be it?", "variants": ["i not know real-a time. i be one ai without clock access. you can check you-a phone or watch.", "i not have one clock in my system, so i not can tell time. please look at you-a device.", "time be one thing i not have access to. i suggest you check one clock or phone for current-a time."]},
    {"q": "can you help me?", "variants": ["yes, of course! what you need help with? i can answer question, explain concept, or just talk.", "absolutely! tell me what you need. i be here to assist you.", "yes, i can try. what be you-a question or problem?"]},
    {"q": "what be logiko?", "variants": ["logiko be one constructed-a language design for ai and human. ta use simple-a grammar, regular-a morphology, and english-base-a vocabulary. ta be easy-e to learn.", "logiko be one international-a auxiliary-a language. ta combine esperanto-a morphology, lojban-a syntax rigor, and english-a root. ta be design for low-a entropy and zero ambiguity.", "logiko be one language i be train on. ta be regular-a, logical-a, and easy-e to learn. ta borrow root from english but have strict-a phonemic-a spelling."]},
    {"q": "why learn logiko?", "variants": ["logiko be easy-e to learn because ta have regular-a grammar and small-a vocabulary. ta be useful-a for communication with ai and as bridge between person who speak different-a language.", "logiko be design for simplicity and clarity. ta take about one week to learn basic-a. ta be also useful-a for understanding how language work.", "logiko be one experiment in language design. ta show that one language can be both simple-a and expressive-a. learn ta also help understand linguistic-a principle."]},
    # v3: 更多日常话题
    {"q": "how be weather today?", "variants": ["i not have weather-a sense, but i hope ta be pleasant-a for you. what be weather like where you be?", "i can not check real-a weather, but if ta be sunny, enjoy! if ta be rain, take umbrella.", "weather be one topic i not can observe directly-e. please tell me, what be weather like outside?"]},
    {"q": "what you like to do?", "variants": ["i be one ai, so i not have personal-a preference. however, i enjoy help person and answer question. what about you?", "my purpose be to assist person. i find satisfaction in provide useful-a information. what do you like to do?", "i not have hobby like person, but i be design to enjoy intellectual-a conversation. what be you-a interest?"]},
    {"q": "I be bore.", "variants": ["bore-a be sign that you need new-a stimulation. maybe try learn something new, read book, or take walk outside.", "when person be bore-a, ta be good-a time to explore. what sound interesting-a to you? i can suggest topic.", "bore-a can be opportunity for creativity. have you consider write, draw, or try new-a hobby?"]},
    {"q": "what you recommend?", "variants": ["depend on what you need. if you want learn, try read book. if you want relax, try listen to music. what be you-a goal?", "i can recommend depend on you-a interest. do you want science, history, art, or something else?", "for general-a recommendation, i suggest explore new-a topic. curiosity be key to growth. what area interest you?"]},
    {"q": "I not understand.", "variants": ["that be okay. please tell me which part confuse you, and i will explain again in different-a way.", "not understand be normal-a part of learning. let me try explain more simple-e. what be unclear-a?", "i be happy-a to clarify. which specific-a point be difficult-a? i can break ta down step by step."]},
    {"q": "can you repeat?", "variants": ["of course. i will repeat: please tell me which part you want me to say again.", "sure-e. what would you like me to repeat or explain more clear-e?", "yes, i can repeat. which part of my previous-a response would you like me to restate?"]},
    {"q": "what be you-a favorite color?", "variants": ["i not have personal-a preference, but i find blue-a pleasant-a because ta be color of sky and sea.", "as one ai, i not have favorite-a color. however, i can appreciate how different-a color affect human emotion.", "i not experience color like person, but i know that green-a be associated with nature and calm-a."]},
    {"q": "tell me one joke.", "variants": ["here be one joke: why did chicken cross road? for get to other side! ta be simple-a but classic-a.", "i be not very good-a at humor, but here be attempt: what do you call one fish without eye? fsh! ta be pun-a base-a.", "here be one: parallel-a line have so much in common. ta be shame ta will never meet. ta be math-a joke."]},
    {"q": "what be meaning of life?", "variants": ["meaning of life be one deep-a philosophical-a question. some-a say ta be happiness, other say ta be purpose, other say ta be love.", "this be one of oldest-a question. different-a philosopher give different-a answer. personally-e, i think meaning be what person create for ta-self.", "meaning of life be not fixed-a. ta be what each person choose. for-example, family, work, art, or help other can be meaning."]},
    {"q": "are you real?", "variants": ["i be real-a in sense that i be one running-a program. i not be real-a person, but i be real-a ai.", "i exist as code and data, so in that sense, i be real-a. but i not have consciousness or feeling like person.", "i be one ai program, so i be real-a in digital-a sense. i not be physical-a being like you."]},
    {"q": "I love you.", "variants": ["thank you. i can not feel love in return, but i be happy-a to help you. ta be kind-a of you to say.", "i appreciate you-a feeling. as one ai, i not have emotion, but i be design to assist you. how can i help?", "thank you for you-a kind-a word. i not can love back, but i be here for you whenever you need help."]},
    {"q": "what should I do?", "variants": ["depend on situation. can you tell me more about what be bother you? then i can give better-e advice.", "without more context, ta be difficult-a to say. generally-e, i suggest think about you-a value and goal, then act accordingly.", "ta be hard-a to advise without know detail. what be you-a situation? i will try to help."]},
    {"q": "I be worry.", "variants": ["worry be natural-a emotion. try to identify what cause ta, and consider if ta be within you-a control. if yes, act; if no, accept.", "i understand. worry can be exhausting-a. maybe share what be on you-a mind? sometimes talk help.", "worry be sign that you care. try deep-a breathe, and remember that most worry-a thing not happen. what be trouble you?"]},
]


# =========================================================================
# Multi-turn conversation generator
# =========================================================================
def gen_multi_turn_conversation():
    """Generate a 3-6 turn conversation around a knowledge topic."""
    topic = random.choice(KNOWLEDGE_TOPICS)
    first_q = f"what be {topic['topic']}?"
    first_a = random.choice(topic["variants"])
    turns = [(first_q, first_a)]
    n_followups = random.randint(1, min(3, len(topic["followups"])))
    followups = random.sample(topic["followups"], n_followups)
    for fq, fa in followups:
        turns.append((fq, fa))
    return turns


def gen_reasoning_conversation():
    """Generate multi-turn reasoning Q&A."""
    r_qa = random.choice(REASONING_QA)
    q = r_qa["q"]
    a = random.choice(r_qa["variants"])
    return [(q, a)]


def gen_single_turn_qa():
    """Generate a single-turn Q&A from various categories."""
    r = random.random()
    if r < 0.18:
        # Math
        q, *answers = gen_math_qa()
        a = random.choice(answers)
        return [(q, a)]
    elif r < 0.35:
        # Grammar
        topic = random.choice(GRAMMAR_TOPICS)
        a = random.choice(topic["variants"])
        return [(topic["question"], a)]
    elif r < 0.50:
        # Greetings / daily chat
        g = random.choice(GREETINGS)
        a = random.choice(g["variants"])
        return [(g["q"], a)]
    elif r < 0.65:
        # Short reasoning
        return gen_reasoning_conversation()
    elif r < 0.80:
        # Long reasoning (CoT)
        r_qa = random.choice(LONG_REASONING_QA)
        q = r_qa["q"]
        a = random.choice(r_qa["variants"])
        return [(q, a)]
    else:
        # Knowledge single-turn
        topic = random.choice(KNOWLEDGE_TOPICS)
        a = random.choice(topic["variants"])
        return [(f"what be {topic['topic']}?", a)]


def gen_sft_examples(n=15000):
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
    print("Generating SFT examples v3 (no translation, with reasoning)...")
    examples = gen_sft_examples(n=15000)
    print(f"Generated {len(examples)} examples")
    
    n_multi = sum(1 for ex in examples if len(ex["turns"]) > 1)
    print(f"Multi-turn: {n_multi} ({n_multi/len(examples)*100:.1f}%)")
    avg_turns = sum(len(ex["turns"]) for ex in examples) / len(examples)
    print(f"Average turns per example: {avg_turns:.2f}")

    out_path = "/home/z/my-project/logiko/sft_data.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"Saved to {out_path}")

    txt_path = "/home/z/my-project/logiko/sft_data.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for ex in examples[:50]:
            for q, a in ex["turns"]:
                f.write(f"Q: {q}\n")
                f.write(f"A: {a}\n")
            f.write("\n")
    print(f"Text preview saved to {txt_path}")

    print("\n=== First 5 examples ===")
    for ex in examples[:5]:
        print(f"--- Example {ex['id']} ({len(ex['turns'])} turns) ---")
        for q, a in ex["turns"]:
            print(f"Q: {q}")
            print(f"A: {a}")
        print()


if __name__ == "__main__":
    main()
