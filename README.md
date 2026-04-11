# OS Project Multi-Threaded Downloader

A polished Windows desktop downloader built with Python and CustomTkinter for an Operating Systems project. The app downloads files in parallel chunks, shows thread activity live, manages a queue safely, and exposes pause, resume, cancel, retry, and history actions in one GUI.

## Features

- Multi-threaded chunk downloading with HTTP range requests
- Automatic fallback to single-thread mode when a server does not support ranges
- Session-only pause and resume
- Cancel and retry controls
- Sequential download queue for predictable demos
- Live task table with progress, speed, ETA, and task state
- Thread monitor showing worker-level status and per-thread bytes
- Download history stored in `data/history.json`
- Open-file and open-folder shortcuts after completion

## OS Concepts Demonstrated

- Multithreading through chunk workers
- Synchronization between UI, queue manager, and worker threads
- Shared resource coordination when combining chunk files
- Task lifecycle management and state transitions
- I/O management with streamed network reads and file writes

## Project Structure

```text
multi-threaded-downloader/
|-- app.py
|-- data/
|   `-- history.json
|-- downloads/
|-- temp_chunks/
`-- src/
    |-- core/
    |   |-- chunk_worker.py
    |   |-- download_task.py
    |   |-- downloader.py
    |   |-- pause_resume.py
    |   `-- queue_manager.py
    |-- ui/
    |   `-- main_window.py
    `-- utils/
        |-- file_utils.py
        |-- history_db.py
        `-- network_utils.py
```

## Architecture Flow

1. User enters a URL, thread count, and save folder in the GUI.
2. The queue manager creates a `DownloadTask` and places it in the queue.
3. The downloader probes the server for file size, filename, and range support.
4. If ranges are supported, the file is split into byte segments and downloaded by multiple worker threads.
5. Progress from each thread is aggregated into task-level speed, ETA, and UI updates.
6. Temporary chunk files are merged into the final output file.
7. The task is marked completed and recorded in history.

## Installation

```bash
pip install -r requirements.txt
```

## Run The App

```bash
python app.py
```

## Demo Notes

- The app processes one queued task at a time to keep the UI stable during demos.
- Pause and resume work while the app stays open.
- Servers without `Accept-Ranges: bytes` are downloaded in single-thread mode automatically.

## Optional Packaging

If you want a portable Windows demo build later, you can package it with PyInstaller:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name os-downloader app.py
```

## Author

Lavanya S
