from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DOWNLOAD_DIR = ROOT_DIR / "downloads"
TEMP_DIR = ROOT_DIR / "temp_chunks"
DATA_DIR = ROOT_DIR / "data"


def ensure_app_directories() -> None:
    DOWNLOAD_DIR.mkdir(exist_ok=True)
    TEMP_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)


def sanitize_filename(filename: str) -> str:
    cleaned = filename.strip().strip(".")
    if not cleaned:
        cleaned = "download.bin"

    invalid_chars = '<>:"/\\|?*'
    for invalid_char in invalid_chars:
        cleaned = cleaned.replace(invalid_char, "_")

    return cleaned or "download.bin"


def unique_path(directory: str | Path, filename: str) -> Path:
    base_dir = Path(directory)
    safe_name = sanitize_filename(filename)
    candidate = base_dir / safe_name
    stem = candidate.stem
    suffix = candidate.suffix
    counter = 1

    while candidate.exists():
        candidate = base_dir / f"{stem} ({counter}){suffix}"
        counter += 1

    return candidate


def chunk_file_for(task_id: str, chunk_index: int) -> Path:
    return TEMP_DIR / f"{task_id}.part{chunk_index}"


def merge_chunks(chunk_paths: list[Path], destination: str | Path) -> None:
    destination_path = Path(destination)
    with destination_path.open("wb") as destination_handle:
        for chunk_path in chunk_paths:
            with chunk_path.open("rb") as source_handle:
                while True:
                    buffer = source_handle.read(64 * 1024)
                    if not buffer:
                        break
                    destination_handle.write(buffer)


def cleanup_files(paths: list[str | Path]) -> None:
    for path in paths:
        candidate = Path(path)
        if candidate.exists():
            candidate.unlink()
