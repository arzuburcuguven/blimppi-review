from multiblimp.treebank import Treebank
from collections import defaultdict
from blimppi.base_detectors import get_clause_head_id, has_fixed_relation, apply_bigrams, resolve_licensor, build_clause_graph, is_verbless_fragment, in_blocked_phrase, gar_is_npi, write_stats
import json
from blimppi.blacklist import BLACKLIST
import re


"""
TODO: A general InflectSubtree rule that recursively inflects all dependents of a given head, for slavic genitive
TODO: How do I incorporate NPIs licensed in clausal objects. Does licensing apply to all clausal objects? 
Can I use discovery through heuristics for this licensing environ through heuristics? My data is too sparse, can I trust a new neural parsers ability to 
correctly identify matrix clause head, whether its negated and then if it correcly identifies that the dependent clause is in object position? How D trees look like.
TODO: How do I incoprote lang specific environment-removal pairs in this pipeline.
TODO: check the reliablity of ccomp vs advcl through cog verbs
"""

    
class LanguageConfig:
    def __init__(
        self,
        language,
        removal_rules,
        npi_upos=None,
        npi_lemmas=None,
        npi_forms=None,
        min_freq=10,
        threshold=0.60,
        exclude_lemmas=None,
        inflector=None,
        noun_inflector=None,
        npi_environments=None,
        neg_lemmas=None,
        skip_pair_environments=None,
        max_sent_len=None,
        direction_environments=None,
        comparative_markers=None,
        conditional_markers=None,
        extra_licensors=None,
        bigrams=None,
        extra_detectors = None,
        n_series= None,
        interclause_licensor = None,
        negative_predicates = None,
        neg_coord = None,
        npi_lemma_upos = None,
        npi_allowed_envs = None,
        bad_modified_substrings: set = None,
        bad_modified_regexes: list = None
        
    ):
        self.lang = language
        self.removal_rules = removal_rules
        self.npi_upos = npi_upos        # e.g. {"PRON", "ADV", "DET"}
        self.npi_lemmas = npi_lemmas    # e.g. {"nada", "nadie"} or None
        self.min_freq = min_freq
        self.threshold = threshold
        self.exclude_lemmas = exclude_lemmas or set()
        self.inflector = inflector
        self.noun_inflector = noun_inflector
        self.npi_environments= npi_environments or {"neg"}
        self.neg_lemmas= neg_lemmas or set()
        self.skip_pair_environments=skip_pair_environments or set()
        self.max_sent_len = max_sent_len or 25
        self.npi_forms = npi_forms
        self.direction_environments = direction_environments or {}
        self.comparative_markers = comparative_markers or {}
        self.conditional_markers = conditional_markers or {}
        self.extra_licensors = extra_licensors or {}
        self.bigrams = bigrams or []
        self.extra_detectors = extra_detectors or []
        self.n_series = n_series or {}
        self.interclause_licensor = interclause_licensor or {}
        self.negative_predicates = negative_predicates or {}
        self.neg_coord = neg_coord or {}
        self.npi_lemma_upos = npi_lemma_upos or {}     
        self.npi_allowed_envs = npi_allowed_envs or {}     # <-- add
        self.bad_modified_substrings = bad_modified_substrings or ()
        self.bad_modified_regexes = bad_modified_regexes or []

