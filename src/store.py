"""Persistent state: which jobs we've already alerted, full job catalog for
/tailor lookups, and the Telegram getUpdates offset. All plain JSON files in
data/ so GitHub Actions can commit them back between runs."""
import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEEN_FILE = DATA_DIR / "seen_jobs.json"
CATALOG_FILE = DATA_DIR / "jobs_catalog.json"
OFFSET_FILE = DATA_DIR / "telegram_offset.json"

CATALOG_MAX = 600  # keep the most recent N jobs available for /tailor


def _load(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default
    return default


def _save(path: Path, obj):
    DATA_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def job_id(url: str) -> str:
    """Short stable id for a job, derived from its URL."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]


def load_seen() -> set:
    return set(_load(SEEN_FILE, []))


def save_seen(seen: set):
    _save(SEEN_FILE, sorted(seen)[-5000:])  # cap file growth


def load_catalog() -> dict:
    return _load(CATALOG_FILE, {})


def save_catalog(catalog: dict):
    if len(catalog) > CATALOG_MAX:
        # drop oldest entries (dict preserves insertion order)
        for key in list(catalog.keys())[: len(catalog) - CATALOG_MAX]:
            del catalog[key]
    _save(CATALOG_FILE, catalog)


def load_offset() -> int:
    return _load(OFFSET_FILE, {"offset": 0}).get("offset", 0)


def save_offset(offset: int):
    _save(OFFSET_FILE, {"offset": offset})
