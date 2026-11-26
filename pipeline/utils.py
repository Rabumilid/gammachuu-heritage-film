import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from jsonschema import validate

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
STORYBOARD_PATH = ROOT / "storyboard.json"
SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
CACHE_DIR = ROOT / "outputs" / ".cache"
RUNS_LOG = ROOT / "runs.jsonl"


def load_and_validate() -> dict:
    storyboard = json.loads(STORYBOARD_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validate(instance=storyboard, schema=schema)
    return storyboard


def compute_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def is_cached(key: str, current_hash: str, output_path: Path) -> bool:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    hash_file = CACHE_DIR / f"{key}.sha256"
    if not output_path.exists() or not hash_file.exists():
        return False
    return hash_file.read_text(encoding="utf-8").strip() == current_hash


def save_cache(key: str, current_hash: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.sha256").write_text(current_hash, encoding="utf-8")


def log_run(
    stage: str,
    shot_id: str,
    model: str,
    params: dict,
    seed: int | None,
    latency_s: float,
    cost_usd: float = 0.0,
    status: str = "success",
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "shot_id": shot_id,
        "model": model,
        "params": params,
        "seed": seed,
        "latency_s": round(latency_s, 3),
        "cost_usd": round(cost_usd, 6),
        "status": status,
    }
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def with_retry(fn, retries: int = 3, backoff: float = 2.0):
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == retries:
                raise
            time.sleep(backoff ** attempt)