# /src/hypotheses/c2.py
import json
from typing import Any, Dict, List, Tuple, Optional, Set

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

# ---------- GraphRAG retrieval (symbolic) ----------

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

# ---------- Prompt ----------

def build_prompt(
    observed_retract: Triple,
    step_name: str,
    allowed_entities: List[str],
    allowed_event_classes: List[str],
    allowed_obj_props: List[str],
    context_triples: List[Triple],
) -> str:
    s, p, o = observed_retract

    ents = sorted(set(allowed_entities))[:80]
    evts = sorted(set(allowed_event_classes))[:120]
    props = sorted(set(allowed_obj_props))[:80]
    ctx = context_triples[:90]

    ctx_block = ""
    if ctx:
        ctx_block = (
            "\nRetrieved context triples (ABox, GraphRAG):\n"
            + "\n".join(f"- ({ts}, {tp}, {to})" for (ts, tp, to) in ctx)
            + "\n"
        )

    return f"""{ROBOT_CONTEXT}

Observed change (retract) at step '{step_name}':
- retracted triple: ({s}, {p}, {o})
{ctx_block}
Allowed entities (ABox individuals from the current scenario; MUST be used verbatim for participants/where and triple objects):
{chr(10).join("- " + e for e in ents)}

Allowed event classes (MUST choose one of these verbatim):
{chr(10).join("- " + e for e in evts)}

Allowed object properties (do NOT invent; use only these in proposed_triples):
{chr(10).join("- " + pr for pr in props)}

Task:
Propose EXACTLY 3 alternative causal hypotheses that could explain the retract.
Use the Retrieved context triples to make the hypotheses consistent with the current state/history.

Return ONLY valid JSON with exactly 3 objects using this schema:
[
  {{
    "title": "short name",
    "event_class": "OneAllowedEventClass",
    "event_id": "EventIndividualName",
    "participants": ["Entity1", "Entity2"],
    "where": "Entity",
    "proposed_triples": [
      ["<event_id>", "<object_property>", "<Entity>"]
    ]
  }}
]

Rules (STRICT):
- Output MUST be valid JSON only.
- event_class MUST be one of Allowed event classes.
- event_id MUST be one of: "<event_class>_H1", "<event_class>_H2", "<event_class>_H3".
- participants and where MUST be from Allowed entities (verbatim).
- proposed_triples:
  - list of [s,p,o] strings
  - s MUST equal event_id
  - p MUST be one of Allowed object properties
  - o MUST be one of Allowed entities
- FOCUS CONSTRAINT (PER HYPOTHESIS): For EACH hypothesis object, its proposed_triples MUST contain at least one triple whose object (o) is exactly "{s}" OR exactly "{o}". (Do NOT satisfy this by referencing an intermediate episode/id; it must be the exact entity string.)
- Avoid generic/abstract explanations (e.g., "plan failure", "collaboration issue") unless you explicitly connect them to the retract via proposed_triples that mention "{s}" or "{o}".
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
        "ok_vocab_strict": all(
            x["ok_event_class"]
            and x["ok_event_id_pattern"]
            and x["ok_entities"]
            and x["ok_triple_props"]
            and x["ok_triple_objects"]
            and x["ok_triple_subjects"]
            for x in per
        ),
    }
    return out

def generate_hypotheses_c2(
    llm: client,
    observed_retract: Triple,
    step_name: str,
    allowed_entities: set,
    allowed_event_classes: List[str],
    allowed_obj_props: List[str],
    runtime: Optional[Any] = None,
    hops: int = 2,
    max_ctx_triples: int = 80,
    temperature: float = 0.3,
    max_tokens: int = 850,
) -> Dict[str, Any]:
    
    ctx_triples: List[Triple] = []
    if runtime is not None:
        all_triples = extract_triples_from_runtime(runtime)
        s_seed = _norm(observed_retract[0])
        o_seed = _norm(observed_retract[2])
        

        seeds = {x for x in (s_seed, o_seed) if x}
        ctx_triples = retrieve_subgraph(all_triples, seeds, hops=hops, max_triples=max_ctx_triples)


    
    prompt = build_prompt(
        observed_retract=observed_retract,
        step_name=step_name,
        allowed_entities=list(allowed_entities),
        allowed_event_classes=allowed_event_classes,
        allowed_obj_props=allowed_obj_props,
        context_triples=ctx_triples,
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
        }

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
    }
