from __future__ import annotations

import threading


class ExecutionController:
    def __init__(self) -> None:
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._cancel_event = threading.Event()

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def cancel(self) -> None:
        self._cancel_event.set()
        self._resume_event.set()

    def wait_if_paused(self) -> None:
        self._resume_event.wait()

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()
