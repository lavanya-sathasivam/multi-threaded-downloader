from __future__ import annotations

import queue
import threading
from typing import Callable, Optional

from src.core.download_task import DownloadTask
from src.core.downloader import Downloader
from src.core.pause_resume import ExecutionController
from src.utils.file_utils import DOWNLOAD_DIR, ensure_app_directories
from src.utils.history_db import append_history


class QueueManager:
    def __init__(self, on_task_update: Optional[Callable[[DownloadTask], None]] = None) -> None:
        ensure_app_directories()
        self.on_task_update = on_task_update or (lambda task: None)
        self.download_queue: queue.Queue[DownloadTask] = queue.Queue()
        self.tasks: list[DownloadTask] = []
        self.active_task: Optional[DownloadTask] = None
        self.active_controller: Optional[ExecutionController] = None
        self._lock = threading.Lock()
        self.worker = threading.Thread(target=self._run, daemon=True)
        self.worker.start()

    def add_task(self, url: str, threads: int, output_dir: str | None = None) -> DownloadTask:
        task = DownloadTask(url=url, output_dir=output_dir or str(DOWNLOAD_DIR), requested_threads=threads)
        with self._lock:
            self.tasks.append(task)
        self.download_queue.put(task)
        self.on_task_update(task)
        return task

    def retry_task(self, task_id: str) -> DownloadTask | None:
        original = self.get_task(task_id)
        if original is None:
            return None

        retry_task = DownloadTask(
            url=original.url,
            output_dir=original.output_dir,
            requested_threads=original.requested_threads,
        )
        retry_task.filename = original.filename
        with self._lock:
            self.tasks.append(retry_task)
        self.download_queue.put(retry_task)
        self.on_task_update(retry_task)
        return retry_task

    def get_task(self, task_id: str) -> DownloadTask | None:
        with self._lock:
            for task in self.tasks:
                if task.id == task_id:
                    return task
        return None

    def pause_task(self, task_id: str) -> None:
        if self.active_task and self.active_task.id == task_id and self.active_controller:
            self.active_controller.pause()
            self.active_task.update_status("paused")
            self.on_task_update(self.active_task)

    def resume_task(self, task_id: str) -> None:
        if self.active_task and self.active_task.id == task_id and self.active_controller:
            self.active_controller.resume()
            self.active_task.update_status("downloading")
            self.on_task_update(self.active_task)

    def cancel_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if task is None:
            return

        if self.active_task and self.active_task.id == task_id and self.active_controller:
            self.active_controller.cancel()
            return

        if task.status == "queued":
            task.update_status("cancelled")
            self.on_task_update(task)

    def get_tasks_snapshot(self) -> list[dict]:
        with self._lock:
            return [task.snapshot() for task in self.tasks]

    def _run(self) -> None:
        while True:
            task = self.download_queue.get()
            if task.status == "cancelled":
                self.download_queue.task_done()
                continue

            controller = ExecutionController()
            with self._lock:
                self.active_task = task
                self.active_controller = controller

            downloader = Downloader(task, controller, on_update=self.on_task_update)

            try:
                final_status = downloader.start()
                if final_status == "completed":
                    append_history(task.snapshot())
            except Exception as exc:  # noqa: BLE001
                task.update_status("failed", str(exc))
                self.on_task_update(task)
            finally:
                with self._lock:
                    self.active_task = None
                    self.active_controller = None
                self.download_queue.task_done()
