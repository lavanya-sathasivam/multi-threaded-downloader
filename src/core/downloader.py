from __future__ import annotations

import threading
import time
from pathlib import Path

from src.core.chunk_worker import ChunkDownloadCancelled, download_chunk
from src.core.pause_resume import ExecutionController
from src.utils.file_utils import (
    cleanup_files,
    chunk_file_for,
    ensure_app_directories,
    merge_chunks,
    sanitize_filename,
    unique_path,
)
from src.utils.network_utils import probe_download, validate_url


class Downloader:
    def __init__(self, task, controller: ExecutionController, on_update=None) -> None:
        self.task = task
        self.controller = controller
        self.on_update = on_update or (lambda _task: None)
        self._speed_window: list[tuple[float, int]] = []
        self._progress_lock = threading.Lock()

    def start(self) -> str:
        ensure_app_directories()

        url = validate_url(self.task.url)
        self.task.update_status("connecting")
        self._publish()

        metadata = probe_download(url)
        filename = sanitize_filename(metadata["filename"])
        output_path = unique_path(self.task.output_dir, filename)

        with self.task.lock:
            self.task.url = metadata["final_url"]
            self.task.filename = filename
            self.task.output_path = str(output_path)
            self.task.total_bytes = metadata["total_bytes"]
            self.task.supports_ranges = metadata["supports_ranges"]
            self.task.effective_threads = (
                self.task.requested_threads if metadata["supports_ranges"] else 1
            )
            self.task.range_note = (
                ""
                if metadata["supports_ranges"]
                else "Server does not support range requests. Falling back to single-thread mode."
            )
            self.task.started_at = time.time()
            self.task.thread_progress = {i: 0 for i in range(self.task.effective_threads)}
            self.task.thread_statuses = {i: "queued" for i in range(self.task.effective_threads)}

        self.task.update_status("downloading")
        self._publish()

        chunk_plans = self._build_chunk_plan()
        workers = []
        errors: list[Exception] = []

        def run_chunk(chunk_index: int, start_byte: int, end_byte: int | None, chunk_path: Path) -> None:
            try:
                self._set_thread_status(chunk_index, "downloading")
                download_chunk(
                    url=self.task.url,
                    start_byte=start_byte,
                    end_byte=end_byte,
                    destination=str(chunk_path),
                    controller=self.controller,
                    progress_callback=lambda delta: self._record_progress(chunk_index, delta),
                    status_callback=lambda status: self._set_thread_status(chunk_index, status),
                )
            except ChunkDownloadCancelled as exc:
                errors.append(exc)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
                self._set_thread_status(chunk_index, "failed")

        for chunk_index, start_byte, end_byte, chunk_path in chunk_plans:
            worker = threading.Thread(
                target=run_chunk,
                args=(chunk_index, start_byte, end_byte, chunk_path),
                daemon=True,
            )
            workers.append(worker)
            worker.start()

        while any(worker.is_alive() for worker in workers):
            if self.controller.is_paused():
                self.task.update_status("paused")
            elif self.task.status == "paused":
                self.task.update_status("downloading")
            self._publish()
            time.sleep(0.2)

        for worker in workers:
            worker.join()

        if self.controller.is_cancelled():
            cleanup_files([chunk_path for _, _, _, chunk_path in chunk_plans])
            self.task.update_status("cancelled")
            self._publish()
            return self.task.status

        if errors:
            cleanup_files([chunk_path for _, _, _, chunk_path in chunk_plans])
            self.task.update_status("failed", str(errors[0]))
            self._publish()
            raise errors[0]

        self.task.update_status("merging")
        self._publish()
        merge_chunks([chunk_path for _, _, _, chunk_path in chunk_plans], self.task.output_path)

        with self.task.lock:
            self.task.downloaded_bytes = self.task.total_bytes
            self.task.speed_bps = 0.0
            self.task.eta_seconds = 0
            self.task.completed_at = time.time()

        self.task.update_status("completed")
        self._publish()
        cleanup_files([chunk_path for _, _, _, chunk_path in chunk_plans])
        return self.task.status

    def _build_chunk_plan(self) -> list[tuple[int, int, int | None, Path]]:
        total_bytes = self.task.total_bytes
        total_threads = max(1, self.task.effective_threads)
        chunk_plans: list[tuple[int, int, int | None, Path]] = []

        if total_threads == 1 or total_bytes <= 0:
            chunk_path = chunk_file_for(self.task.id, 0)
            with self.task.lock:
                self.task.thread_totals[0] = total_bytes
            chunk_plans.append((0, 0, None, chunk_path))
            return chunk_plans

        chunk_size = total_bytes // total_threads
        for index in range(total_threads):
            start_byte = chunk_size * index
            end_byte = total_bytes - 1 if index == total_threads - 1 else (start_byte + chunk_size - 1)
            with self.task.lock:
                self.task.thread_totals[index] = end_byte - start_byte + 1
            chunk_plans.append((index, start_byte, end_byte, chunk_file_for(self.task.id, index)))
        return chunk_plans

    def _record_progress(self, chunk_index: int, delta: int) -> None:
        with self._progress_lock, self.task.lock:
            self.task.downloaded_bytes += delta
            self.task.thread_progress[chunk_index] = self.task.thread_progress.get(chunk_index, 0) + delta
            now = time.time()
            self._speed_window.append((now, delta))
            self._speed_window = [(stamp, size) for stamp, size in self._speed_window if now - stamp <= 2.0]
            total_recent = sum(size for _, size in self._speed_window)
            if self._speed_window:
                elapsed = max(now - self._speed_window[0][0], 0.001)
                self.task.speed_bps = total_recent / elapsed
            if self.task.speed_bps > 0 and self.task.total_bytes:
                remaining = max(self.task.total_bytes - self.task.downloaded_bytes, 0)
                self.task.eta_seconds = remaining / self.task.speed_bps
            else:
                self.task.eta_seconds = None

    def _set_thread_status(self, chunk_index: int, status: str) -> None:
        with self.task.lock:
            self.task.thread_statuses[chunk_index] = status
        self._publish()

    def _publish(self) -> None:
        self.on_update(self.task)
