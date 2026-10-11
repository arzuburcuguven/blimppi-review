DUTCH_ENV_BUCKET = {
    # neg (core negation)
    "niet": "neg", "geen": "n_series_neg", "n-woord": "n_series_neg", "negatief predicaat": "neg_predicate",
    "niet + universele kwantor": "neg", "niet veel": "neg",
    # DE_licensor (everything previously weak_nonveridical now folds here too)
    "evenmin": "DE_licensor", "zomin": "DE_licensor", "geenszins": "DE_licensor",
    "allerminst": "DE_licensor", "allesbehalve": "DE_licensor", "verre van": "DE_licensor",
    "nul": "DE_licensor", "voor(dat)": "DE_licensor", "voor etc.": "DE_licensor",
    "de/het enige": "DE_licensor", "de enige": "DE_licensor",
    "nauwelijks": "DE_licensor", "amper": "DE_licensor", "weinig": "DE_licensor",
    "zelden": "DE_licensor", "moeilijk": "DE_licensor", "onmogelijk": "DE_licensor",
    "minder": "DE_licensor", "hoogstens": "DE_licensor", "restrictief bijwoord": "DE_licensor",
    "finale bijzin": "DE_licensor", "concessieve bijzin": "DE_licensor", "te": "DE_licensor",
    "exclamatief": "DE_licensor", "lang geleden": "DE_licensor", "universele kwantor": "DE_licensor",
    # without
    "zonder": "without_pp_licensor", "buiten": "without_pp_licensor", "in plaats van": "without_pp_licensor",
    # conditional
    "conditionele bijzin": "conditional", "zodra": "conditional",
    "zolang": "conditional", "tenzij": "conditional",
    # question
    "vraag": "question",
    # comparative
    "comparatief": "comparative", "comparatief van gelijkheid": "comparative", "alsof": "comparative",
    # superlative
    "superlatief": "superlative", "de/het eerste": "superlative", "de eerste": "superlative",
    "de/het laatste": "superlative", "de laatste": "superlative",
    # positive-polarity mass
    "een positief voorkomen": "undetected_other",
}

import re, pandas as pd
from config.paths import FINAL_PAIRS
from pathlib import Path

TRIGGER_RE = re.compile(r'(\d+)\s*x?\s+([^()]+?)\s*\([\d,]+\s*%\)')

def parse(text):
    counts, unmapped = {}, []
    for m in TRIGGER_RE.finditer(text):
        n, lab = int(m.group(1)), m.group(2).strip().lower()
        b = DUTCH_ENV_BUCKET.get(lab)
        if b is None:
            unmapped.append((lab, n)); continue
        counts[b] = counts.get(b, 0) + n
    return counts, unmapped

def build(hoeksema, out_path, min_freq=20, threshold=0.6):
    rows = []
    for lemma, text in hoeksema.items():
        c, unmapped = parse(text)
        for lab, n in unmapped:
            print(f"  [{lemma}] UNMAPPED {lab!r} (n={n})")
        total = sum(c.values())
        licensed = total - c.get("undetected_other", 0)
        for env, n in c.items():
            rows.append({"lang": "Dutch", "lemma": lemma, "total": total,
                         "licensed": licensed,
                         "licensing_ratio": round(licensed/total, 3),
                         "env": env, "env_count": n,
                         "env_share": round(n/total, 4),
                         "min_freq": min_freq, "threshold": threshold})
    df = pd.DataFrame(rows)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(df.to_string(index=False)); return df

