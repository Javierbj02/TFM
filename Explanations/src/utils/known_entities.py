# /src/utils/known_entities.py

from typing import Set
from validator.runtime import ExperimentConfig

def build_known_entities_from_cfg(cfg: ExperimentConfig) -> Set[str]:
    ents: Set[str] = set()

    for step in cfg.steps:
        for inst_name, _cls in (step.types or []):
            if inst_name:
                ents.add(inst_name)

        for s, _p, o in (step.asserts or []):
            if s: ents.add(s)
            if o: ents.add(o)

        for s, _p, o in (step.retracts or []):
            if s: ents.add(s)
            if o: ents.add(o)

        for s, _p, old_o, new_o in (step.updates or []):
            if s: ents.add(s)
            if old_o: ents.add(old_o)
            if new_o: ents.add(new_o)

        for n in (step.deletes or []):
            if n:
                ents.add(n)

    return ents
