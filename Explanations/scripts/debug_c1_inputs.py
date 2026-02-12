# scripts/debug_c1_inputs.py
import os
from scenarios.medicine_lost import cfg_unexpected
from utils.known_entities import build_known_entities_from_cfg

from hypotheses.c1 import build_prompt, extract_allowed_event_types, extract_allowed_object_properties


def main():
    os.makedirs("results", exist_ok=True)

    ents = sorted(build_known_entities_from_cfg(cfg_unexpected))
    evts = extract_allowed_event_types(cfg_unexpected.ontology_path, roots=["SOMA.Event"])
    props = extract_allowed_object_properties(cfg_unexpected.ontology_path)

    print("\n=== C1 DEBUG INPUTS ===")
    print(f"Entities: {len(ents)}")
    print(f"Event classes: {len(evts)}")
    print(f"Object properties: {len(props)}")

    print("\n--- Entities (sample) ---")
    print("\n".join(ents[:25]))

    print("\n--- Event classes (sample) ---")
    print("\n".join(evts[:25]))

    print("\n--- Object properties (sample) ---")
    print("\n".join(props[:25]))

    observed_retract = ("PhysicalObject_Medicine1", "DUL.hasLocation", "PhysicalObject_ShadowTray")

    prompt = build_prompt(
        observed_retract=observed_retract,
        step_name="Unexpected_event",
        allowed_entities=ents,
        allowed_event_types=evts,
        allowed_obj_props=props,
    )

    out_path = "results/c1/c1_debug_prompt.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print("\nSaved prompt to:", out_path)


if __name__ == "__main__":
    main()
