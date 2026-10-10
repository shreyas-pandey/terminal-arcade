"""Per-game high scores and arcade settings, one JSON file each under saves/.

Missing or corrupt files are ignored and recreated.
"""

import datetime
import json
import shutil
from pathlib import Path

MAX_ENTRIES = 10


def insert_score(entries, entry):
    """Insert an entry by score. Returns (new_entries, rank); rank is None if it didn't place."""
    rank = next((i for i, e in enumerate(entries) if entry["score"] > e["score"]), len(entries))
    new_entries = (entries[:rank] + [entry] + entries[rank:])[:MAX_ENTRIES]
    return new_entries, (rank if rank < MAX_ENTRIES else None)


class Saves:
    def __init__(self, directory):
        self.directory = Path(directory)
        self._scores = {}

    def path(self, name):
        return self.directory / f"{name}.json"

    def _read(self, name):
        try:
            return json.loads(self.path(name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _write(self, name, data):
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            self.path(name).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass

    # --- scores -------------------------------------------------------

    def scores(self, game):
        if game not in self._scores:
            data = self._read(game)
            entries = [e for e in data if isinstance(e, dict) and isinstance(e.get("score"), int)] \
                if isinstance(data, list) else []
            entries.sort(key=lambda e: e["score"], reverse=True)
            self._scores[game] = entries[:MAX_ENTRIES]
        return self._scores[game]

    def best(self, game):
        entries = self.scores(game)
        return entries[0]["score"] if entries else 0

    def add_score(self, game, score, **details):
        """Record a finished game. Returns its rank (0 = new best) or None."""
        if score <= 0:
            return None
        entry = {"score": score, **details, "date": datetime.date.today().isoformat()}
        self._scores[game], rank = insert_score(self.scores(game), entry)
        self._write(game, self._scores[game])
        return rank

    # --- settings -----------------------------------------------------

    def setting(self, key, default=None):
        data = self._read("settings")
        return data.get(key, default) if isinstance(data, dict) else default

    def set_setting(self, key, value):
        data = self._read("settings")
        data = data if isinstance(data, dict) else {}
        data[key] = value
        self._write("settings", data)


def migrate_legacy(saves, legacy_path, game):
    """Move a pre-arcade high-score file into saves/ once."""
    legacy_path = Path(legacy_path)
    if legacy_path.exists() and not saves.path(game).exists():
        try:
            saves.directory.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy_path), str(saves.path(game)))
        except OSError:
            pass
