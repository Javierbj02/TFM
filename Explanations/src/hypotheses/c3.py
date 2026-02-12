# /src/hypotheses/c3.py
import json
from typing import Any, Dict, List, Tuple, Optional, Set
from owlready2 import ThingClass

from llm.client import client

Triple = Tuple[str, str, str]

SYSTEM = (
    "You propose causal hypotheses for observed structural changes. "
    "Return ALWAYS valid JSON. No extra text, no markdown."
)

ROBOT_CONTEXT = """\
Context:
- Domain: indoor hospital logistics.
- Robot: mobile base with wheels, no arms; has a tray for transporting small objects, such as medications, tracked by a camera.
- Mission: follow a supervisor/nurse during medicine delivery assistance.
"""


def _norm(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        t = x.strip()
        return t if t else None
    name = getattr(x, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    try:
        s = str(x).strip()
        return s if s else None
    except Exception:
        return None


def extract_triples_from_runtime(rt: Any) -> List[Triple]:
    """
    Intenta obtener triples ABox como tuplas (s,p,o) con nombres locales (strings).
    Prioridad:
      1) rt.graph iterable de triples string
      2) rt.triples / rt.abox_triples si existiese
      3) fallback vacío (mejor que romper)
    """
    
    g = getattr(rt, "graph", None)
    if g is not None:
        out: List[Triple] = []
        try:
            for (s, p, o) in g:
                s2, p2, o2 = _norm(s), _norm(p), _norm(o)
                if s2 and p2 and o2:
                    out.append((s2, p2, o2))
            return out
        except Exception:
            pass
        
    for attr in ("triples", "abox_triples", "kb_triples"):
        t = getattr(rt, attr, None)
        if t is None:
            continue
        out2: List[Triple] = []
        try:
            for (s, p, o) in t:
                s2, p2, o2 = _norm(s), _norm(p), _norm(o)
                if s2 and p2 and o2:
                    out2.append((s2, p2, o2))
            return out2
        except Exception:
            pass

    onto = getattr(rt, "onto", None) or getattr(rt, "ontology", None)
    if onto is not None:
        out3: List[Triple] = []
        try:
            for s in onto.individuals():
                s_name = _norm(s)
                if not s_name:
                    continue

                for prop in onto.object_properties():
                    p_name = _norm(prop)
                    if not p_name:
                        continue
                    try:
                        vals = prop[s]
                    except Exception:
                        continue
                    if not vals:
                        continue
                    for o in vals:
                        o_name = _norm(o)
                        if s_name and p_name and o_name:
                            out3.append((s_name, p_name, o_name))
        except Exception:
            pass

        if out3:
            out3 = list(dict.fromkeys(out3))
            return out3

    return []




def retrieve_subgraph(
    all_triples: List[Triple],
    seeds: Set[str],
    *,
    hops: int = 2,
    max_triples: int = 80,
) -> List[Triple]:

    if not all_triples or not seeds:
        return []


    idx: Dict[str, List[Triple]] = {}
    for (s, p, o) in all_triples:
        idx.setdefault(s, []).append((s, p, o))
        idx.setdefault(o, []).append((s, p, o))

    frontier = set(seeds)
    visited_nodes = set(seeds)
    selected: List[Triple] = []
    seen_triples: Set[Triple] = set()

    for _ in range(max(1, hops)):
        next_frontier: Set[str] = set()

        for node in sorted(frontier):
            for t in idx.get(node, []):
                if t in seen_triples:
                    continue
                seen_triples.add(t)
                selected.append(t)
                s, _, o = t
                if s not in visited_nodes:
                    next_frontier.add(s)
                if o not in visited_nodes:
                    next_frontier.add(o)

                if len(selected) >= max_triples:
                    break
            if len(selected) >= max_triples:
                break

        visited_nodes |= next_frontier
        frontier = next_frontier
        if not frontier or len(selected) >= max_triples:
            break

    selected = list(dict.fromkeys(selected))
    return selected[:max_triples]



def _first_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, list):
        return str(x[0]) if x else ""
    return str(x)

def extract_eventtype_catalog_from_ontos(ontos: List[Any]) -> List[Dict[str, str]]:
    ontos = [o for o in ontos if o is not None]
    if not ontos:
        return []

    root = None
    for o in ontos:
        try:
            cand = o.search_one(iri="*EventType") or o.search_one(name="EventType")
        except Exception:
            cand = None
        if isinstance(cand, ThingClass):
            root = cand
            break

    out: List[Dict[str, str]] = []
    for o in ontos:
        try:
            classes = list(o.classes())
        except Exception:
            continue

        for cls in classes:
            if not isinstance(cls, ThingClass):
                continue

            if root is not None:
                try:
                    if root not in cls.ancestors():
                        continue
                except Exception:
                    continue
            else:
                # fallback heurístico
                n = (getattr(cls, "name", "") or "").lower()
                if not any(k in n for k in ("event", "action", "task", "process", "activity")):
                    continue

            label = _first_text(getattr(cls, "label", None)).strip()
            comment = _first_text(getattr(cls, "comment", None)).strip()
            out.append({"name": cls.name, "label": label, "comment": comment})

    seen = set()
    uniq: List[Dict[str, str]] = []
    for e in sorted(out, key=lambda d: d["name"]):
        if e["name"] in seen:
            continue
        seen.add(e["name"])
        uniq.append(e)
    return uniq

def extract_eventtype_catalog_from_runtime(rt: Any) -> List[Dict[str, str]]:
    onto_main = getattr(rt, "onto", None)
    extra_ontos = list(getattr(rt, "extra_ontos", []) or [])
    ontos = [onto_main] + extra_ontos
    return extract_eventtype_catalog_from_ontos(ontos)


def format_eventtype_catalog(catalog: List[Dict[str, str]], *, max_items: int = 250) -> str:
    lines: List[str] = []
    for e in catalog[:max_items]:
        desc = (e.get("comment") or e.get("label") or "").strip()
        if desc:
            if len(desc) > 200:
                desc = desc[:200].rstrip() + "..."
            lines.append(f"- {e['name']}: {desc}")
        else:
            lines.append(f"- {e['name']}")
    return "\n".join(lines)



def _invalid_event_classes(cands: List[Dict[str, Any]], allowed: set) -> List[str]:
    bad = []
    for h in cands:
        ec = h.get("event_class")
        if ec not in allowed:
            bad.append(str(ec))
    return bad

def _shadow_missing(cands: List[Dict[str, Any]], shadow: str) -> bool:
    for h in cands:
        parts = h.get("participants", [])
        if shadow not in parts:
            return True
    return False



def build_prompt(
    observed_retract: Triple,
    step_name: str,
    allowed_entities: List[str],
    allowed_event_classes: List[str],
    allowed_obj_props: List[str],
    context_triples: List[Triple],
    tmo_catalog_text: str,
    mlo_catalog_text: str,

) -> str:

    s, p, o = observed_retract

    ents = sorted(set(allowed_entities))[:80]
    evts = list(dict.fromkeys(allowed_event_classes))
    props = sorted(set(allowed_obj_props))[:80]
    ctx = context_triples[:90]

    ctx_block = ""
    if ctx:
        ctx_block = (
            "\nRetrieved context triples (ABox, GraphRAG):\n"
            + "\n".join(f"- ({ts}, {tp}, {to})" for (ts, tp, to) in ctx)
            + "\n"
        )
        
    catalog_block = ""
    if tmo_catalog_text.strip():
        catalog_block += (
            "\nPreferred EventType class catalog (TMO) — prioritize these:\n"
            + tmo_catalog_text
            + "\n"
        )
    if mlo_catalog_text.strip():
        catalog_block += (
            "\nFallback EventType class catalog (MLO) — use only if none of the preferred TMO classes fit:\n"
            + mlo_catalog_text
            + "\n"
        )


    return f"""{ROBOT_CONTEXT}

Observed change (retract) at step '{step_name}':
- retracted triple: ({s}, {p}, {o})
{ctx_block}
{catalog_block}
Allowed entities (ABox individuals from the current scenario; MUST be used verbatim for participants/where and triple objects):
{chr(10).join("- " + e for e in ents)}

Allowed object properties (do NOT invent; use only these in proposed_triples):
{chr(10).join("- " + pr for pr in props)}

Allowed EventType classes (MUST be used verbatim for event_class; copy/paste EXACTLY one of these strings, no prefixes, no colons):
{chr(10).join("- " + c for c in evts)}


Task:
Propose EXACTLY 3 alternative causal hypotheses that could explain the retract.
Use the Retrieved context triples to make the hypotheses consistent with the current state/history.

Return ONLY valid JSON with exactly 3 objects using this schema:
[
  {{
    "title": "short name",
    "event_class": "OneAllowedEventTypeClass",
    "event_id": "EventTypeInstanceId",
    "participants": ["Entity1", "Entity2"],
    "where": "Entity",
    "proposed_triples": [
      ["<event_id>", "<object_property>", "<Entity>"]
    ]
  }}
]

Rules (STRICT):
- Output MUST be valid JSON only.
- event_class MUST be EXACTLY one of the strings in "Allowed EventType classes" (verbatim). 
- Do NOT output individuals in event_class.
- Do NOT choose Event (or other non-EventType classes) unless it appears in Allowed EventType classes (it should not).
- event_class must NOT contain "_H" (those belong to event_id only).
- event_id MUST be one of: "<event_class>_H1", "<event_class>_H2", "<event_class>_H3".
  (event_id is an INDIVIDUAL name that starts with the chosen event_class plus an underscore.)
- COVERAGE CONSTRAINT: At least 2 of the 3 hypotheses MUST use an event_class from the Preferred (TMO) catalog.
- Only use Fallback (MLO) classes if no Preferred (TMO) class fits the hypothesis.
- participants and where MUST be from Allowed entities (verbatim).
- PARTICIPANT CONSTRAINT (PER HYPOTHESIS): For EACH hypothesis, "participants" MUST include "Agent_Shadow".
- proposed_triples:
  - list of [s,p,o] strings
  - s MUST equal event_id
  - p MUST be one of Allowed object properties
  - o MUST be one of Allowed entities
- FOCUS CONSTRAINT (PER HYPOTHESIS):
  proposed_triples MUST include
  (at least one triple whose object (o) is exactly "{s}")
  AND
  (at least one triple whose object (o) is exactly "{o}").
- Avoid generic/abstract explanations unless you explicitly connect them to the retract via proposed_triples that mention "{s}" or "{o}".
- Prefer the MOST SPECIFIC EventType class from the catalog.
- Do NOT choose very generic classes unless there is no more specific option.
"""



def _strip_code_fences(txt: str) -> str:
    t = txt.strip()
    if t.startswith("```"):
        lines = t.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    if t.lower().startswith("json"):
        t = t[4:].strip()
    return t

def _validate_schema(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("LLM output is not a JSON list.")
    if len(data) != 3:
        raise ValueError(f"Expected exactly 3 hypotheses, got {len(data)}.")

    required = {"title", "event_class", "event_id", "participants", "where", "proposed_triples"}
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValueError(f"Item {i} is not an object.")
        missing = required - set(obj.keys())
        if missing:
            raise ValueError(f"Item {i} missing keys: {sorted(missing)}")

        if not isinstance(obj["title"], str) or not obj["title"].strip():
            raise ValueError(f"Item {i} title invalid.")
        if not isinstance(obj["event_class"], str) or not obj["event_class"].strip():
            raise ValueError(f"Item {i} event_class invalid.")
        if not isinstance(obj["event_id"], str) or not obj["event_id"].strip():
            raise ValueError(f"Item {i} event_id invalid.")
        if not isinstance(obj["where"], str) or not obj["where"].strip():
            raise ValueError(f"Item {i} where invalid.")

        parts = obj["participants"]
        if not isinstance(parts, list) or not all(isinstance(x, str) and x.strip() for x in parts):
            raise ValueError(f"Item {i} participants must be list[str] (non-empty strings).")

        triples = obj["proposed_triples"]
        if not isinstance(triples, list) or not all(isinstance(t, list) and len(t) == 3 for t in triples):
            raise ValueError(f"Item {i} proposed_triples must be list of [s,p,o].")

    return data 

def compute_vocab_flags(
    candidates: List[Dict[str, Any]],
    allowed_entities: set,
    allowed_event_classes: set,
    allowed_obj_props: set,
) -> Dict[str, Any]:
    per = []
    for h in candidates:
        evt_class = h["event_class"]
        evt_id = h["event_id"]

        evt_ok = evt_class in allowed_event_classes


        looks_like_instance = evt_class.endswith(("_H1", "_H2", "_H3"))
        evt_ok = evt_ok and (not looks_like_instance)

        id_ok = evt_id in {f"{evt_class}_H1", f"{evt_class}_H2", f"{evt_class}_H3"}

        parts_ok = all(p in allowed_entities for p in h["participants"])
        where_ok = h["where"] in allowed_entities

        triples = h.get("proposed_triples", [])
        triples_prop_ok = all((t[1] in allowed_obj_props) for t in triples)
        triples_obj_ok = all((t[2] in allowed_entities) for t in triples)
        triples_subj_ok = all((t[0] == evt_id) for t in triples)

        per.append({
            "ok_event_class": bool(evt_ok),
            "ok_event_id_pattern": bool(id_ok),
            "ok_entities": bool(parts_ok and where_ok),
            "ok_triple_props": bool(triples_prop_ok),
            "ok_triple_objects": bool(triples_obj_ok),
            "ok_triple_subjects": bool(triples_subj_ok),
            "ok_event_class_not_instance": bool(not looks_like_instance),

        })

    out = {
        "per_hypothesis": per,
        "ok_vocab_strict": all(
            x["ok_event_class"]
            and x["ok_event_class_not_instance"]
            and x["ok_event_id_pattern"]
            and x["ok_entities"]
            and x["ok_triple_props"]
            and x["ok_triple_objects"]
            and x["ok_triple_subjects"]
            for x in per
        ),
    }
    return out

def generate_hypotheses_c3(
    llm: client,
    observed_retract: Triple,
    step_name: str,
    allowed_entities: set,
    allowed_obj_props: List[str],
    runtime: Optional[Any] = None,
    hops: int = 2,
    max_ctx_triples: int = 80,
    temperature: float = 0.3,
    max_tokens: int = 850,
    max_eventtype_items: int = 250,
) -> Dict[str, Any]:
    ctx_triples: List[Triple] = []
    if runtime is not None:
        all_triples = extract_triples_from_runtime(runtime)
        s_seed = _norm(observed_retract[0])
        o_seed = _norm(observed_retract[2])
        seeds = {x for x in (s_seed, o_seed) if x}
        ctx_triples = retrieve_subgraph(all_triples, seeds, hops=hops, max_triples=max_ctx_triples)
        print("[C3] GraphRAG seeds:", s_seed, o_seed)
        print("[C3] ctx_triples_n =", len(ctx_triples))
        print("[C3] ctx_triples_sample =", ctx_triples[:8])


    tmo_catalog: List[Dict[str, str]] = []
    mlo_catalog: List[Dict[str, str]] = []
    tmo_text = ""
    mlo_text = ""

    if runtime is not None:
        onto_main = getattr(runtime, "onto", None)
        extra_ontos = list(getattr(runtime, "extra_ontos", []) or [])

        if extra_ontos:
            tmo_catalog = extract_eventtype_catalog_from_ontos(extra_ontos)
            tmo_text = format_eventtype_catalog(tmo_catalog, max_items=max_eventtype_items)

        if onto_main is not None:
            mlo_catalog = extract_eventtype_catalog_from_ontos([onto_main])
            mlo_text = format_eventtype_catalog(mlo_catalog, max_items=120)

    allowed_event_classes = [e["name"] for e in tmo_catalog] + [e["name"] for e in mlo_catalog]
    allowed_event_classes = list(dict.fromkeys(allowed_event_classes))


    if not allowed_event_classes:
        allowed_event_classes = ["EventType"]
        tmo_text = "- EventType"
        mlo_text = ""

        
    shadow = "Agent_Shadow"
    if shadow not in allowed_entities:
        allowed_entities = set(allowed_entities)
        allowed_entities.add(shadow)


    if runtime is not None:
        onto_main = getattr(runtime, "onto", None)
        extra_ontos = list(getattr(runtime, "extra_ontos", []) or [])
        print("[C3] ontologies loaded:", 
              ("main=" + (getattr(onto_main, "base_iri", "") or "<?>")) if onto_main else "main=None",
              "extra_n=", len(extra_ontos))
        print("[C3] catalog_n_types =", len(allowed_event_classes),
            "tmo_lines =", len(tmo_text.splitlines()),
            "mlo_lines =", len(mlo_text.splitlines()))
        # print("[C3] TMO catalog FULL:")
        # print(tmo_text)

        # print("[C3] MLO catalog FULL:")
        # print(mlo_text)




    prompt = build_prompt(
        observed_retract=observed_retract,
        step_name=step_name,
        allowed_entities=list(allowed_entities),
        allowed_event_classes=allowed_event_classes,
        allowed_obj_props=allowed_obj_props,
        context_triples=ctx_triples,
        tmo_catalog_text=tmo_text,
        mlo_catalog_text=mlo_text,
    )

    res = llm.chat(
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw = res.text
    txt = _strip_code_fences(raw)

    try:
        data = json.loads(txt)
    except Exception as e:
        return {
            "ok_schema": False,
            "schema_error_type": "json_parse",
            "schema_error_msg": str(e),
            "candidates": None,
            "latency_s": res.latency_s,
            "usage": res.usage,
            "raw_text": raw,
            "vocab": None,
            "retrieval": {"hops": hops, "max_ctx_triples": max_ctx_triples, "ctx_triples_n": len(ctx_triples)},
            "catalog": {"n_types": len(allowed_event_classes), "max_items": max_eventtype_items},
        }

    try:
        candidates = _validate_schema(data)
    except Exception as e:
        return {
            "ok_schema": False,
            "schema_error_type": "schema_validation",
            "schema_error_msg": str(e),
            "candidates": None,
            "latency_s": res.latency_s,
            "usage": res.usage,
            "raw_text": raw,
            "vocab": None,
            "retrieval": {"hops": hops, "max_ctx_triples": max_ctx_triples, "ctx_triples_n": len(ctx_triples)},
            "catalog": {"n_types": len(allowed_event_classes), "max_items": max_eventtype_items},
        }

    allowed_evt_set = set(allowed_event_classes)
    
    bad_classes = _invalid_event_classes(candidates, allowed_evt_set)

    require_shadow = "Agent_Shadow" in set(allowed_entities)
    shadow_missing = require_shadow and _shadow_missing(candidates, "Agent_Shadow")
    
    bad_ids = []
    for h in candidates:
        ec = h.get("event_class")
        eid = h.get("event_id")
        if isinstance(ec, str) and isinstance(eid, str):
            if eid not in {f"{ec}_H1", f"{ec}_H2", f"{ec}_H3"}:
                bad_ids.append(eid)

    id_mismatch = bool(bad_ids)
    tmo_set = {e["name"] for e in tmo_catalog}
    tmo_count = sum(1 for h in candidates if h.get("event_class") in tmo_set)
    tmo_missing = bool(tmo_set) and (tmo_count < 2)



    if bad_classes or shadow_missing or id_mismatch or tmo_missing:
        repair_instructions = []
        if bad_classes:
            repair_instructions.append(
                "Some event_class values are not in Allowed event classes: "
                + ", ".join(bad_classes)
                + ". Replace each invalid event_class with the closest EXACT string from Allowed event classes."
            )
        if shadow_missing:
            repair_instructions.append(
                'For EACH hypothesis, ensure "participants" includes "Agent_Shadow" (verbatim) in addition to any others.'
            )
        if id_mismatch:
            repair_instructions.append(
                'For EACH hypothesis, set "event_id" to exactly one of: "<event_class>_H1", "<event_class>_H2", "<event_class>_H3".'
            )
        if tmo_missing:
            repair_instructions.append(
                "COVERAGE FIX: At least 2 hypotheses must use an event_class from the Preferred (TMO) catalog. "
                'Change event_class (and event_id accordingly) to satisfy this.'
            )

        repair_prompt = (
            "Your JSON is valid but violates constraints.\n"
            + "\n".join(repair_instructions)
            + "\nReturn ONLY the corrected JSON. Do not change any other fields unless required by these fixes."
        )

        res2 = llm.chat(
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": txt},
                {"role": "user", "content": repair_prompt},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        raw2 = res2.text
        txt2 = _strip_code_fences(raw2)
        data2 = json.loads(txt2)
        candidates2 = _validate_schema(data2)

        raw, txt, candidates = raw2, txt2, candidates2
        res = res2 


    vocab = compute_vocab_flags(
        candidates,
        allowed_entities=set(allowed_entities),
        allowed_event_classes=set(allowed_event_classes),
        allowed_obj_props=set(allowed_obj_props),
    )

    return {
        "ok_schema": True,
        "schema_error_type": None,
        "schema_error_msg": None,
        "candidates": candidates,
        "latency_s": res.latency_s,
        "usage": res.usage,
        "raw_text": raw,
        "vocab": vocab,
        "retrieval": {"hops": hops, "max_ctx_triples": max_ctx_triples, "ctx_triples_n": len(ctx_triples)},
        "catalog": {"n_types": len(allowed_event_classes), "max_items": max_eventtype_items},
    }
