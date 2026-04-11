from __future__ import annotations

import os
from pathlib import Path
from tkinter import END, StringVar, filedialog, messagebox, ttk

import customtkinter as ctk

from src.core.queue_manager import QueueManager
from src.utils.file_utils import DOWNLOAD_DIR, ensure_app_directories, sanitize_filename
from src.utils.history_db import clear_history, load_history, remove_history_entry


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")


class DownloaderApp(ctk.CTk):
    STATUS_COLORS = {
        "queued": "#9ca3af",
        "connecting": "#f59e0b",
        "downloading": "#22c55e",
        "paused": "#f97316",
        "merging": "#06b6d4",
        "completed": "#10b981",
        "failed": "#ef4444",
        "cancelled": "#64748b",
    }

    def __init__(self) -> None:
        super().__init__()
        ensure_app_directories()

        self.title("Multi-Threaded Downloader")
        self.geometry("1240x820")
        self.minsize(1100, 740)

        self.output_dir_var = StringVar(value=str(DOWNLOAD_DIR))
        self.selected_task_id: str | None = None
        self.selected_history_id: str | None = None
        self.task_rows: dict[str, str] = {}

        self.queue_manager = QueueManager(on_task_update=self._on_task_update)

        self._configure_styles()
        self._build_layout()
        self._refresh_history()
        self.after(400, self._poll_ui)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Downloader.Treeview",
            background="#111827",
            foreground="#e5e7eb",
            fieldbackground="#111827",
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Downloader.Treeview.Heading",
            background="#1f2937",
            foreground="#f9fafb",
            relief="flat",
        )
        style.map("Downloader.Treeview", background=[("selected", "#166534")])

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        header = ctk.CTkFrame(self, corner_radius=18)
        header.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="ew")
        header.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(
            header,
            text="Multi-Threaded Downloader",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, padx=18, pady=(16, 2), sticky="w")
        ctk.CTkLabel(
            header,
            text="Visible threads, queue states, pause/resume, and clean history.",
            text_color="#a7f3d0",
        ).grid(row=1, column=0, padx=18, pady=(0, 16), sticky="w")

        self.summary_label = ctk.CTkLabel(header, text="0 tasks", anchor="e")
        self.summary_label.grid(row=0, column=2, padx=18, pady=(16, 2), sticky="e")
        self.speed_summary_label = ctk.CTkLabel(header, text="Total speed: 0 B/s", anchor="e")
        self.speed_summary_label.grid(row=1, column=2, padx=18, pady=(0, 16), sticky="e")

        content = ctk.CTkFrame(self, corner_radius=18)
        content.grid(row=1, column=0, padx=18, pady=10, sticky="nsew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(1, weight=1)

        self._build_form(content)
        self._build_task_table(content)
        self._build_side_panel(content)

        footer = ctk.CTkFrame(self, corner_radius=18)
        footer.grid(row=2, column=0, padx=18, pady=(10, 18), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(footer, text="About Project", command=self._show_about).grid(
            row=0, column=0, padx=12, pady=12, sticky="w"
        )
        ctk.CTkButton(footer, text="Open Downloads Folder", command=self._open_downloads_folder).grid(
            row=0, column=1, padx=12, pady=12, sticky="e"
        )

    def _build_form(self, parent) -> None:
        form = ctk.CTkFrame(parent, corner_radius=16)
        form.grid(row=0, column=0, columnspan=2, padx=16, pady=16, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form, text="File URL").grid(row=0, column=0, padx=14, pady=(14, 8), sticky="w")
        self.url_entry = ctk.CTkEntry(form, placeholder_text="https://example.com/file.zip")
        self.url_entry.grid(row=0, column=1, columnspan=3, padx=14, pady=(14, 8), sticky="ew")

        ctk.CTkLabel(form, text="Save To").grid(row=1, column=0, padx=14, pady=8, sticky="w")
        self.output_entry = ctk.CTkEntry(form, textvariable=self.output_dir_var)
        self.output_entry.grid(row=1, column=1, padx=14, pady=8, sticky="ew")
        ctk.CTkButton(form, text="Browse", width=110, command=self._choose_output_dir).grid(
            row=1, column=2, padx=14, pady=8
        )

        ctk.CTkLabel(form, text="Threads").grid(row=1, column=3, padx=14, pady=8, sticky="w")
        self.thread_slider = ctk.CTkSlider(form, from_=1, to=16, number_of_steps=15, command=self._sync_thread_label)
        self.thread_slider.set(8)
        self.thread_slider.grid(row=1, column=4, padx=(0, 8), pady=8, sticky="ew")
        self.thread_value_label = ctk.CTkLabel(form, text="8")
        self.thread_value_label.grid(row=1, column=5, padx=(0, 14), pady=8)

        self.note_label = ctk.CTkLabel(form, text="Add a URL to create a queued task. Downloads run one-by-one for stable demos.")
        self.note_label.grid(row=2, column=0, columnspan=4, padx=14, pady=(4, 14), sticky="w")

        ctk.CTkButton(form, text="Add Download", command=self._submit_download, width=150).grid(
            row=2, column=5, padx=14, pady=(4, 14), sticky="e"
        )

    def _build_task_table(self, parent) -> None:
        frame = ctk.CTkFrame(parent, corner_radius=16)
        frame.grid(row=1, column=0, padx=(16, 8), pady=(0, 16), sticky="nsew")
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Download Queue", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 10), sticky="w"
        )

        columns = ("file", "progress", "speed", "eta", "status")
        self.task_table = ttk.Treeview(frame, columns=columns, show="headings", style="Downloader.Treeview")
        self.task_table.heading("file", text="File")
        self.task_table.heading("progress", text="Progress")
        self.task_table.heading("speed", text="Speed")
        self.task_table.heading("eta", text="ETA")
        self.task_table.heading("status", text="Status")
        self.task_table.column("file", width=300)
        self.task_table.column("progress", width=95, anchor="center")
        self.task_table.column("speed", width=100, anchor="center")
        self.task_table.column("eta", width=85, anchor="center")
        self.task_table.column("status", width=105, anchor="center")
        self.task_table.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="nsew")
        self.task_table.bind("<<TreeviewSelect>>", self._on_task_selected)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.task_table.yview)
        scrollbar.grid(row=1, column=1, pady=(0, 10), sticky="ns")
        self.task_table.configure(yscrollcommand=scrollbar.set)

    def _build_side_panel(self, parent) -> None:
        panel = ctk.CTkFrame(parent, corner_radius=16)
        panel.grid(row=1, column=1, padx=(8, 16), pady=(0, 16), sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(5, weight=1)
        panel.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(panel, text="Task Details", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=14, pady=(14, 8), sticky="w"
        )

        self.selected_file_label = ctk.CTkLabel(panel, text="No task selected", anchor="w")
        self.selected_file_label.grid(row=1, column=0, padx=14, pady=4, sticky="ew")
        self.status_chip = ctk.CTkLabel(panel, text="idle", corner_radius=999, fg_color="#334155", padx=12, pady=6)
        self.status_chip.grid(row=2, column=0, padx=14, pady=6, sticky="w")
        self.selected_meta_label = ctk.CTkLabel(panel, text="Choose a task to inspect progress and threads.", justify="left")
        self.selected_meta_label.grid(row=3, column=0, padx=14, pady=4, sticky="ew")

        action_frame = ctk.CTkFrame(panel, fg_color="transparent")
        action_frame.grid(row=4, column=0, padx=14, pady=8, sticky="ew")
        for column in range(3):
            action_frame.grid_columnconfigure(column, weight=1)

        ctk.CTkButton(action_frame, text="Pause", command=self._pause_selected).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(action_frame, text="Resume", command=self._resume_selected).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(action_frame, text="Cancel", command=self._cancel_selected, fg_color="#7f1d1d", hover_color="#991b1b").grid(
            row=0, column=2, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(action_frame, text="Retry", command=self._retry_selected).grid(row=1, column=0, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(action_frame, text="Open File", command=self._open_selected_file).grid(row=1, column=1, padx=4, pady=4, sticky="ew")
        ctk.CTkButton(action_frame, text="Open Folder", command=self._open_selected_folder).grid(row=1, column=2, padx=4, pady=4, sticky="ew")

        ctk.CTkLabel(panel, text="Thread Monitor", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=5, column=0, padx=14, pady=(10, 8), sticky="nw"
        )
        self.thread_monitor = ctk.CTkTextbox(panel, height=180)
        self.thread_monitor.grid(row=6, column=0, padx=14, pady=(0, 12), sticky="nsew")
        self.thread_monitor.insert("1.0", "No active thread data yet.")
        self.thread_monitor.configure(state="disabled")

        ctk.CTkLabel(panel, text="History", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=7, column=0, padx=14, pady=(0, 8), sticky="nw"
        )
        history_frame = ctk.CTkFrame(panel)
        history_frame.grid(row=8, column=0, padx=14, pady=(0, 14), sticky="nsew")
        history_frame.grid_columnconfigure(0, weight=1)
        history_frame.grid_rowconfigure(0, weight=1)

        self.history_table = ttk.Treeview(
            history_frame,
            columns=("file", "status", "time"),
            show="headings",
            height=7,
            style="Downloader.Treeview",
        )
        self.history_table.heading("file", text="File")
        self.history_table.heading("status", text="Status")
        self.history_table.heading("time", text="Completed")
        self.history_table.column("file", width=180)
        self.history_table.column("status", width=80, anchor="center")
        self.history_table.column("time", width=120, anchor="center")
        self.history_table.grid(row=0, column=0, sticky="nsew")
        self.history_table.bind("<<TreeviewSelect>>", self._on_history_selected)

        history_actions = ctk.CTkFrame(panel, fg_color="transparent")
        history_actions.grid(row=9, column=0, padx=14, pady=(0, 14), sticky="ew")
        history_actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(history_actions, text="Remove Entry", command=self._remove_history_entry).grid(
            row=0, column=0, padx=4, pady=4, sticky="ew"
        )
        ctk.CTkButton(history_actions, text="Clear History", command=self._clear_history).grid(
            row=0, column=1, padx=4, pady=4, sticky="ew"
        )

    def _sync_thread_label(self, value) -> None:
        self.thread_value_label.configure(text=str(int(float(value))))

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(DOWNLOAD_DIR))
        if selected:
            self.output_dir_var.set(selected)

    def _submit_download(self) -> None:
        url = self.url_entry.get().strip()
        output_dir = self.output_dir_var.get().strip() or str(DOWNLOAD_DIR)
        thread_count = int(self.thread_slider.get())

        if not url:
            messagebox.showwarning("Missing URL", "Enter a file URL to add a download task.")
            return

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        task = self.queue_manager.add_task(url=url, threads=thread_count, output_dir=output_dir)
        self.selected_task_id = task.id
        self.note_label.configure(text="Task queued. The worker will start it when the current task finishes.")
        self.url_entry.delete(0, END)
        self._refresh_tasks()

    def _on_task_update(self, _task) -> None:
        self.after(0, self._refresh_tasks)

    def _refresh_tasks(self) -> None:
        tasks = self.queue_manager.get_tasks_snapshot()
        selected_exists = False

        for task in tasks:
            values = (
                task["filename"] or sanitize_filename(task["url"].split("/")[-1] or "pending"),
                self._format_progress(task["downloaded_bytes"], task["total_bytes"]),
                self._format_speed(task["speed_bps"]),
                self._format_eta(task["eta_seconds"]),
                task["status"],
            )
            row_id = self.task_rows.get(task["id"])
            if row_id is None:
                row_id = self.task_table.insert("", END, iid=task["id"], values=values)
                self.task_rows[task["id"]] = row_id
            else:
                self.task_table.item(row_id, values=values)

            if self.selected_task_id == task["id"]:
                selected_exists = True

        if self.selected_task_id and selected_exists:
            self.task_table.selection_set(self.selected_task_id)
            self._refresh_selected_task_details()
        elif tasks and not self.selected_task_id:
            self.selected_task_id = tasks[-1]["id"]
            self.task_table.selection_set(self.selected_task_id)
            self._refresh_selected_task_details()
        else:
            self._update_summary(tasks)

    def _refresh_selected_task_details(self) -> None:
        task = self._selected_task_snapshot()
        tasks = self.queue_manager.get_tasks_snapshot()
        self._update_summary(tasks)

        if task is None:
            self.selected_file_label.configure(text="No task selected")
            self.selected_meta_label.configure(text="Choose a task to inspect progress and threads.")
            self.status_chip.configure(text="idle", fg_color="#334155")
            self._set_thread_monitor_text("No active thread data yet.")
            return

        self.selected_file_label.configure(text=task["filename"] or task["url"])
        note = task["range_note"] or task["error_message"] or f"Saved to: {task['output_path'] or self.output_dir_var.get()}"
        self.selected_meta_label.configure(
            text=(
                f"Requested threads: {task['requested_threads']}\n"
                f"Effective threads: {task['effective_threads'] or '-'}\n"
                f"Size: {self._format_bytes(task['total_bytes'])}\n"
                f"Downloaded: {self._format_bytes(task['downloaded_bytes'])}\n"
                f"{note}"
            )
        )
        self.status_chip.configure(
            text=task["status"],
            fg_color=self.STATUS_COLORS.get(task["status"], "#334155"),
        )
        self._set_thread_monitor_text(self._build_thread_monitor_text(task))

    def _selected_task_snapshot(self) -> dict | None:
        if not self.selected_task_id:
            return None
        for task in self.queue_manager.get_tasks_snapshot():
            if task["id"] == self.selected_task_id:
                return task
        return None

    def _build_thread_monitor_text(self, task: dict) -> str:
        lines = [
            f"Active thread count: {sum(1 for status in task['thread_statuses'].values() if status not in {'done', 'cancelled', 'failed'})}",
            f"Current total speed: {self._format_speed(task['speed_bps'])}",
            "",
        ]

        if not task["thread_statuses"]:
            lines.append("Thread details will appear once the download starts.")
            return "\n".join(lines)

        for thread_id in sorted(task["thread_statuses"]):
            done = task["thread_progress"].get(thread_id, 0)
            total = task["thread_totals"].get(thread_id, 0)
            status = task["thread_statuses"].get(thread_id, "queued")
            percent = f"{(done / total * 100):.0f}%" if total else "--"
            lines.append(
                f"Thread {thread_id + 1}: {status:<10} {percent:>4}  {self._format_bytes(done)} / {self._format_bytes(total)}"
            )
        return "\n".join(lines)

    def _set_thread_monitor_text(self, text: str) -> None:
        self.thread_monitor.configure(state="normal")
        self.thread_monitor.delete("1.0", END)
        self.thread_monitor.insert("1.0", text)
        self.thread_monitor.configure(state="disabled")

    def _update_summary(self, tasks: list[dict]) -> None:
        active = [task for task in tasks if task["status"] in {"connecting", "downloading", "paused", "merging"}]
        completed = [task for task in tasks if task["status"] == "completed"]
        failed = [task for task in tasks if task["status"] == "failed"]
        total_speed = sum(task["speed_bps"] for task in active)
        self.summary_label.configure(
            text=f"{len(tasks)} tasks | {len(active)} active | {len(completed)} completed | {len(failed)} failed"
        )
        self.speed_summary_label.configure(text=f"Total speed: {self._format_speed(total_speed)}")

    def _on_task_selected(self, _event=None) -> None:
        selection = self.task_table.selection()
        if selection:
            self.selected_task_id = selection[0]
            self._refresh_selected_task_details()

    def _pause_selected(self) -> None:
        if self.selected_task_id:
            self.queue_manager.pause_task(self.selected_task_id)

    def _resume_selected(self) -> None:
        if self.selected_task_id:
            self.queue_manager.resume_task(self.selected_task_id)

    def _cancel_selected(self) -> None:
        if self.selected_task_id:
            self.queue_manager.cancel_task(self.selected_task_id)

    def _retry_selected(self) -> None:
        task = self._selected_task_snapshot()
        if task and task["status"] in {"failed", "cancelled"}:
            new_task = self.queue_manager.retry_task(task["id"])
            if new_task:
                self.selected_task_id = new_task.id

    def _open_selected_file(self) -> None:
        task = self._selected_task_snapshot()
        if task and task["status"] == "completed" and task["output_path"]:
            os.startfile(task["output_path"])

    def _open_selected_folder(self) -> None:
        task = self._selected_task_snapshot()
        if task and task["output_path"]:
            os.startfile(str(Path(task["output_path"]).parent))

    def _open_downloads_folder(self) -> None:
        os.startfile(self.output_dir_var.get() or str(DOWNLOAD_DIR))

    def _refresh_history(self) -> None:
        for item in self.history_table.get_children():
            self.history_table.delete(item)

        for entry in load_history():
            self.history_table.insert(
                "",
                END,
                iid=entry["id"],
                values=(entry["filename"], entry["status"], entry["completed_at"].replace("T", " ")),
            )

    def _on_history_selected(self, _event=None) -> None:
        selection = self.history_table.selection()
        self.selected_history_id = selection[0] if selection else None

    def _remove_history_entry(self) -> None:
        if self.selected_history_id:
            remove_history_entry(self.selected_history_id)
            self.selected_history_id = None
            self._refresh_history()

    def _clear_history(self) -> None:
        clear_history()
        self.selected_history_id = None
        self._refresh_history()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About This Project",
            (
                "This desktop downloader was built for an Operating Systems project.\n\n"
                "Concepts demonstrated:\n"
                "- Multithreading through chunk-based workers\n"
                "- Synchronization via pause/resume and queue control\n"
                "- Shared resource coordination while merging output files\n"
                "- Task lifecycle management from queued to completed\n"
                "- Error handling and recovery with retry/cancel flows"
            ),
        )

    def _poll_ui(self) -> None:
        self._refresh_tasks()
        self._refresh_history()
        self.after(500, self._poll_ui)

    @staticmethod
    def _format_bytes(value: int | float) -> str:
        size = float(value or 0)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                return f"{size:.1f} {unit}"
            size /= 1024
        return "0 B"

    def _format_progress(self, downloaded: int, total: int) -> str:
        if total <= 0:
            return self._format_bytes(downloaded)
        return f"{(downloaded / total) * 100:.0f}%"

    def _format_speed(self, speed_bps: float | None) -> str:
        return f"{self._format_bytes(speed_bps or 0)}/s"

    @staticmethod
    def _format_eta(eta_seconds) -> str:
        if eta_seconds is None:
            return "--"
        eta_seconds = int(max(eta_seconds, 0))
        minutes, seconds = divmod(eta_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"
