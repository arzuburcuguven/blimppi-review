import copy
import unicodedata
import pandas as pd
from blimppi.pipeline import tokens_to_string
from blimppi.base_detectors import get_clause_head_id, find_subject_aux_inversion


class ConditionalRule:
    def __init__(self, condition, action, check="auto"):
        # check: "npi", "neg", or "auto" (npi first, then neg)
        self.condition = condition
        self.action = action
        self.check = check

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        if self.check == "npi":
            check_tok = token_dict.get(npi_id) if npi_id is not None else None
        elif self.check == "neg":
            check_tok = token_dict.get(neg_id) if neg_id is not None else None
        else:  # auto: npi if usable, else neg
            if npi_id is not None:
                check_tok = token_dict.get(npi_id)
            elif neg_id is not None:
                check_tok = token_dict.get(neg_id)
            else:
                check_tok = None

        if check_tok is None:
            return None, None, "no_target_provided"
        if not self.condition(check_tok, token_dict):
            return None, None, "condition_not_met"
        return self.action(tree, token_dict, neg_id=neg_id, npi_id=npi_id)
        

class Drop:
    def __init__(self, lemmas):
        self.lemmas = lemmas

    @staticmethod
    def _first_lettered(tokens):
        for t in tokens:
            if any(ch.isalpha() for ch in (t["form"] or "")):
                return t
        return None

    @staticmethod
    def _capitalize_form(form):
        for j, ch in enumerate(form):
            if ch.isalpha():
                return form[:j] + ch.upper() + form[j + 1:]
        return form

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]

        if neg_id not in {t["id"] for t in int_tokens}:
            return None, None, "drop_failed"

        int_tokens.sort(key=lambda t: t["id"])
        first_word = self._first_lettered(int_tokens)
        neg_was_first = (
            first_word is not None
            and first_word["id"] == neg_id
            and any(ch.isalpha() and ch.isupper() for ch in first_word["form"])
        )

        modified_int = [t for t in int_tokens if t["id"] != neg_id]

        if modified_int and neg_was_first:
            new_first = self._first_lettered(modified_int)
            if new_first is not None:
                new_first["form"] = self._capitalize_form(new_first["form"])
                new_first_id = new_first["id"]

                # Mirror onto any range token covering the new first word,
                # because tokens_to_string prefers the range's fused form.
                for rt in range_tokens:
                    rid = rt["id"]
                    if isinstance(rid, tuple) and rid[1] == "-":
                        start, _, end = rid
                        if start <= new_first_id <= end and rt["form"] and rt["form"] != "_":
                            rt["form"] = self._capitalize_form(rt["form"])

        modified_tree = modified_int + range_tokens
        return modified_tree, tokens_to_string(modified_tree), "success"

class Swap:
    def __init__(self, form_map):
        self.form_map = form_map

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]

        if neg_id is None:
            return None, None, "no_neg_id"

        token_dict_copy = {t["id"]: t for t in int_tokens}
        neg_token = token_dict_copy.get(neg_id)

        if neg_token is None:
            return None, None, "neg_token_not_found"

        original_form = neg_token["form"]
        mapped_form = self.form_map.get(original_form.lower())

        if mapped_form is None:
            return None, None, f"form_not_in_map:{original_form}"

        if original_form[0].isupper():
            mapped_form = mapped_form[0].upper() + mapped_form[1:]

        modified_int = []
        for t in int_tokens:
            if t["id"] == neg_id:
                t["form"] = mapped_form
            modified_int.append(t)

        modified_tree = modified_int + range_tokens
        return modified_tree, tokens_to_string(modified_tree), "success"
    
def _subtree_ids(root_id, token_dict):
    ids, frontier = {root_id}, [root_id]
    while frontier:
        cur = frontier.pop()
        for t in token_dict.values():
            if t.get("head") == cur and t["id"] not in ids:
                ids.add(t["id"]); frontier.append(t["id"])
    return ids

def detok_in_order(token_list):
    """Like tokens_to_string but prints in the GIVEN order (no id sort)."""
    range_tokens = {
        t["id"]: t for t in token_list
        if isinstance(t["id"], tuple) and t["id"][1] == "-" and t["form"] != "_"
    }
    seq = [t for t in token_list if isinstance(t["id"], int)]   # NO .sort()
    parts, i = [], 0
    while i < len(seq):
        tid = seq[i]["id"]
        cov = None
        for (start, _, end), rtok in range_tokens.items():
            if start <= tid <= end:
                cov = (start, end, rtok); break
        if cov:
            start, end, rtok = cov
            parts.append(rtok["form"])
            no_space = (rtok.get("misc") or {}).get("SpaceAfter") == "No"
            while i < len(seq) and start <= seq[i]["id"] <= end:
                i += 1
            if not no_space and i < len(seq):
                parts.append(" ")
        else:
            parts.append(seq[i]["form"])
            no_space = (seq[i].get("misc") or {}).get("SpaceAfter") == "No"
            i += 1
            if not no_space and i < len(seq):
                parts.append(" ")
    s = "".join(parts)
    for a, b in (('\u201c','"'),('\u201d','"'),('\u2018',"'"),('\u2019',"'")):
        s = s.replace(a, b)
    return s.strip().strip('"').strip("'")

