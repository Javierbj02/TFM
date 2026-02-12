# /src/hypotheses/c1.py
import json
from typing import Any, Dict, List, Tuple, Optional
from owlready2 import get_ontology

from llm.client import client

Triple = Tuple[str, str, str]

SYSTEM = (
    "You propose causal hypotheses for observed structural changes. "
    "Return ALWAYS valid JSON. No extra text, no markdown."
)

ROBOT_CONTEXT = """\
Context:
- Domain: indoor hospital logistics.
- Robot: mobile base with wheels, no arms; has a tray to carry small items like medicine.
- Mission: follow a supervisor/nurse during medicine delivery assistance.
"""

def build_prompt(
    observed_retract: Triple,
    step_name: str,
    allowed_entities: List[str],
    allowed_event_types: List[str],
    allowed_obj_props: List[str],
) -> str:
    s, p, o = observed_retract

    ents = sorted(set(allowed_entities))[:80]
    evts = sorted(set(allowed_event_types))[:120]
    props = sorted(set(allowed_obj_props))[:80]

    return f"""{ROBOT_CONTEXT}

Observed change (retract) at step '{step_name}':
- retracted triple: ({s}, {p}, {o})

Allowed entities (ABox individuals from the current scenario; MUST be used verbatim for participants and where):
{chr(10).join("- " + e for e in ents)}

Allowed event classes (MUST choose one of these verbatim):
{chr(10).join("- " + e for e in evts)}

Allowed object properties (do NOT invent; use only these in proposed_triples):
{chr(10).join("- " + pr for pr in props)}

Task:
Propose EXACTLY 3 alternative causal hypotheses that could explain the retract.

Return ONLY valid JSON with exactly 3 objects using this schema:
[
  {{
    "title": "short name",
    "event_class": "OneAllowedEventClass",
    "event_id": "EventIndividualName",
    "participants": ["Entity1", "Entity2"], //1..N
    "where": "Entity",
    "proposed_triples": [
      ["<event_id>", "<object_property>", "<Entity>"],
      ["<event_id>", "<object_property>", "<Entity>"]
    ]
  }}
]

Rules (STRICT):
- Output MUST be valid JSON only.
- event_class MUST be one of Allowed event classes.
- event_id MUST follow the pattern "<event_class>_H1" / "<event_class>_H2" / "<event_class>_H3".
  Examples: "Action_H1", "Collaboration_H2".
- participants MUST be a non-empty list (1..N) of Allowed entities (verbatim).
- where MUST be from Allowed entities (verbatim).
- proposed_triples:
  - MUST be a list of triples [s,p,o] (strings).
  - Subject s MUST equal event_id (use the same exact string).
  - p MUST be one of Allowed object properties.
  - o MUST be one of Allowed entities.
- Keep proposed_triples minimal (2-4 triples). Prefer hasParticipant and hasLocation when applicable.
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
        if not isinstance(parts, list) or len(parts) < 1 or not all(isinstance(x, str) for x in parts):
            raise ValueError(f"Item {i} participants must be list[str] of len >= 1.")

        triples = obj["proposed_triples"]
        if not isinstance(triples, list) or not all(isinstance(t, list) and len(t) == 3 for t in triples):
            raise ValueError(f"Item {i} proposed_triples must be list of [s,p,o].")

        if not (2 <= len(triples) <= 6):
            raise ValueError(f"Item {i} proposed_triples must have length 2..6.")
        
        ev_id = obj["event_id"]
        for t in triples:
            if not isinstance(t[0], str) or not isinstance(t[1], str) or not isinstance(t[2], str):
                raise ValueError(f"Item {i} proposed_triples contains non-string values.")
            if t[0].strip() == "":
                raise ValueError(f"Item {i} proposed_triples has empty subject.")

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
        })

    out = {
        "per_hypothesis": per,
        "ok_all_event_class": all(x["ok_event_class"] for x in per),
        "ok_all_event_id_pattern": all(x["ok_event_id_pattern"] for x in per),
        "ok_all_entities": all(x["ok_entities"] for x in per),
        "ok_all_triple_props": all(x["ok_triple_props"] for x in per),
        "ok_all_triple_objects": all(x["ok_triple_objects"] for x in per),
        "ok_all_triple_subjects": all(x["ok_triple_subjects"] for x in per),
    }

    out["ok_vocab_strict"] = (
        out["ok_all_event_class"]
        and out["ok_all_event_id_pattern"]
        and out["ok_all_entities"]
        and out["ok_all_triple_props"]
        and out["ok_all_triple_objects"]
        and out["ok_all_triple_subjects"]
    )
    return out

def generate_hypotheses_c1(
    llm: client,
    observed_retract: Triple,
    step_name: str,
    allowed_entities: set,
    allowed_event_types: List[str],
    allowed_obj_props: List[str],
    temperature: float = 0.3,
    max_tokens: int = 750,
) -> Dict[str, Any]:
    prompt = build_prompt(
        observed_retract,
        step_name,
        allowed_entities=list(allowed_entities),
        allowed_event_types=allowed_event_types,
        allowed_obj_props=allowed_obj_props,
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
        }

    vocab = compute_vocab_flags(
        candidates,
        allowed_entities=set(allowed_entities),
        allowed_event_classes=set(allowed_event_types),
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
    }

def extract_allowed_event_types(ontology_path: str, roots: Optional[List[str]] = None) -> List[str]:
    roots = roots or ["SOMA.Event"]
    onto = get_ontology("file://" + ontology_path if not ontology_path.startswith("file://") else ontology_path).load()

    cls_by_name = {c.name: c for c in onto.classes()}

    root_classes = []
    for qn in roots:
        root_name = qn.split(".")[-1]
        rc = cls_by_name.get(root_name)
        if rc is not None:
            root_classes.append(rc)

    if not root_classes:
        return []

    allowed = []
    for c in onto.classes():
        try:
            if any(r in c.ancestors() for r in root_classes):
                allowed.append(c.name)
        except Exception:
            continue

    return sorted(set(allowed))

def extract_allowed_object_properties(ontology_path: str) -> List[str]:
    onto = get_ontology("file://" + ontology_path if not ontology_path.startswith("file://") else ontology_path).load()
    props = [p.name for p in onto.object_properties()]
    return sorted(set(props))
