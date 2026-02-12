# /src/utils/tbox_vocab.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set, Optional
import types
from owlready2 import get_ontology, ThingClass

@dataclass
class TBoxVocab:
    event_types: List[str]
    object_properties: List[str]
    data_properties: List[str]

def _load_onto(path: str):
    if not path.startswith("file://"):
        path = "file://" + path
    return get_ontology(path).load()

def _get_class_by_local(onto, local: str) -> Optional[ThingClass]:
    for c in onto.classes():
        if c.name == local:
            return c
    return None

def extract_tbox_vocab(
    ontology_path: str,
    event_root_locals: Optional[List[str]] = None,
    max_event_types: int = 120,
) -> TBoxVocab:
    onto = _load_onto(ontology_path)

    event_root_locals = event_root_locals or ["Event", "Action", "Process", "Occurrence"]

    roots: List[ThingClass] = []
    for rlocal in event_root_locals:
        cls = _get_class_by_local(onto, rlocal)
        if cls is not None:
            roots.append(cls)

    event_set: Set[str] = set()
    if roots:
        for c in onto.classes():
            try:
                if any(root in c.ancestors() for root in roots):
                    event_set.add(c.name)
            except Exception:
                continue
    else:
        event_set = {c.name for c in onto.classes()}

    obj_props = sorted({p.name for p in onto.object_properties()})
    data_props = sorted({p.name for p in onto.data_properties()})

    event_types = sorted(event_set)[:max_event_types]

    return TBoxVocab(
        event_types=event_types,
        object_properties=obj_props,
        data_properties=data_props,
    )