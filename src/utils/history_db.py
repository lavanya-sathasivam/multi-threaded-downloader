from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.utils.file_utils import DATA_DIR, ensure_app_directories


HISTORY_FILE = DATA_DIR / "history.json"


def load_history() -> list[dict]:
    ensure_app_directories()
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")
        return []

    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_history(entries: list[dict]) -> None:
    ensure_app_directories()
    HISTORY_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def append_history(task_snapshot: dict) -> None:
    history = load_history()
    history.insert(
        0,
        {
            "id": task_snapshot["id"],
            "filename": task_snapshot["filename"],
            "url": task_snapshot["url"],
            "size": task_snapshot["total_bytes"],
            "save_path": task_snapshot["output_path"],
            "status": task_snapshot["status"],
            "completed_at": datetime.now().isoformat(timespec="seconds"),
        },
    )
    save_history(history[:50])


def remove_history_entry(entry_id: str) -> None:
    save_history([entry for entry in load_history() if entry.get("id") != entry_id])


def clear_history() -> None:
    save_history([])
