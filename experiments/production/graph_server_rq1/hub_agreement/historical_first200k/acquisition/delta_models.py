from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

CURRENT_CSV =  "all_huggingface_models_2026Aug28.csv"
BASELINE_CSV =  "all_huggingface_models_CIKM.csv"
OUTPUT_CSV =  "delta_model-2026-Aug28.csv"

CURRENT_COLUMN = "modelId"
BASELINE_COLUMN = "model_id"

current_df = pd.read_csv(CURRENT_CSV, dtype=str)
baseline_df = pd.read_csv(BASELINE_CSV, dtype=str)

if CURRENT_COLUMN not in current_df.columns:
    raise ValueError(
        f"{CURRENT_CSV} does not contain '{CURRENT_COLUMN}'. "
        f"Found: {current_df.columns.tolist()}"
    )

if BASELINE_COLUMN not in baseline_df.columns:
    raise ValueError(
        f"{BASELINE_CSV} does not contain '{BASELINE_COLUMN}'. "
        f"Found: {baseline_df.columns.tolist()}"
    )

current_ids = set(
    current_df[CURRENT_COLUMN].dropna().str.strip()
)
baseline_ids = set(
    baseline_df[BASELINE_COLUMN].dropna().str.strip()
)

current_ids.discard("")
baseline_ids.discard("")

new_model_ids = sorted(current_ids - baseline_ids)

pd.DataFrame(
    new_model_ids,
    columns=["modelId"],
).to_csv(OUTPUT_CSV, index=False)

print(
    f"Found {len(new_model_ids):,} new models; "
    f"saved to {OUTPUT_CSV}"
)