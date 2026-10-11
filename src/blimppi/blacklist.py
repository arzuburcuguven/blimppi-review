# src/blimmpu/blacklist.py

BLACKLIST = {
    "Chinese": {"test-s422"},
    "Romanian": {"train-398"},
    "Russian": {"2003Zemlya_naiznanku.xml_89"},
    "Turkish": {"204540.train",},
    "German": {"hdt-s42393", "hdt-s28639"},
    "Persian": {"train-s20971", "dev-s637", "train-s18562"},
    "English": {"en_lines-ud-test-doc9-5583", "GUM_news_questionnaire-27", "GUM_bio_jerome-34", "en_lines-ud-dev-doc6-3894", "GUM_court_mental-33", "email-enronsent37_01-0022", "en_partut-ud-2055", "GUM_speech_humanitarian-51", "email-enronsent01_02-0038" } ## yet annoation is ambiguuous between adv and cconj
}
BLOCKED_NPI_PHRASES = {
    "at_all": [
    ("at_all", "cost"),
    ("at_all", "time"),
    ("not", "at_all"),
],
    "anything": [("anything", "but")],
    "ever":     [("for", "ever"), ("ever", "-", "more")],
    "yet":      [("yet", "to"), ("and", "yet")],
    "either":   [("either", "way")],
    "τίποτα":   [("από", "ο", "τίποτα")],
    "ні":       [("так", "чи", "ні"), ("чи", "ні")],
    "legen":    [("lahm", "zu", "legen")],
"gar": [(("gar","nicht","mehr"))],
"div":  [("není", "divu"), ("div", "ne")],   
"ani":  [("ani", "náhodou"), ("ani", "nápad"), ("ani", "omylem")],
"mikään": [("ei", "mitään", "hätää"), ("ei", "se", "mitään")],
}