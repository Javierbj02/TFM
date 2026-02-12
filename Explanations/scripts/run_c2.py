# /scripts/run_c2.py
from experiments.runner import run_c2_batch
from scenarios.medicine_lost import cfg_unexpected

if __name__ == "__main__":
    out_path = run_c2_batch(
        cfg=cfg_unexpected,
        out_dir="results",
        n_runs=20,
        temperature=0.3,
        max_tokens=850,
        hops=2,
        max_ctx_triples=80,
    )
    print("Saved to:", out_path)
