
############################################################ Negation Env #########################################################################


def has_neg_dependent(clause_head_id, token_dict, neg_lemmas):
    for tid, token in token_dict.items():
        if token["deprel"] in ("advmod", "advmod:neg", "compound", "compound:lvc", "cop", "aux", "aux:pass") and token["head"] == clause_head_id:
            feats = token["feats"] or {}
            if feats.get("Polarity") == "Neg":
                return tid
        if token["deprel"] in ("advmod", "advmod:neg", "aux") and token["head"] == clause_head_id:
            if token.get("lemma") in neg_lemmas:
                return tid
    return None

def _is_negated_base(clause_head_id, token_dict, neg_lemmas):
    if neg_lemmas and token_dict[clause_head_id]["lemma"] in neg_lemmas:
        return clause_head_id
    if clause_head_id is None or clause_head_id == 0:
        return None
    feats = token_dict[clause_head_id]["feats"] or {}
    if feats.get("Polarity") == "Neg":
        return clause_head_id
    return None

def is_n_neg(clause_head_id, token_dict, n_series,npi_id
            ):
    """
    Detect an n-series word licensing within the clause headed by clause_head_id.

    Position 1 — direct dependent of the clause head:
        "Nothing happened"   nothing --nsubj--> happened
        "He never came"      never   --advmod--> came
    Position 2 — determiner on the SUBJECT of the clause head:
        "No preacher has ever..."   no --det--> preacher --nsubj--> has
        "neither one had ever..."   neither --det--> one --nsubj--> had
    """
    # position 1 
    for t in token_dict.values():
        if t.get("lemma") in n_series and t["head"] == clause_head_id:
            return t["id"]

    # position 2: n-determiner on a subject argument of the clause head
    # licensing only when it precedes the NPI
    arg_deprels = {"nsubj", "nsubj:pass", "obj", "iobj", "obl"}
    for arg in token_dict.values():
        if arg.get("head") == clause_head_id and arg.get("deprel") in arg_deprels:
            for t in token_dict.values():
                if (t.get("lemma") in n_series
                        and t["head"] == arg["id"]
                        and t.get("deprel") in {"det", "det:predet"}
                        and t["id"] < npi_id):          # precedence guard
                    return t["id"]
    return None

def negated_matrix_clause(clause_head_id, token_dict, neg_lemmas):
    # if the other negations fail
    clause_token = token_dict[clause_head_id]
    # if the clause head of the candidate have ccomp or csubj or csubj:cop relations going out of it
    if clause_token["deprel"] in ("ccomp", "csubj", "csubj:cop", "xcomp"):
        # if the end point of the such relations (i.e. the matrix clause) either is a negated verb itself. or has neg dependent
        matrix_head_id = clause_token["head"] 
        if matrix_head_id == 0 or matrix_head_id not in token_dict:  
            return None
        matrix_token = token_dict[matrix_head_id]  
        
        feats = matrix_token["feats"] or {}        
        if feats.get("Polarity") == "Neg":
            return matrix_head_id
        
        neg_id = has_neg_dependent(matrix_head_id, token_dict, neg_lemmas)
        if neg_id:
            return neg_id
        neg_id = _is_negated_base(matrix_head_id, token_dict, neg_lemmas)
        if neg_id:
            return neg_id
    
    return None

def has_neg_predicate_dependent(clause_head_id, token_dict, neg_predicates):
    head = token_dict.get(clause_head_id, {})
    # case 1: the head itself (e.g. a finite verb like विरोध करना lemmatized oddly)
    if head.get("lemma") in neg_predicates:
        return clause_head_id
    # case 2: light-verb construction — noun dependent carries the meaning
    for tid, t in token_dict.items():
        if t["head"] == clause_head_id and t.get("lemma") in neg_predicates:
            if t.get("deprel") in ("compound", "compound:lvc", "obj", "obl", "nmod"):
                return tid
    return None


############################################################ Question Env #########################################################################


