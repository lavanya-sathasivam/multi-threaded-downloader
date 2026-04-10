import threading
import requests
import os

from thread_worker import DownloadWorker
from utils import SpeedTracker

class MultiThreadDownloader:

    def __init__(self, url, threads=4, output_folder="downloads"):

        self.url = url
        self.threads = threads
        self.output_folder = output_folder

        self.file_size = 0
        self.progress = {"downloaded": 0}
        self.pause_flag = {"paused": False}

    def get_file_size(self):

        r = requests.head(self.url)

        if "Content-Length" not in r.headers:
            raise Exception("Server does not provide file size")

        self.file_size = int(r.headers["Content-Length"])
        return self.file_size

    def start(self):

        size = self.get_file_size()
        part_size = size // self.threads
        threads = []
        tracker = SpeedTracker()
        for i in range(self.threads):
            start = i * part_size
            end = size - 1 if i == self.threads - 1 else start + part_size - 1
            file_path = f"{self.output_folder}/part_{i}.tmp"
            worker = DownloadWorker(
                self.url,
                start,
                end,
                file_path,
                self.progress,
                self.pause_flag
            )

            t = threading.Thread(target=worker.run)
            threads.append(t)
            t.start()

        while any(t.is_alive() for t in threads):
            downloaded = self.progress["downloaded"]
            speed = tracker.get_speed(downloaded)
            eta = tracker.get_eta(downloaded, size)
            print(
                f"Downloaded {downloaded}/{size} bytes | "
                f"Speed {speed/1024/1024:.2f} MB/s | ETA {eta:.1f}s",
                end="\r"
            )

        for t in threads:
            t.join()

        self.merge_files()

    def merge_files(self):
        filename = self.url.split("/")[-1]
        final_path = f"{self.output_folder}/{filename}"
        with open(final_path, "wb") as outfile:
            for i in range(self.threads):
                part = f"{self.output_folder}/part_{i}.tmp"
                with open(part, "rb") as pf:
                    outfile.write(pf.read())
                os.remove(part)
        print("\nDownload completed:", final_path)