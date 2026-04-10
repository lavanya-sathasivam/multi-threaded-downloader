import time
import os

class SpeedTracker:

    def __init__(self):
        self.start_time = time.time()

    def get_speed(self, downloaded_bytes):
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0
        return downloaded_bytes / elapsed

    def get_eta(self, downloaded, total):
        speed = self.get_speed(downloaded)
        if speed == 0:
            return 0
        remaining = total - downloaded
        return remaining / speed


def get_filename_from_url(url):
    return os.path.basename(url.split("?")[0])


def format_size(size):
    for unit in ['B','KB','MB','GB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024