def is_question_env(clause_head_id, token_dict):
    head = token_dict.get(clause_head_id)
    if not head:
        return False
    
    # 1. Check for ? in punctuation dependents
    for tok in token_dict.values():
        if tok.get("head") == clause_head_id and tok.get("form") == "?":
            return True
    
    # 2. Check for interrogative wh-words (PronType=Int) anywhere in clause
    for tok in token_dict.values():
        feats = tok.get("feats") or {}
        if feats.get("PronType") == "Int":
            return True
        
    return False

def find_subject_aux_inversion(clause_head_id, token_dict):

    head = token_dict.get(clause_head_id)
    if not head:
        return None

    # locate the finite AUX (or finite verb) in this clause
    aux = None
    for t in token_dict.values():
        if t.get("upos") == "AUX" and (t.get("feats") or {}).get("VerbForm") == "Fin":
            # aux attaches to clause head (or is the head)
            if t.get("head") == clause_head_id or t["id"] == clause_head_id:
                aux = t
                break
    # exclude do-support (handled above)

    if aux is None:
        return None
    if aux.get("lemma") == "do":
        return None


    # locate the subject of the clause
    subj = None
    for t in token_dict.values():
        if t.get("deprel") in {"nsubj", "nsubj:pass"} and \
           t.get("head") in {clause_head_id, aux["id"]}:
            subj = t
            break
    if subj is None:
        return None

    # exclude expletive subjects: "Has there been...", "Is there..."
    if subj.get("deprel") == "expl" or subj.get("lemma") in {"there", "it"}:
        return None
    # INVERSION test: aux must LINEARLY PRECEDE its subject
    if int(aux["id"]) >= int(subj["id"]):
        return None      # normal SV order, no inversion -> not this environment

    # EXCLUDE wh-questions: if a wh-word (PronType=Int) sits before the aux,
    WH = {"who","what","which","whose","why","how","where","when","whom"}
    for t in token_dict.values():
        feats = t.get("feats") or {}
            
        if (feats.get("PronType") == "Int" or (t.get("lemma") or "").lower() in WH) \
            and int(t["id"]) < int(aux["id"]):
            return None
    

    return {"aux_id": aux["id"], "subj_id": subj["id"]}

############################################################ Comparative Env #########################################################################

def is_comparative(token_id, clause_head_id, token_dict, comparative_markers):
    """
    Check whether the NPI candidate (token_id) appears inside a comparative clause.
    
    Handles two structural patterns:
    
    Path 1a — marker heads the NPI directly:
        "dan ooit" / "than ever"
        than(mark) → ever(NPI)
        ever.head == than's head → npi_candidate IS the NPI
    
    Path 1b — marker is deeper, NPI connects to clause head:
        "than she has ever heard"
        than(mark) → heard → listened(clause_head)
        npi_candidate.head == clause_head_id
    
    Path 2 — NPI and marker share the same head:
        "more closely than I've ever listened"
        both "than" and "ever" hang off "listened"
        token.head == npi_candidate.id (than's head)
    """
    if not comparative_markers:
        return None

    for tid, t in token_dict.items():
        # Find a comparative marker token (e.g. "than", "dan")
        if t.get("lemma") not in comparative_markers:
            continue
        # Must function as a subordinator or case marker in the tree
        if t.get("deprel") not in {"mark", "case"}:
            continue
        # Climb one step up from the marker to its head
        # e.g. than → ever (path 1a) or than → heard (path 1b)
        npi_candidate = token_dict.get(t["head"], {})

        # Path 1b: marker's head connects up to the clause head
        # than → heard → listened(clause_head)
        if npi_candidate.get("head") == clause_head_id:
            return True

        # Path 1a: the token we're checking IS the marker's direct head
        # than → ever(token_id)
        if token_id == npi_candidate.get("id"):
            return True

        # Path 2: the NPI and the marker share the same head
        # both "than" and "ever" → listened
        actual_token = token_dict.get(token_id, {})
        if actual_token.get("head") == npi_candidate.get("id"):
            return True

    return None

############################################################ Conditional Env #########################################################################

def is_conditional(clause_head_id, token_dict, conditional_markers):
    if not conditional_markers:
        return None   
    for tid, t in token_dict.items():
        if (t.get("lemma") in conditional_markers
                and t.get("deprel") in {"mark", "case"}
                and token_dict.get(t["head"], {}).get("head") == clause_head_id):
            return True
    return None

