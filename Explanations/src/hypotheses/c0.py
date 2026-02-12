# /src/hypotheses/c0.py
import json
from typing import Any, Dict, List, Tuple

from llm.client import client

Triple = Tuple[str, str, str]

SYSTEM = (
    "You propose causal hypotheses for observed structural changes. "
    "Return ALWAYS a valid JSON list. No extra text, no markdown."
)

ROBOT_CONTEXT = """\
Context:
- Domain: indoor hospital logistics.
- Robot: mobile base with wheels, no arms; has a tray to carry small items like medicine.
- Mission: follow a supervisor/nurse during medicine delivery assistance.
"""

def build_prompt(observed_retract: Triple, step_name: str) -> str:
    s, p, o = observed_retract
    return f"""{ROBOT_CONTEXT}

Observed change (retract) at step '{step_name}':
- retracted triple: ({s}, {p}, {o})

Task:
Propose EXACTLY 3 alternative causal hypotheses (cause events) that could explain this retract.

Return ONLY a JSON list with exactly 3 objects using this schema:
[
  {{
    "title": "short name of the hypothesis",
    "event_type": "EventTypeName_1",
    "participants": ["Entity1", "Entity2"],
    "where": "LocationOrCarrierEntity"
  }}
]

Rules:
- Output MUST be valid JSON only.
- EXACTLY 3 objects in the list.
- participants: list of 1 or 2 strings.
- where: a single string.
- event_type: a plausible event type name (NOT an OWL property).
"""

def _strip_code_fences(txt: str) -> str:
    t = txt.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    if t.lower().startswith("json"):
        t = t[4:].strip()
    return t

def _validate_candidates(data: Any) -> List[Dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("LLM output is not a JSON list.")
    if len(data) != 3:
        raise ValueError(f"Expected exactly 3 hypotheses, got {len(data)}.")

    required = {"title", "event_type", "participants", "where"}

    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValueError(f"Item {i} is not an object.")

        missing = required - set(obj.keys())
        if missing:
            raise ValueError(f"Item {i} missing keys: {sorted(missing)}")

        if not isinstance(obj["title"], str) or not obj["title"].strip():
            raise ValueError(f"Item {i} title is empty.")
        if not isinstance(obj["event_type"], str) or not obj["event_type"].strip():
            raise ValueError(f"Item {i} event_type is empty.")
        if not isinstance(obj["participants"], list) or not all(isinstance(x, str) for x in obj["participants"]):
            raise ValueError(f"Item {i} participants must be a list of strings.")
        if not (1 <= len(obj["participants"]) <= 2):
            raise ValueError(f"Item {i} participants must have length 1 or 2.")
        if not isinstance(obj["where"], str) or not obj["where"].strip():
            raise ValueError(f"Item {i} where is empty or not a string.")

    return data

def try_parse_candidates(raw_text: str) -> Dict[str, Any]:
    txt = _strip_code_fences(raw_text)

    try:
        data = json.loads(txt)
        ok_json = True
        json_error = None
    except Exception as e:
        return {
            "ok_json": False,
            "ok_schema": False,
            "error_type": "json_parse",
            "error_msg": str(e),
            "candidates": None,
        }

    try:
        candidates = _validate_candidates(data)
        return {
            "ok_json": True,
            "ok_schema": True,
            "error_type": None,
            "error_msg": None,
            "candidates": candidates,
        }
    except Exception as e:
        return {
            "ok_json": True,
            "ok_schema": False,
            "error_type": "schema_validation",
            "error_msg": str(e),
            "candidates": None,
        }

def _content_checks(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    event_types = [str(c.get("event_type", "")).strip() for c in candidates]
    bad_like_property = sum(1 for et in event_types if ("." in et) or ("has" in et) or ("DUL" in et))
    return {
        "distinct_event_types": len(set(event_types)),
        "event_type_bad_like_property_count": bad_like_property,
    }

def generate_hypotheses_c0(
    llm: client,
    observed_retract: Triple,
    step_name: str,
    temperature: float = 0.3,
    max_tokens: int = 600,
) -> Dict[str, Any]:
    prompt = build_prompt(observed_retract, step_name)

    res = llm.chat(
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    raw = res.text
    parsed = try_parse_candidates(raw)

    out = {
        "ok_json": parsed["ok_json"],
        "ok_schema": parsed["ok_schema"],
        "schema_error_type": parsed["error_type"],
        "schema_error_msg": parsed["error_msg"],
        "candidates": parsed["candidates"],
        "latency_s": res.latency_s,
        "usage": res.usage,
        "raw_text": raw,
    }

    if parsed["ok_schema"] and parsed["candidates"] is not None:
        out["content_checks"] = _content_checks(parsed["candidates"])
    else:
        out["content_checks"] = None

    return out