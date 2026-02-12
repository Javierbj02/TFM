# /scripts/run_c1.py
from experiments.runner import run_c1_batch
from scenarios.medicine_lost import cfg_unexpected

if __name__ == "__main__":
    out_path = run_c1_batch(
        cfg=cfg_unexpected,
        out_dir="results",
        n_runs=20,
        temperature=0.3,
        max_tokens=700,
    )
    print("Saved to:", out_path)