############################################################ Superlative Env #########################################################################

def is_superlative(clause_head_id, token_dict):
    # case 1: ooit's clause head is directly modified by a superlative
    # (Witte Waan: ooit -> films <- beste)
    for tid, t in token_dict.items():
        if (t.get("head") == clause_head_id
                and (t.get("feats") or {}).get("Degree") == "Sup"):
            return tid

    # case 2: ooit's clause head is an acl/acl:relcl of a noun
    # that is modified by a superlative
    # (Harry Potter: ooit -> gekend(acl:relcl) -> potje <- beste)
    clause_token = token_dict.get(clause_head_id, {})
    if clause_token.get("deprel") in {"acl", "acl:relcl"}:
        noun_id = clause_token.get("head")
        if noun_id and noun_id in token_dict:
            for tid, t in token_dict.items():
                if (t.get("head") == noun_id
                        and (t.get("feats") or {}).get("Degree") == "Sup"):
                    return tid
    return None



############################################################ Basic Env Checker #########################################################################

def has_extra_licensor(clause_head_id, token_dict, licensor_lemmas, levels=1, npi_id=None):
    # we keep the levels here as 
    if not licensor_lemmas:
        return None
    for tid, t in token_dict.items():
        if tid == npi_id:
            continue
        if t.get("lemma") in licensor_lemmas:
            # level 1: direct dependent of clause head
            if t["head"] == clause_head_id:

                return tid
            # level 2+: walk up
            if levels is not None and levels >= 2:

                parent = token_dict.get(t["head"])
                if parent and parent["head"] == clause_head_id:
                    return tid
            if levels is not None and levels >= 3:
                if parent:
                    grandparent = token_dict.get(parent["head"])
                    if grandparent and grandparent["head"] == clause_head_id:
                        return tid
                    
    return None


#### generic detector dispatcher

def detect_environment(clause_head_id, token_dict, config, token_id=None):
    return detect_all_environments(clause_head_id, token_dict, config, token_id)[0]

def detect_all_environments(clause_head_id, token_dict, config, token_id=None):
    if clause_head_id == 0:
        root_id, _ = get_root(token_dict)
        clause_head_id = root_id

    results = []

    # negation family — these are mutually exclusive on one head,
    # but keep checking so concord (n_series + neg) both surface
    nid = _is_negated_base(clause_head_id, token_dict, config.neg_lemmas)
    if nid: results.append(("neg", nid))
    nid = has_neg_dependent(clause_head_id, token_dict, config.neg_lemmas)
    if nid: results.append(("neg", nid))
    nid = is_n_neg(clause_head_id, token_dict, config.n_series, token_id)
    if nid: results.append(("n_series_neg", nid))

    for detector_fn in config.extra_detectors:
        env, nid = detector_fn(clause_head_id, token_dict)
        if env: results.append((env, nid))

    if config.negative_predicates:
        npid = has_neg_predicate_dependent(clause_head_id, token_dict, config.negative_predicates)
        if npid:
            results.append(("neg_predicate", npid))

    if is_question_env(clause_head_id, token_dict):
        if config.lang in {"English","German","Dutch","Swedish","Danish","Norwegian","Icelandic"}:
            if find_subject_aux_inversion(clause_head_id, token_dict) is not None:
                results.append(("aux_inversion", clause_head_id))
            else:
                results.append(("question", None))
        else:
            results.append(("question", None))

    if is_comparative(token_id, clause_head_id, token_dict, config.comparative_markers):
        results.append(("comparative", None))
    if is_conditional(clause_head_id, token_dict, config.conditional_markers):
        results.append(("conditional", None))
    if is_superlative(clause_head_id, token_dict):
        results.append(("superlative", None))

    for licensor_lemmas, (env_label, levels) in config.extra_licensors.items():
        nid = has_extra_licensor(clause_head_id, token_dict, licensor_lemmas, levels=levels, npi_id=token_id)
        if nid: results.append((env_label, nid))

    return results or [("undetected", None)]