class UninvertAux:
    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        inv = find_subject_aux_inversion(neg_id, token_dict)   # neg_id = clause head
        if inv is None:
            return None, None, "no_inversion"
        aux_id, subj_id = inv["aux_id"], inv["subj_id"]

        int_tokens   = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]

        subj_right = max(_subtree_ids(subj_id, token_dict))     # multiword subject edge

        ordered = sorted(int_tokens, key=lambda t: t["id"])
        aux_tok = next(t for t in ordered if t["id"] == aux_id)
        if aux_tok["form"][:1].isupper():                       # de-capitalize moved aux
            aux_tok["form"] = aux_tok["form"][0].lower() + aux_tok["form"][1:]
        rest = [t for t in ordered if t["id"] != aux_id]

        out = []
        for t in rest:
            out.append(t)
            if t["id"] == subj_right:
                out.append(aux_tok)

        modified_tree = out + range_tokens
        s = detok_in_order(modified_tree)
        if s:
            s = s[0].upper() + s[1:]
        s = s.rstrip(" ?!") + "."
        return modified_tree, s, "success"

class Inflect:
    def __init__(self, inflector, default_features=None):
        self.inflector = inflector
        self.default_features = default_features or {}

    
    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        # Work only with int tokens for logic
    
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        # Keep range tokens unchanged
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]
        
        if neg_id is None:
            return None, None, "no_neg_token"
            
        token_dict_copy = {t["id"]: t for t in int_tokens}
        neg_token = token_dict_copy.get(neg_id)
        if neg_token is None:
            return None, None, "no_neg_token"

        ud_features = dict(neg_token["feats"] or {})
        # Lock output VerbForm to match input
        verbform = ud_features.get("VerbForm")  # e.g. "Fin", "Conv", "Part"
        strategies = []
        if verbform:
            # map UD VerbForm value to UM column format
            strategies = [{"VerbForm": f"VerbForm_{verbform}"}]

        forms, _ = self.inflector.inflect(neg_token["form"], ud_features, strategies=strategies)    
        if forms and len(forms) == 1:
            pos_form = forms[0]
        elif forms and len(forms) > 1:
            pos_form = min(forms, key=lambda f: abs(len(f) - len(neg_token["form"])))
        else:
            return None, None, "polarity_inflection_failed"
        
        modified_int = []
        for t in int_tokens:
            if t["id"] == neg_id:
                t["form"] = pos_form
                if t["feats"]:
                    t["feats"]["Polarity"] = "Pos"
                t["form"] = unicodedata.normalize("NFC", t["form"])
                t["form"] = t["form"].replace("i\u0307", "i")
                t["form"] = t["form"].replace("I\u0307", "İ")
            modified_int.append(t)

        # Combine modified int tokens with unchanged range tokens
        modified_tree = modified_int + range_tokens
        
        return modified_tree, tokens_to_string(modified_tree), "success"


# class NounInflect:
#     def __init__(self, noun_inflector):
#         self.noun_inflector = noun_inflector

#     def __call__(self, tree, token_dict, neg_id):
#         # Work only with int tokens for logic
#         int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
#         # Keep range tokens unchanged
#         range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]
        
#         if neg_id is None:
#             return None, None, "no_neg_token"
            
#         token_dict_copy = {t["id"]: t for t in int_tokens}
#         neg_token = token_dict_copy.get(neg_id)
#         if neg_token is None:
#             return None, None, "no_neg_token"

#         ud_features = dict(neg_token["feats"] or {})
#         forms, _ = self.noun_inflector.inflect(neg_token["form"], ud_features)
#         if forms and len(forms) == 1:
#             pos_form = forms[0]
#         elif forms and len(forms) > 1:
#             pos_form = min(forms, key=lambda f: abs(len(f) - len(neg_token["form"])))
#         else:
#             return None, None, "polarity_inflection_failed"
        
#         modified_int = []
#         for t in int_tokens:
#             if t["id"] == neg_id:
#                 t["form"] = pos_form
#                 if t["feats"]:
#                     t["feats"]["Polarity"] = "Pos"
#             modified_int.append(t)

