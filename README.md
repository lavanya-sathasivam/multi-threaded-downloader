# Multi-Thread Downloader

A high-performance **multi-threaded file downloader** built with Python that splits files into segments and downloads them concurrently to maximize network utilization.

This project demonstrates key **Operating System concepts** such as multithreading, concurrency, synchronization, and resource sharing while providing a practical system utility similar to a lightweight download manager.

---

# Features

• Multi-threaded segmented downloading
• Pause and resume support
• Download speed monitoring
• ETA prediction
• Download queue manager
• Graphical user interface (Tkinter)
• Automatic file merging
• Download history tracking

---

# System Architecture

User URL
↓
File size detection (HTTP HEAD request)
↓
Segment splitter
↓
Thread workers download segments in parallel
↓
Temporary file storage
↓
Merge engine combines all segments
↓
Final downloaded file

---

# Technologies Used

Python
Threading module
HTTP Range Requests
Requests library
Tkinter GUI
JSON for persistent state

---

# Operating System Concepts Demonstrated

Multithreading
Concurrency
Thread synchronization
Resource sharing
Context switching
I/O management

---

# Project Structure

```
download-manager
│
├── src
│   ├── manager.py
│   ├── downloader.py
│   ├── thread_worker.py
│   ├── utils.py
│   └── ui.py
│
├── downloads
├── history.json
├── requirements.txt
└── README.md
```

---

# Installation

Clone the repository

```
git clone https://github.com/yourusername/multithread-download-manager.git
cd multithread-download-manager
```

Install dependencies

```
pip install -r requirements.txt
```

---

# Run the Application

```
python src/ui.py
```

---

# How It Works

1. The application receives a file URL from the user.
2. It sends a HEAD request to determine the file size.
3. The file is divided into multiple byte ranges.
4. Each range is downloaded using a separate thread.
5. Downloaded segments are stored temporarily.
6. After all threads complete, segments are merged into the final file.

---

# Example Workflow

1. Enter file URL
2. Select number of threads
3. Start download
4. Monitor progress, speed, and ETA
5. Pause or resume download
6. File merges automatically after completion

---

# Future Improvements

Download scheduling
Bandwidth limiting
Dark mode interface
Browser integration
Advanced thread monitoring

---

# Educational Purpose

This project was developed as part of an **Operating Systems course project** to demonstrate practical implementation of multithreading and concurrent programming concepts.

---

# License

MIT License

---

# Author

Lavanya S
Student of AIML Department