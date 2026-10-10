"""High-score table stored as JSON. Missing or corrupt files are ignored."""

import datetime
import json
from pathlib import Path

MAX_ENTRIES = 10


def load(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    entries = [e for e in data if isinstance(e, dict) and isinstance(e.get("score"), int)]
    entries.sort(key=lambda e: e["score"], reverse=True)
    return entries[:MAX_ENTRIES]


def save(path, entries):
    try:
        Path(path).write_text(json.dumps(entries, indent=2), encoding="utf-8")
    except OSError:
        pass


def add(entries, score, lines, level, date=None):
    """Insert a result. Returns (new_entries, rank), rank is None if it didn't place."""
    entry = {
        "score": score,
        "lines": lines,
        "level": level,
        "date": date or datetime.date.today().isoformat(),
    }
    rank = next((i for i, e in enumerate(entries) if score > e["score"]), len(entries))
    new_entries = (entries[:rank] + [entry] + entries[rank:])[:MAX_ENTRIES]
    return new_entries, (rank if rank < MAX_ENTRIES else None)
