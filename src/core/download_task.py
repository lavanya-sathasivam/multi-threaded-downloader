from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from typing import Dict, Optional
from uuid import uuid4


TASK_STATUSES = (
    "queued",
    "connecting",
    "downloading",
    "paused",
    "merging",
    "completed",
    "failed",
    "cancelled",
)


@dataclass
class DownloadTask:
    url: str
    output_dir: str
    requested_threads: int
    id: str = field(default_factory=lambda: uuid4().hex[:8])
    filename: str = ""
    output_path: str = ""
    total_bytes: int = 0
    downloaded_bytes: int = 0
    speed_bps: float = 0.0
    eta_seconds: Optional[float] = None
    status: str = "queued"
    error_message: str = ""
    supports_ranges: bool = True
    effective_threads: int = 0
    created_at: float = field(default_factory=time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    range_note: str = ""
    thread_progress: Dict[int, int] = field(default_factory=dict)
    thread_totals: Dict[int, int] = field(default_factory=dict)
    thread_statuses: Dict[int, str] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock, repr=False)

    def reset_for_retry(self) -> None:
        with self.lock:
            self.downloaded_bytes = 0
            self.speed_bps = 0.0
            self.eta_seconds = None
            self.status = "queued"
            self.error_message = ""
            self.supports_ranges = True
            self.effective_threads = 0
            self.started_at = None
            self.completed_at = None
            self.range_note = ""
            self.thread_progress = {}
            self.thread_totals = {}
            self.thread_statuses = {}

    def update_status(self, status: str, error_message: str = "") -> None:
        with self.lock:
            self.status = status
            if error_message:
                self.error_message = error_message

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "id": self.id,
                "url": self.url,
                "filename": self.filename,
                "output_path": self.output_path,
                "requested_threads": self.requested_threads,
                "effective_threads": self.effective_threads,
                "total_bytes": self.total_bytes,
                "downloaded_bytes": self.downloaded_bytes,
                "speed_bps": self.speed_bps,
                "eta_seconds": self.eta_seconds,
                "status": self.status,
                "error_message": self.error_message,
                "supports_ranges": self.supports_ranges,
                "range_note": self.range_note,
                "thread_progress": dict(self.thread_progress),
                "thread_totals": dict(self.thread_totals),
                "thread_statuses": dict(self.thread_statuses),
                "created_at": self.created_at,
                "started_at": self.started_at,
                "completed_at": self.completed_at,
            }