def tokens_to_string(token_list):
    """Reconstruct sentence using range tokens when available, otherwise integer tokens."""
    # Separate range and integer tokens
    range_tokens = {
        t["id"]: t 
        for t in token_list 
        if isinstance(t["id"], tuple) and t["id"][1] == "-" and t["form"] != "_"
    }
    
    int_tokens = [t for t in token_list if isinstance(t["id"], int)]
    int_tokens.sort(key=lambda x: x["id"])  # ensure proper order
    
    parts = []
    i = 0
    
    while i < len(int_tokens):
        token = int_tokens[i]
        tid = token["id"]
        
        # Check if this token is covered by a range token
        covering_range = None
        for (start, _, end), range_tok in range_tokens.items():
            if start <= tid <= end:
                covering_range = (start, end, range_tok)
                break
        
        if covering_range:
            start, end, range_tok = covering_range
            # Use the fused surface form from range token
            parts.append(range_tok["form"])
            
            # Handle spacing - use range token's SpaceAfter
            range_misc = range_tok.get("misc") or {}
            no_space_after = range_misc.get("SpaceAfter") == "No"
            
            # Skip all tokens covered by this range
            while i < len(int_tokens) and start <= int_tokens[i]["id"] <= end:
                i += 1
                
            # Add space if needed and not at end
            if not no_space_after and i < len(int_tokens):
                parts.append(" ")
        else:
            # Use individual token
            form = token["form"]
            misc = token.get("misc") or {}
            no_space_after = misc.get("SpaceAfter") == "No"
            
            parts.append(form)
            i += 1
            
            # Add space if needed and not at end  
            if not no_space_after and i < len(int_tokens):
                parts.append(" ")
    
    s = "".join(parts)
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    s = s.replace('\u2018', "'").replace('\u2019', "'")
    # collapse stray space before closing punctuation (Latin + Arabic/Persian)
    s = re.sub(r"\s+([,;:.!?…)\]}»”’،؛؟])", r"\1", s)
    # collapse stray space after opening brackets/quotes
    s = re.sub(r"([(\[{«“‘])\s+", r"\1", s)
    return s.strip().strip('"').strip("'")

def iter_npi_tokens(token_dict, config, candidates=None):
    DISCOURSE_DEPRELS = {"discourse", "parataxis", "vocative"}
    for tid, token in token_dict.items():
        if not isinstance(tid, int):
            continue
        lemma, upos = token["lemma"], token["upos"]

        if candidates is not None and lemma not in candidates:
            continue
        if config.npi_lemma_upos:
            allowed = config.npi_lemma_upos.get(lemma)
            if allowed is None or upos not in allowed:
                continue
        elif config.npi_lemmas:
            if lemma not in config.npi_lemmas:
                continue
            if config.npi_upos and upos not in config.npi_upos:
                continue

        if config.npi_forms and token["form"] not in config.npi_forms:
            continue
        if lemma in (config.exclude_lemmas or ()):
            continue
        if token.get("deprel") in DISCOURSE_DEPRELS:
            continue
        if config.lang != "indonesian" and has_fixed_relation(token, token_dict, bigrams=config.bigrams):
            continue
        if lemma == "gar" and not gar_is_npi(token, token_dict):
            continue
        if lemma == "anything" and token["deprel"] in {"nsubj", "nsubj:pass"}:
            continue
        if config.lang in {"Spanish", "Catalan", "Norwegian-Bokmaal", "Norwegian-Nynorsk"}:
            ch = get_clause_head_id(tid, token_dict)
            if ch is None or tid < ch or token["deprel"] == "nsubj":
                continue

        yield tid, token



