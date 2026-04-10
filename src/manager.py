from downloader import MultiThreadDownloader

class DownloadManager:
    def __init__(self):
        self.queue = []

    def add_download(self, url, threads):
        job = {
            "url": url,
            "threads": threads,
            "status": "waiting"
        }
        self.queue.append(job)

    def start_next(self):
        for job in self.queue:
            if job["status"] == "waiting":
                job["status"] = "downloading"
                downloader = MultiThreadDownloader(
                    job["url"],
                    job["threads"]
                )

                downloader.start()
                job["status"] = "completed"
                break