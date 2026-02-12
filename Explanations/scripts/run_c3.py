from experiments.runner import run_c3_batch
from scenarios.medicine_lost import cfg_unexpected
import copy

if __name__ == "__main__":
    cfg = copy.deepcopy(cfg_unexpected)
    cfg.enable_reasoner = False
    cfg.extra_ontology_paths = ["data/ontologies/TMO.owl"]

    out_path = run_c3_batch(
        cfg=cfg,
        out_dir="results",
        n_runs=20,
        temperature=0.3,
        max_tokens=850,
        hops=2,
        max_ctx_triples=80,
        max_eventtype_items=250,
    )
    print("Saved to:", out_path)