def build_clause_graph(token_dict, clause_head_upos={"VERB", "AUX"}):
    graph = {}
    for tid, tok in token_dict.items():
        if tok["upos"] not in clause_head_upos:
            continue
        parent_id = tok["head"]
        if parent_id == 0:
            graph[tid] = {"parent_head": None, "parent_rel": None}
            continue
        parent_tok = token_dict.get(parent_id)
        # If the head is itself verbal, IT is the parent clause head. The old
        # get_clause_head_id(parent_id) climbed PAST a verbal parent, skipping the
        # clause that held the licensor and landing the resolver on a far one.
        if parent_tok and parent_tok["upos"] in ("VERB", "AUX", "PART"):
            parent_clause_head = parent_id
        else:
            parent_clause_head = get_clause_head_id(parent_id, token_dict)
        graph[tid] = {
            "parent_head": parent_clause_head if parent_clause_head != 0 else None,
            "parent_rel": tok["deprel"],
        }
    return graph

def resolve_licensor(npi_id, token_dict, graph, config,
                     licensing_deprels={"xcomp", "ccomp", "conj"}):
    clause_head_id = get_clause_head_id(npi_id, token_dict)
    npi_form = token_dict.get(npi_id, {}).get("form", "?")
    npi_lemma = token_dict.get(npi_id, {}).get("lemma")

    SCOPERS = {"neg", "n_series_neg", "neg_predicate", "aux_inversion",
               "question", "only_licensor", "without_pp_licensor",
               "superlative", "conditional"}
    SUBJ_DEPRELS = {"nsubj", "nsubj:pass", "csubj", "csubj:pass"}
    WEAK_ENVS = {"modal_licensor"}

    allowed_envs = (config.npi_allowed_envs or {}).get(npi_lemma)

    def admissible(env):
        return allowed_envs is None or env in allowed_envs

    local_envs = [(e, n) for e, n in
                  detect_all_environments(clause_head_id, token_dict, config, token_id=npi_id)
                  if e != "undetected" and admissible(e)]

    matrix_hits = []
    seen = set()
    node_id = clause_head_id
    while node_id in token_dict:
        deprel = token_dict[node_id].get("deprel", "")
        head = token_dict[node_id]["head"]
        if not head or head == 0 or head in seen:
            break
        # only cross this clause boundary if the relation is permeable to scope
        if deprel not in licensing_deprels:
            break  # island (acl, acl:relcl, advcl, appos, ...) -> matrix can't reach in

        # S-coordination vs VP-coordination: if we're crossing a conj boundary and
        # this conjunct is self-contained (own subject OR own negation), it's an
        # independent clause -> a matrix/sibling licensor must not reach into it.
        if deprel == "conj":
            own_subject = any(t["head"] == node_id and t.get("deprel") in SUBJ_DEPRELS
                              for t in token_dict.values())
            own_neg = has_neg_dependent(node_id, token_dict, config.neg_lemmas)
            if own_subject or own_neg:
                break

        seen.add(head)
        envs = detect_all_environments(head, token_dict, config, token_id=npi_id)
        scopers = [(e, n) for e, n in envs if e in SCOPERS and admissible(e)]
        if scopers:
            matrix_hits.extend(scopers)
        node_id = head

    # A genuine scoper outranks a weak/free-choice environment in the same clause;
    # only collisions among scopers should count as ambiguous.
    if any(e not in WEAK_ENVS for e, _ in local_envs):
        local_envs = [(e, n) for e, n in local_envs if e not in WEAK_ENVS]

    if len(local_envs) > 1:
        return None, "multiple_licensors", "multiple_licensors"
    if len(matrix_hits) > 1:
        return None, "multiple_matrix_licensors", "non_pairable"
    if matrix_hits:
        env, nid = matrix_hits[0]
        if local_envs:
            return None, "local_plus_matrix", "non_pairable"
        if nid is None:                 
            return None, env, "no_licensor"
        return nid, env, "matrix"
    if not local_envs:
        return None, None, "no_licensor"
    env, neg_id = local_envs[0]
    return neg_id, env, "local"