def run_pipeline(config, resource_dir):
    diagnostics = defaultdict(int)
    blocked_ids = BLACKLIST.get(config.lang, set())
   
    # 1. Load treebank
    treebank = Treebank(config.lang, resource_dir=resource_dir, 
                      use_selected_treebanks=True, verbose=True)
    
    # 2. First pass — count lemma occurrences (using only int tokens for logic)
    lemma_counts = defaultdict(lambda: {"neg": 0, "total": 0, "undetected":0, "licensed":0, "unlicensed":0, "multi_licensor":0, "environments": defaultdict(int)})
    undetected_examples = defaultdict(list)
    multi_licensor_examples = defaultdict(list)
    unlicensed_examples = defaultdict(list)
    licensed_skip_examples = defaultdict(list)
    NON_PAIRABLE_ENVS = {"multiple_licensors", "multiple_matrix_licensors", "local_plus_matrix"}
    
    for tree in treebank:
        sent_id = tree.metadata.get("sent_id", None)
        token_dict = {t["id"]: t for t in tree if isinstance(t["id"], int)}
        if len(token_dict) > config.max_sent_len:
            continue
        if sent_id in blocked_ids:
            continue
        if config.bigrams:
            token_dict = apply_bigrams(token_dict, config.bigrams)
        graph = build_clause_graph(token_dict)

        for tid, token in iter_npi_tokens(token_dict, config):
            lemma = token["lemma"]

            if token["head"] == 0 or token["deprel"] == "root":
                diagnostics["candidate_is_root"] += 1

            clause_head_id = get_clause_head_id(tid, token_dict)
            if clause_head_id is None:
                continue

            lemma_counts[lemma]["total"] += 1

            neg_id, env, locality = resolve_licensor(tid, token_dict, graph, config)
            if env is not None:
                lemma_counts[lemma]["environments"][env] += 1
            if tid == neg_id:
                continue

            sent_str = tokens_to_string(tree)
            if env is None:
                lemma_counts[lemma]["undetected"] += 1
                undetected_examples[lemma].extend([sent_str, sent_id])
            elif env in NON_PAIRABLE_ENVS:
                lemma_counts[lemma]["multi_licensor"] += 1
                multi_licensor_examples[lemma].extend([sent_str, sent_id])
            elif env in config.npi_environments:
                lemma_counts[lemma]["licensed"] += 1
                if env in config.skip_pair_environments:
                    licensed_skip_examples[lemma].extend([sent_str, sent_id, env])
            else:
                lemma_counts[lemma]["unlicensed"] += 1
                unlicensed_examples[lemma].extend([sent_str, sent_id])


    candidates = set()
    for lemma, counts in lemma_counts.items():
        if counts["total"] < config.min_freq:
            continue
        if counts["licensed"] / counts["total"] < config.threshold:
            continue
        
        # reject if a skip environment is the largest single environment
        envs = counts["environments"]
        if envs:
            dominant_env = max(envs, key=envs.get)
            if dominant_env in config.skip_pair_environments:
                continue
        
        candidates.add(lemma)

 ############################### Second pass - build minimal pairs  ###############################  ###############################  ############################### 
    
    sent_data = []
    blocked_pairs = []
    for tree in treebank:
        sent_id = tree.metadata.get("sent_id", None)

        if sent_id in blocked_ids:
            continue
        token_dict = {t["id"]: t for t in tree if isinstance(t["id"], int)}
        if len(token_dict) > config.max_sent_len:
            continue

        licensor_to_npis = defaultdict(list)
        if sent_id == "test-s702 ":
            print("\n=== test-s702  injected token_dict ===")
            for tid in sorted(token_dict):
                t = token_dict[tid]
                print(f"  {tid:2d}  {t['form']:<10} lemma={t['lemma']:<10} "
                    f"upos={t['upos']:<6} head={t['head']:<3} dep={t.get('deprel')}")
            
        if config.bigrams:
            token_dict = apply_bigrams(token_dict, config.bigrams)
        graph = build_clause_graph(token_dict)

        npi_tokens_in_sentence = [t for _, t in iter_npi_tokens(token_dict, config, candidates)]

        for tid, token in iter_npi_tokens(token_dict, config, candidates):
            if is_verbless_fragment(token_dict):
                diagnostics["verbless_fragment"] += 1
                continue
            if in_blocked_phrase(tid, token_dict):
                diagnostics["blocked_idiom"] += 1
                continue

            clause_head_id = get_clause_head_id(tid, token_dict)
            if clause_head_id is None:
                diagnostics["no_clause_head"] += 1
                continue

            neg_id, env, locality = resolve_licensor(tid, token_dict, graph, config)

            if neg_id is None:
                diagnostics[f"unresolved_{locality}_{env}"] += 1
                continue
            if env in config.skip_pair_environments:
                diagnostics["excluded_environment"] += 1
                blocked_pairs.append({
                    "original": tokens_to_string(tree),
                    "npi_lemma": token["lemma"],
                    "npi_form": token["form"],
                    "npi_id": token["id"],
                    "neg_id": neg_id,
                    "environment": env,
                    "locality": locality,
                    "sent_id": sent_id,
                    "reason": "skip_pair_environment",
                })
                continue
            if env not in config.npi_environments:
                diagnostics["unlicensed_environment"] += 1
                continue

            licensor_to_npis[neg_id].append((token["id"], env, locality))

            # Use full tree for original reconstruction
        original_string = tokens_to_string(tree)
        for neg_id, npi_list in licensor_to_npis.items():
            _, env, locality = npi_list[0]
            modified_tokens, modified_string, status = None, None, None
            matched_direction = None
            SKIP_STATUSES = {"skip_degil", "skip_yok_cop"} ##TODO this is silly

            for rule in config.removal_rules:
                direction = None
                if hasattr(rule, "action") and hasattr(rule.action, "direction"):
                    direction = rule.action.direction
                
                # If this rule has a direction with env restrictions, check them ????????????????????????????
                if direction and direction in config.direction_environments:
                    if env not in config.direction_environments[direction]:
                        continue
                
                npi_id = npi_list[0][0]  # use first NPI for rule application
                modified_tokens, modified_string, status = rule(
                    tree, token_dict, neg_id=neg_id, npi_id=npi_id
                )
                if status == "success" or status in SKIP_STATUSES:
                    matched_direction = direction
                    break

            diagnostics[status or "no_rule_matched"] += 1

            if status in SKIP_STATUSES or status is None:
                continue
            if status == "success" and original_string == modified_string:
                diagnostics["identical_pair"] += 1
                continue

            distances = [abs(neg_id - npi_tok["id"]) for npi_tok in npi_tokens_in_sentence]
            min_distance = min(distances) if distances else -100

            base_entry = {
                "original": original_string,
                "npi_lemma": token_dict[npi_list[0][0]]["lemma"],
                "npi_form": token_dict[npi_list[0][0]]["form"],
                "lang": config.lang, "status": status, "environment": env,
                "locality": locality, "neg_id": neg_id, "npi_id": npi_list[0][0],
                "sent_id": sent_id,
                "sentence_npi_count": len(npi_tokens_in_sentence) > 1,
                "npis_on_licensor": len(npi_list), "min_npi_distance": min_distance,
                "swap_direction": matched_direction or "unknown",
                "neg_form": token_dict[neg_id]["form"] if neg_id in token_dict else None,
            }

            # Swap emits a gradient: one row per quantity level. Works whether the
            # matched rule is a bare Swap or a ConditionalRule wrapping one.
            expander = getattr(rule, "expand", None) or \
                       getattr(getattr(rule, "action", None), "expand", None)
            if expander:
                for _, v_string, _, level, repl in expander(tree, token_dict, neg_id):
                    if v_string == original_string:
                        diagnostics["identical_pair"] += 1
                        continue
                    sent_data.append({**base_entry, "modified": v_string,
                                      "quantity_level": level, "replacement": repl,
                                      "swap_direction": "increasing"})
            else:
                sent_data.append({**base_entry, "modified": modified_string,
                                  "quantity_level": None, "replacement": None})

    output = {
        "language": config.lang,
        "candidates": sorted(candidates),
        "pairs": sent_data,
        "blocked_pairs": blocked_pairs,
        "diagnostics": dict(diagnostics),
        "lemma_counts": {
            lemma: {
                **counts,
                "environments": dict(counts["environments"]),
                "licensing_ratio": round(counts["licensed"] / counts["total"], 3) if counts["total"] > 0 else 0,
                "undetected_examples": undetected_examples.get(lemma, []),
                "multi_licensor_examples": multi_licensor_examples.get(lemma, []),
                "unlicensed_examples": unlicensed_examples.get(lemma, []),
            }
            for lemma, counts in lemma_counts.items()
            if lemma in candidates
        },
    }

    return output

EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emoticons, pictographs, transport, supplemental
    "\u2600-\u27BF"           # misc symbols + dingbats
    "\u2B00-\u2BFF"           # misc symbols and arrows
    "\u20E3\u3030\u303D\u3297\u3299\u2122\u2139"
    "]"
)

TAG_RE = re.compile(r"<[^>]*>")
ENTITY_RE = re.compile(r"&(?:amp|lt|gt|quot|nbsp|#\d+);")
URL_RE = re.compile(r"(?:https?://|www\.)[^\s)\]}»\"']+")

# Junk in every script: controls, bidi marks, invisible operators, emoji debris.
JUNK_RE = re.compile(
    "["
    "\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f"  # control chars
    "\u00ad"          # soft hyphen
    "\u200b"          # zero-width space
    "\u200e\u200f"    # LTR/RTL marks
    "\u202a-\u202e"   # bidi embedding controls
    "\u2060-\u2064"   # word joiner + invisible operators
    "\ufe00-\ufe0f"   # variation selectors
    "\ufeff"          # BOM
    "]"
)

# ZWNJ/ZWJ are orthographic BETWEEN letters (Persian, Sinhala, Indic);
# junk when orphaned at word edges (emoji debris).
ORPHAN_JOINER_RE = re.compile(r"(?:(?<=\s)|^)[\u200c\u200d]+|[\u200c\u200d]+(?:(?=\s)|$)")


