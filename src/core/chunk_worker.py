from __future__ import annotations

import time
from typing import Callable

import requests


class ChunkDownloadCancelled(Exception):
    pass


def download_chunk(
    *,
    url: str,
    start_byte: int,
    end_byte: int | None,
    destination: str,
    controller,
    progress_callback: Callable[[int], None],
    status_callback: Callable[[str], None],
    timeout: tuple[int, int] = (10, 30),
    retries: int = 3,
    chunk_size: int = 64 * 1024,
) -> None:
    headers = {}
    if end_byte is not None:
        headers["Range"] = f"bytes={start_byte}-{end_byte}"

    last_error = None

    for attempt in range(1, retries + 1):
        if controller.is_cancelled():
            raise ChunkDownloadCancelled()

        try:
            status_callback(f"retry {attempt}/{retries}" if attempt > 1 else "starting")
            with requests.get(url, headers=headers, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                with open(destination, "wb") as file_handle:
                    for chunk in response.iter_content(chunk_size):
                        controller.wait_if_paused()
                        if controller.is_cancelled():
                            raise ChunkDownloadCancelled()

                        if not chunk:
                            continue

                        file_handle.write(chunk)
                        progress_callback(len(chunk))

            status_callback("done")
            return
        except ChunkDownloadCancelled:
            status_callback("cancelled")
            raise
        except requests.RequestException as exc:
            last_error = exc
            status_callback("retrying")
            time.sleep(min(attempt, 3))

    status_callback("failed")
    if last_error is not None:
        raise last_error
    raise RuntimeError("chunk download failed")
