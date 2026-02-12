# /scripts/smoke_test_c0.py
from experiments.runner import run_c0_batch
from scenarios.medicine_lost import cfg_unexpected


if __name__ == "__main__":
    out_path = run_c0_batch(
        cfg=cfg_unexpected,
        out_dir="results",
        n_runs=2,
        temperature=0.0,
        max_tokens=200,
        sleep_s=0.0,
    )
    print("Saved to:", out_path)