def clean_text(s):
    if s is None:
        return s
    s = TAG_RE.sub("", s)                              # strip tags, keep inner text
    s = ENTITY_RE.sub(" ", s)
    s = URL_RE.sub("", s)                              # drop bare/leftover URLs
    s = s.replace('\u201c', '"').replace('\u201d', '"')
    s = s.replace('\u2018', "'").replace('\u2019', "'")
    s = EMOJI_RE.sub("", s)
    s = s.replace("\t", " ").replace("\n", " ").replace("\r", " ")
    s = JUNK_RE.sub("", s)
    s = ORPHAN_JOINER_RE.sub("", s)
    s = re.sub(r"\(\s*\)|\[\s*\]", "", s)              # empty brackets left behind
    s = re.sub(r"\s+([,;:.!?…)\]}»”’،؛؟])", r"\1", s)  # no space before closing punct
    s = re.sub(r"([(\[{«“‘])\s+", r"\1", s)            # no space after opening punct
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip().strip('"').strip("'")


def save_output(output, config, output_dir):
    import os
    os.makedirs(output_dir, exist_ok=True)

    summary_path = os.path.join(output_dir, f"{config.lang.lower()}_output.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    write_stats(output, config, output_dir)   # <-- here
    


    print(f"Summary saved to {summary_path}")
    # Print environment distribution per lemma
    print("\n--- Environment distribution ---")
    for lemma, counts in output["lemma_counts"].items():
        total = counts["total"]
        print(f"\n{lemma} (total={total}, ratio={counts['licensing_ratio']}):")
        for env, count in sorted(counts["environments"].items(), key=lambda x: -x[1]):
            print(f"  {env}: {count} ({round(count/total*100, 1)}%)")

    # Save minimal pairs as TSV
    pairs_path = os.path.join(output_dir, f"{config.lang.lower()}_minimal_pairs.tsv")
    with open(pairs_path, "w", encoding="utf-8") as f:
        f.write("sen\twrong_sen\tlemma\ttoken_form\tswap_direction\tnpi_to_neg_distance\t"
                "sent_len\tenv\tsentence_npi_count\tnpis_on_licensor\tsent_id\tquantity_level\treplacement\n")
        seen = set(); count = 0
        for pair in output["pairs"]:
            if pair["modified"] is None: 
                continue
            mod = pair["modified"]
            if any(s in mod for s in config.bad_modified_substrings):
                continue
            if any(re.search(p, mod) for p in config.bad_modified_regexes):
                continue
            orig = clean_text(pair["original"]); mod = clean_text(pair["modified"])
            if (orig, mod) in seen:                       # was: dedup on orig alone
                continue
            seen.add((orig, mod))
            direction = pair["swap_direction"]            # extracted -> no nested quotes
            sent_len = len(orig.split())
            f.write(f"{orig}\t{mod}\t{pair['npi_lemma']}\t{pair['npi_form']}\t{direction}\t"
                    f"{pair.get('min_npi_distance', -100)}\t{sent_len}\t{pair.get('environment')}\t"
                    f"{pair.get('sentence_npi_count', 1)}\t{pair.get('npis_on_licensor', 1)}\t"
                    f"{pair.get('sent_id','')}\t{pair.get('quantity_level','')}\t{pair.get('replacement','')}\n")
            count += 1
    print(f"Pair count: {count}")

