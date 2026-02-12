# /src/experiments/runner.py
import json
import os
import time
from datetime import datetime
from typing import Any, Dict

from llm.client import client
from hypotheses.c0 import generate_hypotheses_c0
from validator.runtime import ExperimentConfig, run_experiment

from utils.tbox_vocab import extract_tbox_vocab
from hypotheses.c1 import generate_hypotheses_c1

from hypotheses.c2 import generate_hypotheses_c2

from hypotheses.c3 import generate_hypotheses_c3



def extract_known_entities_from_runtime(rt: Any) -> set:
    names = set()

    onto = getattr(rt, "onto", None) or getattr(rt, "ontology", None)
    if onto is not None:
        try:
            for ind in onto.individuals():
                if getattr(ind, "name", None):
                    names.add(ind.name)
        except Exception:
            pass

    graph = getattr(rt, "graph", None)
    if graph is not None:
        try:
            for (s, p, o) in graph:
                if isinstance(s, str): names.add(s)
                if isinstance(o, str): names.add(o)
        except Exception:
            pass

    return names



def run_c0_batch(
    cfg: ExperimentConfig,
    out_dir: str,
    n_runs: int,
    temperature: float = 0.3,
    max_tokens: int = 600,
    sleep_s: float = 0.0,
) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_id = getattr(cfg, "scenario_id", None) or "medicine_lost"
    base_dir = os.path.join(out_dir, "c0", scenario_id)
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{ts}.jsonl")

    llm = client()
    meta_path = os.path.join(base_dir, f"{ts}_meta.json")
    meta = {
        "scenario_id": scenario_id,
        "n_runs": n_runs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "model": getattr(llm, "model", None),
        "base_url": getattr(llm, "base_url", None),
        "started_at": datetime.now().isoformat(),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    def append(record: Dict[str, Any]) -> None:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    for run_id in range(1, n_runs + 1):
        wrote_any = False

        def on_unexplained(payload: Dict[str, Any]) -> None:
            nonlocal wrote_any
            step = payload["step"]
            step_index = payload["step_index"]
            errors = payload["errors"]
            if not errors:
                return

            for r in getattr(step, "retracts", []) or []:
                record: Dict[str, Any] = {
                    "run_id": run_id,
                    "config": "C0",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": step_index,
                    "failed_step_name": step.name,
                    "errors": errors,
                    "observed_retract": list(r),
                    "grounding_rule": {"min_part_rate": 0.5, "min_where_rate": 0.0},
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                res = generate_hypotheses_c0(
                    llm=llm,
                    observed_retract=r,
                    step_name=step.name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                record.update(res)
                append(record)
                wrote_any = True

        run_experiment(cfg, on_unexplained=on_unexplained)

        print(f"[C0] run {run_id}/{n_runs} finished")
        if not wrote_any:
            append(
                {
                    "run_id": run_id,
                    "config": "C0",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": None,
                    "failed_step_name": None,
                    "errors": [],
                    "observed_retract": None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "ok_schema": False,
                    "schema_error_type": "no_unexplained_trigger",
                    "schema_error_msg": "No unexplained retracts were detected.",
                    "candidates": None,
                    "vocab": None,
                    "latency_s": None,
                    "usage": {},
                    "raw_text": "",
                }
            )
        if sleep_s:
            time.sleep(sleep_s)

    return out_path



def run_c1_batch(
    cfg: ExperimentConfig,
    out_dir: str,
    n_runs: int,
    temperature: float = 0.3,
    max_tokens: int = 700,
    sleep_s: float = 0.0,
) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_id = getattr(cfg, "scenario_id", None) or "medicine_lost"
    base_dir = os.path.join(out_dir, "c1", scenario_id)
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{ts}.jsonl")

    llm = client()

    vocab = extract_tbox_vocab(cfg.ontology_path)
    allowed_event_types = vocab.event_types
    allowed_obj_props = vocab.object_properties

    meta_path = os.path.join(base_dir, f"{ts}_meta.json")
    meta = {
        "scenario_id": scenario_id,
        "n_runs": n_runs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "model": getattr(llm, "model", None),
        "base_url": getattr(llm, "base_url", None),
        "started_at": datetime.now().isoformat(),
        "tbox_vocab": {
            "n_event_types": len(allowed_event_types),
            "n_object_properties": len(allowed_obj_props),
            "ontology_path": getattr(cfg, "ontology_path", None),
        },
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    def append(record: Dict[str, Any]) -> None:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


    for run_id in range(1, n_runs + 1):
        wrote_any = False

        def on_unexplained(payload: Dict[str, Any]) -> None:
            nonlocal wrote_any

            step = payload["step"]
            step_index = payload["step_index"]
            errors = payload["errors"]

            payload_keys = sorted(list(payload.keys()))
            rt = payload.get("runtime", None) or payload.get("rt", None)
            known_entities = extract_known_entities_from_runtime(rt) if rt is not None else set()
            
            print("rt is None?", rt is None, "type:", type(rt))
            print("payload keys:", list(payload.keys()))

            for r in getattr(step, "retracts", []) or []:
                record: Dict[str, Any] = {
                    "run_id": run_id,
                    "config": "C1",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": step_index,
                    "failed_step_name": step.name,
                    "errors": errors,
                    "observed_retract": list(r),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "debug_payload_keys": payload_keys,
                    "debug_known_entities_n": len(known_entities),

                }

                res = generate_hypotheses_c1(
                    llm=llm,
                    observed_retract=r,
                    step_name=step.name,
                    allowed_entities=known_entities,
                    allowed_event_types=allowed_event_types,
                    allowed_obj_props=allowed_obj_props,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                record.update(res)
                append(record)
                wrote_any = True

        run_experiment(cfg, on_unexplained=on_unexplained)
        print(f"[C1] run {run_id}/{n_runs} finished")

        if not wrote_any:
            append(
                {
                    "run_id": run_id,
                    "config": "C1",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": None,
                    "failed_step_name": None,
                    "errors": [],
                    "observed_retract": None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "ok_schema": False,
                    "schema_error_type": "no_unexplained_trigger",
                    "schema_error_msg": "No unexplained retracts were detected.",
                    "candidates": None,
                    "vocab": None,
                    "latency_s": None,
                    "usage": {},
                    "raw_text": "",
                }
            )
            
            
        if sleep_s:
            time.sleep(sleep_s)

    return out_path



def run_c2_batch(
    cfg: ExperimentConfig,
    out_dir: str,
    n_runs: int,
    temperature: float = 0.3,
    max_tokens: int = 850,
    hops: int = 2,
    max_ctx_triples: int = 80,
    sleep_s: float = 0.05,
) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_id = getattr(cfg, "scenario_id", None) or "medicine_lost"
    base_dir = os.path.join(out_dir, "c2", scenario_id)
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{ts}.jsonl")

    llm = client()

    vocab = extract_tbox_vocab(cfg.ontology_path)
    allowed_event_classes = vocab.event_types
    allowed_obj_props = vocab.object_properties

    meta_path = os.path.join(base_dir, f"{ts}_meta.json")
    meta = {
        "scenario_id": scenario_id,
        "n_runs": n_runs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "hops": hops,
        "max_ctx_triples": max_ctx_triples,
        "model": getattr(llm, "model", None),
        "base_url": getattr(llm, "base_url", None),
        "started_at": datetime.now().isoformat(),
        "config": "C2",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    def append(record: Dict[str, Any]) -> None:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    for run_id in range(1, n_runs + 1):
        wrote_any = False

        def on_unexplained(payload: Dict[str, Any]) -> None:
            nonlocal wrote_any
            step = payload["step"]
            step_index = payload["step_index"]
            errors = payload["errors"]

            rt = payload.get("runtime", None) or payload.get("rt", None)
            known_entities = extract_known_entities_from_runtime(rt) if rt is not None else set()

            for r in getattr(step, "retracts", []) or []:
                record: Dict[str, Any] = {
                    "run_id": run_id,
                    "config": "C2",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": step_index,
                    "failed_step_name": step.name,
                    "errors": errors,
                    "observed_retract": list(r),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "hops": hops,
                    "max_ctx_triples": max_ctx_triples,
                }

                res = generate_hypotheses_c2(
                    llm=llm,
                    observed_retract=r,
                    step_name=step.name,
                    allowed_entities=known_entities,
                    allowed_event_classes=allowed_event_classes,
                    allowed_obj_props=allowed_obj_props,
                    runtime=rt,
                    hops=hops,
                    max_ctx_triples=max_ctx_triples,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                record.update(res)
                append(record)
                wrote_any = True

        run_experiment(cfg, on_unexplained=on_unexplained)
        print(f"[C2] run {run_id}/{n_runs} finished")

        if not wrote_any:
            append(
                {
                    "run_id": run_id,
                    "config": "C2",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": None,
                    "failed_step_name": None,
                    "errors": [],
                    "observed_retract": None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "ok_schema": False,
                    "schema_error_type": "no_unexplained_trigger",
                    "schema_error_msg": "No unexplained retracts were detected.",
                    "candidates": None,
                    "vocab": None,
                    "latency_s": None,
                    "usage": {},
                    "raw_text": "",
                    "retrieval": {"hops": hops, "max_ctx_triples": max_ctx_triples, "ctx_triples_n": 0},
                }
            )

        if sleep_s:
            time.sleep(sleep_s)

    return out_path


def run_c3_batch(
    cfg: ExperimentConfig,
    out_dir: str,
    n_runs: int,
    temperature: float = 0.3,
    max_tokens: int = 850,
    hops: int = 2,
    max_ctx_triples: int = 80,
    max_eventtype_items: int = 250,
    sleep_s: float = 0.05,
) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_id = getattr(cfg, "scenario_id", None) or "medicine_lost"
    base_dir = os.path.join(out_dir, "c3", scenario_id)
    os.makedirs(base_dir, exist_ok=True)
    out_path = os.path.join(base_dir, f"{ts}.jsonl")

    llm = client()

    vocab = extract_tbox_vocab(cfg.ontology_path)
    allowed_obj_props = vocab.object_properties

    meta_path = os.path.join(base_dir, f"{ts}_meta.json")
    meta = {
        "scenario_id": scenario_id,
        "n_runs": n_runs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "hops": hops,
        "max_ctx_triples": max_ctx_triples,
        "max_eventtype_items": max_eventtype_items,
        "model": getattr(llm, "model", None),
        "base_url": getattr(llm, "base_url", None),
        "started_at": datetime.now().isoformat(),
        "config": "C3",
        "extra_ontology_paths": getattr(cfg, "extra_ontology_paths", []),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    def append(record: Dict[str, Any]) -> None:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    for run_id in range(1, n_runs + 1):
        wrote_any = False

        def on_unexplained(payload: Dict[str, Any]) -> None:
            nonlocal wrote_any
            step = payload["step"]
            step_index = payload["step_index"]
            errors = payload["errors"]

            rt = payload.get("runtime", None) or payload.get("rt", None)
            known_entities = extract_known_entities_from_runtime(rt) if rt is not None else set()

            for r in getattr(step, "retracts", []) or []:
                record: Dict[str, Any] = {
                    "run_id": run_id,
                    "config": "C3",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": step_index,
                    "failed_step_name": step.name,
                    "errors": errors,
                    "observed_retract": list(r),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "hops": hops,
                    "max_ctx_triples": max_ctx_triples,
                    "max_eventtype_items": max_eventtype_items,
                    "extra_ontology_paths": getattr(cfg, "extra_ontology_paths", []),
                }

                res = generate_hypotheses_c3(
                    llm=llm,
                    observed_retract=r,
                    step_name=step.name,
                    allowed_entities=known_entities,
                    allowed_obj_props=allowed_obj_props,
                    runtime=rt,
                    hops=hops,
                    max_ctx_triples=max_ctx_triples,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    max_eventtype_items=max_eventtype_items,
                )
                record.update(res)
                append(record)
                wrote_any = True

        run_experiment(cfg, on_unexplained=on_unexplained)
        print(f"[C3] run {run_id}/{n_runs} finished")

        if not wrote_any:
            append(
                {
                    "run_id": run_id,
                    "config": "C3",
                    "timestamp": datetime.now().isoformat(),
                    "failed_step_index": None,
                    "failed_step_name": None,
                    "errors": [],
                    "observed_retract": None,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "ok_schema": False,
                    "schema_error_type": "no_unexplained_trigger",
                    "schema_error_msg": "No unexplained retracts were detected.",
                    "candidates": None,
                    "vocab": None,
                    "latency_s": None,
                    "usage": {},
                    "raw_text": "",
                    "retrieval": {"hops": hops, "max_ctx_triples": max_ctx_triples, "ctx_triples_n": 0},
                    "catalog": {"n_types": 0, "max_items": max_eventtype_items},
                }
            )

        if sleep_s:
            time.sleep(sleep_s)

    return out_path
