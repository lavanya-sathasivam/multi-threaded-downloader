import customtkinter as ctk
from tkinter import filedialog
import threading

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DownloaderApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Ultimate Multi-threaded Downloader")
        self.geometry("720x500")

        self.grid_columnconfigure(0, weight=1)

        # TITLE
        self.title_label = ctk.CTkLabel(
            self,
            text="Multi-threaded File Downloader",
            font=("Arial", 24)
        )
        self.title_label.grid(row=0, column=0, pady=20)

        # URL ENTRY
        self.url_entry = ctk.CTkEntry(
            self,
            width=500,
            placeholder_text="Paste download URL here..."
        )
        self.url_entry.grid(row=1, column=0, pady=10)

        # THREAD SELECT
        self.thread_frame = ctk.CTkFrame(self)
        self.thread_frame.grid(row=2, column=0, pady=10)

        self.thread_label = ctk.CTkLabel(
            self.thread_frame,
            text="Threads:"
        )
        self.thread_label.pack(side="left", padx=10)

        self.thread_slider = ctk.CTkSlider(
            self.thread_frame,
            from_=1,
            to=16,
            number_of_steps=15
        )
        self.thread_slider.set(4)
        self.thread_slider.pack(side="left", padx=10)

        self.thread_value = ctk.CTkLabel(
            self.thread_frame,
            text="4"
        )
        self.thread_value.pack(side="left")

        self.thread_slider.configure(
            command=self.update_threads
        )

        # DOWNLOAD LOCATION
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.grid(row=3, column=0, pady=10)

        self.path_label = ctk.CTkLabel(
            self.path_frame,
            text="Download Folder:"
        )
        self.path_label.pack(side="left", padx=10)

        self.path_entry = ctk.CTkEntry(
            self.path_frame,
            width=300
        )
        self.path_entry.pack(side="left", padx=10)

        self.browse_button = ctk.CTkButton(
            self.path_frame,
            text="Browse",
            command=self.choose_folder
        )
        self.browse_button.pack(side="left")

        # PROGRESS BAR
        self.progress = ctk.CTkProgressBar(
            self,
            width=500
        )
        self.progress.set(0)
        self.progress.grid(row=4, column=0, pady=20)

        # STATUS
        self.status_label = ctk.CTkLabel(
            self,
            text="Idle"
        )
        self.status_label.grid(row=5, column=0)

        # SPEED
        self.speed_label = ctk.CTkLabel(
            self,
            text="Speed: 0 KB/s"
        )
        self.speed_label.grid(row=6, column=0)

        # BUTTONS
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=7, column=0, pady=20)

        self.download_button = ctk.CTkButton(
            self.button_frame,
            text="Start Download",
            command=self.start_download
        )
        self.download_button.pack(side="left", padx=10)

        self.pause_button = ctk.CTkButton(
            self.button_frame,
            text="Pause",
            fg_color="orange"
        )
        self.pause_button.pack(side="left", padx=10)

    def update_threads(self, value):
        self.thread_value.configure(text=str(int(value)))

    def choose_folder(self):
        folder = filedialog.askdirectory()
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, folder)

    def start_download(self):
        url = self.url_entry.get()
        threads = int(self.thread_slider.get())

        self.status_label.configure(
            text=f"Downloading with {threads} threads..."
        )

        # start in background thread
        threading.Thread(target=self.fake_download).start()

    def fake_download(self):
        import time
        for i in range(100):
            time.sleep(0.05)
            self.progress.set(i/100)
            self.speed_label.configure(
                text=f"Speed: {200 + i} KB/s"
            )

        self.status_label.configure(text="Download Completed")


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()