#         # Combine modified int tokens with unchanged range tokens
#         modified_tree = modified_int + range_tokens
        
#         return modified_tree, tokens_to_string(modified_tree), "success"
    

class ContractedDrop:
    """Drop negation and promote any following Short-variant clitic to its long form."""
    def __init__(self, lemmas, inflector):
        self.drop = Drop(lemmas)
        self.inflector = inflector

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        modified_tree, modified_string, status = self.drop(
            tree, token_dict, neg_id, npi_id
        )
        if status != "success":
            return modified_tree, modified_string, status
        neg_token = token_dict.get(neg_id)
        misc = neg_token.get("misc") or {}
  
        if misc.get("SpaceAfter") == "No":
            next_token = token_dict.get(neg_id + 1)
            if next_token and (next_token.get("feats") or {}).get("Variant") == "Short":
                ud_features = {k: v for k, v in next_token["feats"].items() if k != "Variant"}
                forms, _ = self.inflector.inflect(next_token["form"], ud_features)
                if not forms:
                    return None, None, "contracted_drop_failed"
                # find the int token in modified_tree and swap it
                for t in modified_tree:
                    if isinstance(t["id"], int) and t["id"] == next_token["id"]:
                        t["form"] = forms[0]
                        break
                modified_string = tokens_to_string(modified_tree)

        return modified_tree, modified_string, status
    
class DropAndFixGenitive:
    """
    Drop a negation token, then fix genitive→accusative shift on the
    obj dependent of the clause head, if the verb is negation-induced.
    """
    def __init__(self, lemmas, neg_induced_verbs, obj_inflector):
        self.drop = Drop(lemmas)
        self.neg_induced_verbs = neg_induced_verbs
        self.obj_inflector = obj_inflector

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        # Step 1: do the normal drop
        modified_tree, modified_string, status = self.drop(
            tree, token_dict, neg_id=neg_id, npi_id=npi_id
        )
        if status != "success":
            return modified_tree, modified_string, status

        # Step 2: check if verb is negation-induced
        clause_head_id = get_clause_head_id(neg_id, token_dict)
        head = token_dict.get(clause_head_id)
        if head is None or head["lemma"] in self.neg_induced_verbs:
            return modified_tree, modified_string, "success_inherently"

        # Step 3: find genitive obj in the MODIFIED tree
        modified_token_dict = {t["id"]: t for t in modified_tree if isinstance(t["id"], int)}

        obj_token = None
        for tid, token in modified_token_dict.items():
            if token["deprel"] == "obj" and token["head"] == clause_head_id:
                feats = token.get("feats") or {}
                if feats.get("Case") == "Gen":
                    obj_token = token
                    break

        if obj_token is None:
            # No genitive obj found — drop was fine, just return as-is
            return modified_tree, modified_string, "success_no_obj"


        # Step 4: inflect obj to accusative
        ud_features = dict(obj_token.get("feats") or {})
        target_features = {**ud_features, "Case": "Acc"}

        print(f"[DEBUG GEN FIX] verb={head['lemma']} obj_form={obj_token['form']} obj_lemma={obj_token.get('lemma')} feats={ud_features} target={target_features}")

        forms, _ = self.obj_inflector.inflect(obj_token["form"], target_features)

        print(f"[DEBUG GEN FIX] forms returned: {forms}")
        
        if not forms:
            # Inflection failed — still return the drop, just without case fix
            return modified_tree, modified_string, "no_gen_fix"

        new_form = forms[0] if len(forms) == 1 else min(
            forms, key=lambda f: abs(len(f) - len(obj_token["form"]))
        )

        # Preserve capitalisation
        if obj_token["form"][:1].isupper():

            new_form = new_form[:1].upper() + new_form[1:]

        # Step 5: apply the form change to modified_tree
        for t in modified_tree:
            if isinstance(t["id"], int) and t["id"] == obj_token["id"]:
                t["form"] = unicodedata.normalize("NFC", new_form)
                if t["feats"] is not None:
                    t["feats"]["Case"] = "Acc"
                break

        modified_string = tokens_to_string(modified_tree)
        return modified_tree, modified_string, "success_gen_fix"


