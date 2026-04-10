import requests
import time

class DownloadWorker:

    def __init__(self, url, start, end, file_path, progress, pause_flag):
        self.url = url
        self.start = start
        self.end = end
        self.file_path = file_path
        self.progress = progress
        self.pause_flag = pause_flag

    def run(self):

        headers = {"Range": f"bytes={self.start}-{self.end}"}

        response = requests.get(self.url, headers=headers, stream=True)

        with open(self.file_path, "ab") as f:

            for chunk in response.iter_content(chunk_size=1024):

                while self.pause_flag["paused"]:
                    time.sleep(0.2)

                if chunk:
                    f.write(chunk)
                    self.progress["downloaded"] += len(chunk)