if __name__ == "__main__":
    HOEKSEMA = {
        "ook maar": "Triggers (6788 voorkomens): 2x allerminst (0,03%), 64x alsof (1%), 40x comparatief (1%), 3x comparatief van gelijkheid (0,04%), 4x concessieve bijzin (0,1%), 994x conditionele bijzin (15%), 2x  de/het eerste (0,03%), 2x de/het enige  (0,03%), 3x de laatste (0,04%), 25x evenmin (0,4%), 2x exclamatief (0,03%), 57x finale bijzin (1%), 479x geen (7%), 2x geenszins (0,03%),1x minder (0,01%), 5x moeilijk (0,1%),13x nauwelijks (0,2%), 2x niet + universele kwantor (0,03%), 797x niet (12%), 994x n-woord (15%),1x onmogelijk (0,01%), 598x negatief predicaat (9%), 8x restrictief bijwoord (0,1%), 6x superlatief (0,1%),120  te (2%), 358x universele kwantor (5%), 205x voor(dat) (3%), 434x vraag (6%),13x weinig  (0,2%), 5x zelden (0,1%), 90x zodra (1%), 7x  zolang (0,1%), 5x zomin (0,1%),1419x zonder  (21%) en 24x een positief voorkomen (0,4%). Verdere waren enkele gevallen lastig te klassificeren (4x).",
        "hoeven": "Triggers (5189 voorkomens): 3x allerminst (0,1%), 2x allesbehalve (0,04%), 10x amper (0,2%), 10x comparatief (0,2%), 1x comparatief van gelijkheid (0,02%), 76x de/het  enige (1%), 6x de/het laatste (0,1%), 23x evenmin (0,4%), 1x finale bijzin (0,02%),  555x geen (11%), 7x geenszins (0,1%), 1x lang  geleden (0,02%), 2x hoogstens (0,04%), 62x minder (1%), 39x nauwelijks (1%), 166x niet + universele kwantor (3%), 2607x niet  (50%), 26x niet veel (1%), 2x nul (0,04%), 496x n-woord (10%), 5x negatief predicaat (0,1%), 815x restrictief bijwoord (16%), 2x superlatief (0,04%), 1x te (0,02%), 17x universele kwantor (0,3%), 5x voor(dat) (0,1%), 48x vraag (1%), 54x weinig (1%), 7x zelden (0,1%), 130x zonder (3%) en 9x een positief voorkomen (0,2%).",
        "mals": "4x allesbehalve (1%), 1x evenmin (0,3%), 7x geen (2%), 1x  minder (0,3%), 266x niet (92%), 3x niet + universele kwantor (1%), 1x n-woord (0,3%),  2x verre van (1%), 4x weinig (1%). De voorkomens met geen maken steeds deel uit van dezelfde NP.",
        "pluis": "Triggers (261 voorkomens): 6x allerminst (2%), 1x allesbehalve (0,4%) 3x conditionele bijzin (1%), 2x evenmin (1%), 1x minder (0,4%), 231x niet (89%), 5x n-woord (2%), 5x verre van (2%), 3x vraag (1%) en 3x een positief voorkomen (1%).",
        "enig": "Triggers (5011 voorkomens): 1x allerminst (0,02%), 5x alsof (0,1%), 2x amper (0,04%), 3x buiten (0,1%), 564x comparatief (11%), 56x comparatief van gelijkheid (1%), 5x concessieve bijzin (0,1%), 269x conditionele bijzin (5%), 2x de eerste (0,04%), 1x de enige (0,02%), 32x evenmin (1%), 1x exclamatief (0,02%),60x finale bijzin (1%), 281x geen (6%), 5x  geenszins (0,1%), 2x in plaats van (0,04%),  2x minder (0,04%), 27x nauwelijks (1%), 498x niet (10%), 761x n-woord (15%), 286x negatief predicaat (6%), 10x restrictief bijwoord (0,2%), 40x superlatief (1%), 41x te (1%), 3x tenzij (0,1%), 62x universele kwantor (1%), 49x voor etc. (1%), 518x vraag (10%), 11x weinig (0,2%), 18x zelden (0,4%), 11x zodra (0,2%), 901x zonder (18%) en 480x een positief voorkomen (10%). Bij de positieve voorkomens kan worden gemeld dat de gegevens uit de 21ste eeuw (902 zinnen) nog maar 5% positieve voorkomens hebben, en als we de vaste combinatie op  enig moment verwijderen zakt dit percentage  nog verder naar onder de 2%.",
        "hand voor ogen": "Triggers (66 voorkomens): 1x amper (2%), 61x geen (92%), 2x nauwelijks (3%), 1x niet (2%), 1x zonder (2%)",
    }
    build(HOEKSEMA,
          FINAL_PAIRS / "dutch" / "dutch_stats.csv")
    