class LemmaSwapInflect:
    # Features that must match exactly between source and target form.
    # If the source has one of these set, the target form must have the same value.
    STRICT_FEATURES = ("Case", "Number", "Person", "Gender")

    def __init__(self, inflector, lemma_map, feature_updates=None, direction=None,
                 default_features=None, strict_features=None):
        self.inflector = inflector
        self.lemma_map = lemma_map
        self.feature_updates = feature_updates or {}
        self.direction = direction or self._infer_direction()
        self.default_features = default_features or {}
        # Allow per-instance override of which features to enforce strictly
        self.strict_features = tuple(strict_features) if strict_features is not None else self.STRICT_FEATURES

    

    def _infer_direction(self):
        prontype = self.feature_updates.get("PronType")
        if prontype == "Ind":
            return "neg2ind"
        elif prontype == "Neg":
            return "ind2neg"
        return "unknown"

    def _strict_lookup(self, lemma, ud_features):

        FEATURE_DEFAULTS = {"Number": "Sing"}

        # Build required dict from source features
        required = {}
        for feat in self.strict_features:
            val = ud_features.get(feat)
            if val is not None:
                required[feat] = val

        # Default missing Number to Sing on the source side
        if "Number" in self.strict_features and "Number" not in required:
            required["Number"] = "Sing"

        ud_inf = self.inflector.ud_inflector
        if ud_inf is None or not ud_inf.has_unimorph_df:
            return []

        um_features_ud = ud_inf.ud2um_features(ud_features, set_defaults=False)
        sub_df = ud_inf.partial_df_match(
            ud_inf.lemma_groups, lemma, um_features_ud,
            prefer_tight_match=True,
        )
        if len(sub_df) == 0:
            return []

        def row_ok(row):
            for feat, val in required.items():
                if feat not in sub_df.columns:
                    continue
                row_val = row[feat]
                is_unmarked = (row_val == "UNDEFINED" or pd.isna(row_val))

                if is_unmarked:
                    # Unmarked row = paradigm default. Compatible only if source
                    # is asking for the default value.
                    default = FEATURE_DEFAULTS.get(feat)
                    if default is None or val == default:
                        continue
                    return False
                else:
                    expected = f"{feat}_{val}"
                    if row_val != expected:
                        return False
            return True

        mask = sub_df.apply(row_ok, axis=1)
        filtered = sub_df[mask]

        if len(filtered) == 0:
            return []
        return list(filtered.form.unique())

    def __call__(self, tree, token_dict, neg_id=None, npi_id=None):
        int_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], int)]
        range_tokens = [copy.deepcopy(t) for t in tree if isinstance(t["id"], tuple)]



        if npi_id is None:
            print("yes this is why we fail")
            return None, None, "no_target_token"

        token_dict_copy = {t["id"]: t for t in int_tokens}
        target_token = token_dict_copy.get(npi_id)
        if target_token is None:
            print("yes this is why we fail")
            return None, None, "no_target_token"

        old_lemma = target_token["lemma"]
        new_lemma = self.lemma_map.get(old_lemma)
        if new_lemma is None:
            return None, None, f"no_mapping_for_lemma:{old_lemma}"

        ud_features = dict(target_token["feats"] or {})

        # Update PronType (and any other feature_updates) to avoid lookup failures
        for feat, new_val in self.feature_updates.items():
            if new_val is None:
                ud_features.pop(feat, None)
            else:
                ud_features[feat] = new_val

        # Strict paradigm lookup: must agree on Case/Number/Person/Gender
        forms = self._strict_lookup(new_lemma, ud_features)

        # Fallback: drop PronType but KEEP strict features. If the paradigm
        # genuinely lacks the right Case/Number combo, we fail rather than
        # silently picking a wrong-number form.
        if not forms and "PronType" in ud_features:
            fallback_features = {k: v for k, v in ud_features.items() if k != "PronType"}
            forms = self._strict_lookup(new_lemma, fallback_features)

        if not forms:
            required_str = {
                feat: ud_features.get(feat)
                for feat in self.strict_features
                if feat in ud_features
            }
            return None, None, f"inflection_failed_strict:{new_lemma}:{required_str}"

        if len(forms) == 1:
            new_form = forms[0]
        else:
            # Multiple strictly-matching forms — pick closest length to original
            new_form = min(forms, key=lambda f: abs(len(f) - len(target_token["form"])))

        # Preserve sentence-initial capitalization from the original form
        original_form = target_token["form"]
        if original_form and original_form[:1].isupper():
            new_form = new_form[:1].upper() + new_form[1:]

        modified_int = []
        for t in int_tokens:
            if t["id"] == npi_id:
                t["form"] = unicodedata.normalize("NFC", new_form)
                t["form"] = t["form"].replace("i\u0307", "i").replace("I\u0307", "İ")
                t["lemma"] = new_lemma
                if t["feats"] is None:
                    t["feats"] = {}
                for feat, new_val in self.feature_updates.items():
                    if new_val is None:
                        t["feats"].pop(feat, None)
                    else:
                        t["feats"][feat] = new_val
            modified_int.append(t)

        modified_tree = modified_int + range_tokens
        return modified_tree, tokens_to_string(modified_tree), "success_lemma_swap"
    
