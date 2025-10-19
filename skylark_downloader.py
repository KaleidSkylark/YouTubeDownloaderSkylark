import customtkinter as ctk
from customtkinter import filedialog
import threading
import tkinter as tk
import subprocess
import json
import os
import concurrent.futures
import shutil
import sys
import re
import webbrowser

# --- App Settings ---
APP_NAME = "Skylark Downloader"
APP_VERSION = "4.4"
WIDTH = 700
MIN_HEIGHT = 580 # Adjusted for new layout
MAX_HEIGHT = 900 # Expanded for more settings
# Construct the absolute path to the settings file to ensure it's always in the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(script_dir, "settings.json")

# --- FFmpeg Missing Dialog ---
class FFmpegMissingDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.transient(parent)
        self.title("FFmpeg Not Found")
        self.geometry("450x300")
        self.configure(fg_color="#1E1E1E")
        self.resizable(False, False)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(self, text="FFmpeg Installation Required", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        info_text = ("FFmpeg is a required tool for converting videos to MP3 audio files. "
                     "Please install it to use the full functionality of this application.")
        info_label = ctk.CTkLabel(self, text=info_text, wraplength=400, justify="left")
        info_label.grid(row=1, column=0, padx=20, pady=10)

        instructions_text = ("How to install:\n"
                             "1. Click the button below to download FFmpeg.\n"
                             "2. Unzip the downloaded file.\n"
                             "3. Add the 'bin' folder from the unzipped files\n    to your system's PATH environment variable.")
        instructions_label = ctk.CTkLabel(self, text=instructions_text, justify="left", font=ctk.CTkFont(family="monospace"))
        instructions_label.grid(row=2, column=0, padx=20, pady=10, sticky="w")

        download_button = ctk.CTkButton(self, text="Open FFmpeg Download Page", command=self.open_ffmpeg_link)
        download_button.grid(row=3, column=0, padx=20, pady=10)

        exit_button = ctk.CTkButton(self, text="Exit Application", command=self.close_app, fg_color="#C0392B", hover_color="#E74C3C")
        exit_button.grid(row=4, column=0, padx=20, pady=(10, 20))
        
        # Ensure closing the window via 'X' button also exits the app
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def open_ffmpeg_link(self):
        webbrowser.open("https://ffmpeg.org/download.html")

    def close_app(self):
        self.parent.destroy()

# --- Confirmation Dialog Class ---
class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(fg_color="#1E1E1E")
        self.resizable(False, False)
        self.grab_set() # Modal behavior

        self.result = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.message_label = ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14), wraplength=300)
        self.message_label.grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")

        self.no_button = ctk.CTkButton(self, text="No", command=self.on_no, fg_color="#585858", hover_color="#686868")
        self.no_button.grid(row=1, column=0, padx=(20, 10), pady=20, sticky="ew")

        self.yes_button = ctk.CTkButton(self, text="Yes", command=self.on_yes)
        self.yes_button.grid(row=1, column=1, padx=(10, 20), pady=20, sticky="ew")
    
    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()

    def wait_for_response(self):
        self.wait_window()
        return self.result

# --- Main Application Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw() # Hide window initially

        # --- Window Setup ---
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WIDTH}x{MIN_HEIGHT}")
        self.minsize(WIDTH, MIN_HEIGHT)
        self.configure(fg_color="#121212")

        # --- Theme and Appearance ---
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # --- State Variables ---
        self.download_queue = []
        self.is_downloading = False
        self.settings_visible = False
        self.default_save_path = tk.StringVar(value="No default folder selected.")
        self.last_save_path = ""

        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Queue Frame row

        # --- Header Frame ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(self.header_frame, text="Skylark Downloader", font=ctk.CTkFont(size=28, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        self.settings_button = ctk.CTkButton(self.header_frame, text="⚙", font=ctk.CTkFont(size=20), width=40, command=self.toggle_settings)
        self.settings_button.grid(row=0, column=1, sticky="e")

        # --- URL Entry Frame ---
        self.entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.entry_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        self.entry_frame.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Paste YouTube URL here (Video or Playlist)", font=ctk.CTkFont(size=14), height=40, border_width=1, corner_radius=10)
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.add_button = ctk.CTkButton(self.entry_frame, text="Add to Queue", font=ctk.CTkFont(size=14, weight="bold"), command=self.add_to_queue, height=40, corner_radius=10)
        self.add_button.grid(row=0, column=1, padx=(10, 0))

        # --- Queue Frame ---
        self.queue_container = ctk.CTkFrame(self, fg_color="transparent")
        self.queue_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.queue_container.grid_columnconfigure(0, weight=1)
        self.queue_container.grid_rowconfigure(1, weight=1)
        
        self.queue_header_frame = ctk.CTkFrame(self.queue_container, fg_color="transparent")
        self.queue_header_frame.grid(row=0, column=0, sticky="ew")
        self.queue_header_frame.grid_columnconfigure(0, weight=1)
        self.queue_label = ctk.CTkLabel(self.queue_header_frame, text="Download Queue", font=ctk.CTkFont(size=16, weight="bold"))
        self.queue_label.grid(row=0, column=0, sticky="w")
        self.clear_queue_button = ctk.CTkButton(self.queue_header_frame, text="Clear All", command=self.confirm_clear_queue, fg_color="#585858", hover_color="#686868")
        self.clear_queue_button.grid(row=0, column=1, sticky="e")
        
        self.queue_frame = ctk.CTkScrollableFrame(self.queue_container, corner_radius=10, fg_color="#1E1E1E")
        self.queue_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5,0))

        # --- Format & Quality Frame (Now always visible) ---
        self.format_quality_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.format_quality_frame.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        self.format_quality_frame.grid_columnconfigure((0, 2), weight=1)
        self._create_format_quality_widgets()

        # --- Collapsible Settings Frame ---
        self.settings_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=10)
        self.settings_frame.grid_columnconfigure(1, weight=1)
        self._create_settings_widgets()

        # --- Controls Frame ---
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.controls_frame.grid_columnconfigure(0, weight=1)
        self.progress_bar = ctk.CTkProgressBar(self.controls_frame, corner_radius=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.status_label = ctk.CTkLabel(self.controls_frame, text="Status: Initializing...", font=ctk.CTkFont(size=12), anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w")
        self.open_folder_button = ctk.CTkButton(self.controls_frame, text="Open Folder", command=self.open_last_folder)
        
        self.download_button = ctk.CTkButton(self.controls_frame, text="Start Download", font=ctk.CTkFont(size=16, weight="bold"), command=self.start_download_thread, height=45, corner_radius=10, state="disabled")
        self.download_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # --- Startup Actions ---
        self.load_settings()
        # Check dependencies after the main loop has started for stability
        self.after(100, self._check_dependencies)
    
    def _create_format_quality_widgets(self):
        """Creates format and quality widgets, now in their own dedicated frame."""
        self.format_label = ctk.CTkLabel(self.format_quality_frame, text="Format:", font=ctk.CTkFont(size=14))
        self.format_label.grid(row=0, column=0, sticky="e", padx=(0, 10))
        self.format_selector = ctk.CTkOptionMenu(self.format_quality_frame, values=["MP4 - Video", "MP3 - Audio Only"], font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8, command=self.toggle_quality_selector)
        self.format_selector.grid(row=0, column=1, sticky="w")
        
        self.quality_label = ctk.CTkLabel(self.format_quality_frame, text="Quality:", font=ctk.CTkFont(size=14))
        self.quality_label.grid(row=0, column=2, sticky="e", padx=(20, 10))
        self.quality_selector = ctk.CTkOptionMenu(self.format_quality_frame, values=["Highest", "1080p", "720p", "480p", "Lowest"], font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8)
        self.quality_selector.grid(row=0, column=3, sticky="w")
        self.toggle_quality_selector(self.format_selector.get())

    def _create_settings_widgets(self):
        """Creates all widgets for the collapsible settings panel."""
        settings_padx, settings_pady = 20, 10
        row_idx = 0

        # --- Concurrency ---
        self.concurrency_label = ctk.CTkLabel(self.settings_frame, text="Concurrent Downloads:", font=ctk.CTkFont(size=14))
        self.concurrency_label.grid(row=row_idx, column=0, padx=settings_padx, pady=(settings_pady+10, settings_pady), sticky="w")
        self.concurrency_selector = ctk.CTkOptionMenu(self.settings_frame, values=[str(i) for i in range(1, 6)], font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8)
        self.concurrency_selector.grid(row=row_idx, column=1, padx=settings_padx, pady=(settings_pady+10, settings_pady), sticky="e")
        row_idx += 1
        
        # --- Filename Prefix ---
        self.prefix_label = ctk.CTkLabel(self.settings_frame, text="Filename Prefix:", font=ctk.CTkFont(size=14))
        self.prefix_label.grid(row=row_idx, column=0, padx=settings_padx, pady=settings_pady, sticky="w")
        self.prefix_entry = ctk.CTkEntry(self.settings_frame, font=ctk.CTkFont(size=14), corner_radius=8)
        self.prefix_entry.grid(row=row_idx, column=1, padx=settings_padx, pady=settings_pady, sticky="ew")
        row_idx += 1
        self.numbering_switch = ctk.CTkSwitch(self.settings_frame, text="Add Numbering (01, 02...)", font=ctk.CTkFont(size=12))
        self.numbering_switch.grid(row=row_idx, column=1, padx=settings_padx, pady=settings_pady, sticky="w")
        row_idx += 1

        # --- Default Save Path ---
        self.default_path_label = ctk.CTkLabel(self.settings_frame, text="Default Save Folder:", font=ctk.CTkFont(size=14))
        self.default_path_label.grid(row=row_idx, column=0, padx=settings_padx, pady=settings_pady, sticky="w")
        self.select_path_button = ctk.CTkButton(self.settings_frame, text="Select Folder", command=self.select_default_path)
        self.select_path_button.grid(row=row_idx, column=1, padx=settings_padx, pady=settings_pady, sticky="e")
        row_idx += 1
        self.default_path_entry = ctk.CTkEntry(self.settings_frame, textvariable=self.default_save_path, font=ctk.CTkFont(size=12), corner_radius=8, state="readonly")
        self.default_path_entry.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=(0, settings_pady), sticky="ew")
        row_idx += 1
        self.use_default_path_switch = ctk.CTkSwitch(self.settings_frame, text="Always save to default folder (no prompt)", font=ctk.CTkFont(size=12))
        self.use_default_path_switch.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=settings_pady, sticky="w")
        row_idx += 1

        # --- Extra Options ---
        self.playlist_folder_switch = ctk.CTkSwitch(self.settings_frame, text="Create folder for playlists", font=ctk.CTkFont(size=12))
        self.playlist_folder_switch.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=settings_pady, sticky="w")
        row_idx += 1
        
        self.metadata_switch = ctk.CTkSwitch(self.settings_frame, text="Embed file metadata", font=ctk.CTkFont(size=12))
        self.metadata_switch.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=settings_pady, sticky="w")
        row_idx += 1
        
        self.thumbnail_switch = ctk.CTkSwitch(self.settings_frame, text="Embed thumbnail (for MP3)", font=ctk.CTkFont(size=12))
        self.thumbnail_switch.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=settings_pady, sticky="w")
        row_idx += 1
        
        # --- Audio Bitrate ---
        self.bitrate_label = ctk.CTkLabel(self.settings_frame, text="Audio Bitrate (MP3):", font=ctk.CTkFont(size=14))
        self.bitrate_label.grid(row=row_idx, column=0, padx=settings_padx, pady=settings_pady, sticky="w")
        self.bitrate_selector = ctk.CTkOptionMenu(self.settings_frame, values=["128K", "192K", "256K", "320K"], font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8)
        self.bitrate_selector.grid(row=row_idx, column=1, padx=settings_padx, pady=settings_pady, sticky="e")
        row_idx += 1

        # --- Actions ---
        self.update_yt_dlp_button = ctk.CTkButton(self.settings_frame, text="Update Downloader Engine (yt-dlp)", command=self.start_update_thread)
        self.update_yt_dlp_button.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=(settings_pady*2, settings_pady), sticky="ew")
        row_idx += 1
        self.save_button = ctk.CTkButton(self.settings_frame, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=row_idx, column=0, columnspan=2, padx=settings_padx, pady=(0, settings_pady+10), sticky="ew")

    def toggle_settings(self):
        if self.settings_visible:
            self.settings_frame.grid_remove()
            self.geometry(f"{WIDTH}x{MIN_HEIGHT}")
            self.settings_visible = False
        else:
            self.settings_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
            self.geometry(f"{WIDTH}x{MAX_HEIGHT}")
            self.settings_visible = True
    
    def select_default_path(self):
        path = filedialog.askdirectory()
        if path:
            self.default_save_path.set(path)
            self.update_status("Default save path selected.", "green")

    def save_settings(self):
        settings = {
            "concurrent_downloads": self.concurrency_selector.get(),
            "prefix_text": self.prefix_entry.get(),
            "add_numbering": self.numbering_switch.get(),
            "default_save_path": self.default_save_path.get(),
            "use_default_path": self.use_default_path_switch.get(),
            "create_playlist_folder": self.playlist_folder_switch.get(),
            "audio_bitrate": self.bitrate_selector.get(),
            "embed_metadata": self.metadata_switch.get(),
            "embed_thumbnail": self.thumbnail_switch.get()
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            self.update_status("Settings saved successfully!", "green")
        except Exception as e:
            self.update_status(f"Error saving settings: {e}", "red")

    def load_settings(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                self.concurrency_selector.set(settings.get("concurrent_downloads", "3"))
                self.prefix_entry.insert(0, settings.get("prefix_text", "Skylark Downloader"))
                if settings.get("add_numbering"): self.numbering_switch.select()
                self.default_save_path.set(settings.get("default_save_path", "No default folder selected."))
                if settings.get("use_default_path"): self.use_default_path_switch.select()
                if settings.get("create_playlist_folder"): self.playlist_folder_switch.select()
                self.bitrate_selector.set(settings.get("audio_bitrate", "192K"))
                if settings.get("embed_metadata"): self.metadata_switch.select()
                if settings.get("embed_thumbnail"): self.thumbnail_switch.select()
        except (json.JSONDecodeError, KeyError):
             self.update_status("Could not load settings file, using defaults.", "yellow")
        except Exception as e:
            self.update_status(f"Error loading settings: {e}", "red")
            
    def toggle_quality_selector(self, choice):
        if "Audio" in choice:
            self.quality_selector.configure(state="disabled")
        else:
            self.quality_selector.configure(state="normal")
            
    def _check_dependencies(self):
        """Checks for yt-dlp and ffmpeg on startup."""
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        if not ffmpeg_ok:
            FFmpegMissingDialog(self)
            return

        yt_dlp_ok = shutil.which("yt-dlp") is not None
        if not yt_dlp_ok:
            self.update_status("Error: yt-dlp not found. Please install it.", "red")
            self.add_button.configure(state="disabled")
            self.download_button.configure(state="disabled")
        else:
            self.update_status("Ready. Paste a URL to begin.", "green")
        
        # If all checks pass, show the main window
        self.deiconify()


    def add_to_queue(self):
        url = self.url_entry.get().strip()
        
        # --- Validation ---
        if not url:
            self.update_status("Error: Please enter a URL.", "red")
            return
        
        # More robust regex to accept videos, playlists, music, and channel URLs
        youtube_regex = r'^(https?://)?(www\.)?((music\.)?youtube\.com|youtu\.be)/.+$'
        if not re.match(youtube_regex, url):
            self.update_status("Error: Invalid YouTube URL format.", "red")
            return

        if any(item['url'] == url for item in self.download_queue):
            self.update_status("Error: This URL is already in the queue.", "yellow")
            return
        
        self.update_status("Fetching info...", "yellow")
        self.add_button.configure(state="disabled")
        threading.Thread(target=self._process_url_with_yt_dlp, args=(url,), daemon=True).start()

    def _update_ui_after_fetch(self):
        self.add_button.configure(state="normal")
        if self.download_queue and not self.is_downloading:
            self.download_button.configure(state="normal")
        else:
            self.download_button.configure(state="disabled")

    def _process_url_with_yt_dlp(self, url):
        try:
            command = ['yt-dlp', '--flat-playlist', '-j', url]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                self.update_status(f"Error: {(stderr or 'Unknown yt-dlp error').strip()}", "red")
                return
            stdout_data = (stdout or "").strip()
            if not stdout_data:
                self.update_status("Error: No video data received from URL.", "red")
                return

            videos_added = 0
            all_lines = stdout_data.split('\n')
            is_playlist = len(all_lines) > 1
            
            for line in all_lines:
                if not line: continue
                video_info = json.loads(line)
                video_entry = {
                    'title': video_info.get('title', 'Untitled'),
                    'url': video_info.get('webpage_url', video_info.get('url')),
                    'is_playlist': is_playlist,
                    'playlist_title': video_info.get('playlist_title')
                }
                self.download_queue.append(video_entry)
                self.after(0, self._add_queue_item_ui, video_entry['title'], video_entry['url'])
                videos_added += 1
            self.update_status(f"Added {videos_added} item(s) to the queue.", "green")
        except Exception as e:
            self.update_status(f"Error processing URL: {e}", "red")
        finally:
            self.after(10, self._update_ui_after_fetch)

    def _add_queue_item_ui(self, title, url):
        def remove_item(item_frame, item_url):
            self.download_queue[:] = [item for item in self.download_queue if item['url'] != item_url]
            item_frame.destroy()
            if not self.download_queue: self.download_button.configure(state="disabled")
        item_frame = ctk.CTkFrame(self.queue_frame, corner_radius=8, fg_color="#333333")
        item_frame.pack(fill="x", padx=5, pady=(0, 5))
        label = ctk.CTkLabel(item_frame, text=title, wraplength=500, justify="left", anchor="w")
        label.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        remove_button = ctk.CTkButton(item_frame, text="✕", font=ctk.CTkFont(size=16), width=30, height=30, command=lambda f=item_frame, u=url: remove_item(f, u), fg_color="#C0392B", hover_color="#E74C3C")
        remove_button.pack(side="right", padx=10)

    def start_download_thread(self):
        if self.is_downloading: return
        if not self.download_queue:
            self.update_status("Error: Download queue is empty.", "red")
            return
        self.open_folder_button.grid_remove() # Hide button before download
        threading.Thread(target=self.download_process_with_yt_dlp, daemon=True).start()
        
    def start_update_thread(self):
        self.update_yt_dlp_button.configure(state="disabled")
        threading.Thread(target=self._run_yt_dlp_update, daemon=True).start()

    def _run_yt_dlp_update(self):
        self.update_status("Updating yt-dlp...", "yellow")
        try:
            command = ['yt-dlp', '-U']
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if process.returncode == 0:
                self.update_status("yt-dlp updated successfully!" if "Updating to" in process.stdout else "yt-dlp is already up to date.", "green")
            else:
                self.update_status(f"Update failed: {process.stderr.strip()}", "red")
        except Exception as e:
            self.update_status(f"An error occurred: {e}", "red")
        finally:
            self.update_yt_dlp_button.configure(state="normal")

    def download_process_with_yt_dlp(self):
        self.is_downloading = True
        self.download_button.configure(state="disabled", text="Downloading...")
        self.progress_bar.set(0)
        
        save_path = ""
        use_default = self.use_default_path_switch.get() == 1
        default_path = self.default_save_path.get()
        
        if use_default and os.path.isdir(default_path):
            save_path = default_path
        else:
            save_path = filedialog.askdirectory()

        if not save_path:
            self.update_status("Download cancelled: No folder selected.", "yellow")
            self.is_downloading = False
            self._update_ui_after_fetch()
            self.download_button.configure(text="Start Download")
            return
        
        self.last_save_path = save_path

        queue_copy = list(self.download_queue)
        with concurrent.futures.ThreadPoolExecutor(max_workers=int(self.concurrency_selector.get())) as executor:
            futures = {executor.submit(self._download_single_video, item, save_path, idx): item for idx, item in enumerate(queue_copy)}
            completed_count = 0
            for future in concurrent.futures.as_completed(futures):
                completed_count += 1
                self.after(0, self.update_overall_progress, completed_count, len(queue_copy))
        
        self.is_downloading = False
        self.download_queue.clear()
        self.after(0, self._clear_queue_ui)
        self.download_button.configure(text="Start Download", state="disabled")
        self.update_status("All downloads completed!", "green")
        self.open_folder_button.grid(row=1, column=1, sticky="e")

    def open_last_folder(self):
        if self.last_save_path and os.path.isdir(self.last_save_path):
            try:
                if sys.platform == "win32":
                    os.startfile(self.last_save_path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", self.last_save_path])
                else:
                    subprocess.Popen(["xdg-open", self.last_save_path])
            except Exception as e:
                self.update_status(f"Error opening folder: {e}", "red")

    def confirm_clear_queue(self):
        if not self.download_queue: return
        dialog = ConfirmationDialog(self, title="Confirm", message="Are you sure you want to clear the entire queue?")
        if dialog.wait_for_response():
            self.clear_queue()

    def clear_queue(self):
        self.download_queue.clear()
        self._clear_queue_ui()
        self.download_button.configure(state="disabled")
        self.update_status("Queue cleared.", "yellow")

    def _clear_queue_ui(self):
        for widget in self.queue_frame.winfo_children():
            widget.destroy()

    def update_overall_progress(self, completed, total):
        self.progress_bar.set(completed / total)
        self.update_status(f"Downloading... ({completed}/{total}) complete")

    def _download_single_video(self, video_item, save_path, idx):
        try:
            command = self._build_yt_dlp_command(video_item, save_path, idx)
            subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.strip()
            print(f"--- yt-dlp Error Output for {video_item['title']} ---\n{error_output}\n---------------------------------")
            error_message = f"Download failed for {video_item['title'][:30]}... See console."
            if "ffmpeg" in error_output.lower() and "not found" in error_output.lower():
                error_message = "Error: FFmpeg not. It's required for MP3 conversion."
            self.update_status(error_message, "red")

    def _build_yt_dlp_command(self, video_item, save_path, idx):
        prefix = self.prefix_entry.get().strip()
        filename_prefix = f"[{prefix}] " if prefix else ""
        
        number_prefix = f"{idx + 1:02d} - " if self.numbering_switch.get() == 1 else ""
        
        # Build base filename
        filename = f"{number_prefix}{filename_prefix}%(title)s"
        
        # Determine final save path
        final_save_path = save_path
        if self.playlist_folder_switch.get() == 1 and video_item.get('is_playlist') and video_item.get('playlist_title'):
             # Sanitize playlist title to be a valid folder name
            sane_playlist_title = "".join(i for i in video_item['playlist_title'] if i not in r'\/:*?"<>|')
            final_save_path = os.path.join(save_path, sane_playlist_title)

        # Build command based on format
        if "Audio" in self.format_selector.get():
            output_template = os.path.join(final_save_path, f"{filename}.%(ext)s")
            audio_bitrate = self.bitrate_selector.get()
            command = ['yt-dlp', '-x', '--audio-format', 'mp3', '-f', 'bestaudio', '--audio-quality', audio_bitrate]
            if self.thumbnail_switch.get() == 1:
                command.append('--embed-thumbnail')
        else: # Video
            quality_tag = self.quality_selector.get()
            filename += f" - {quality_tag}"
            output_template = os.path.join(final_save_path, f"{filename}.%(ext)s")
            quality_map = {
                "Highest": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
                "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
                "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
                "Lowest": "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst",
            }
            command = ['yt-dlp', '-f', quality_map.get(quality_tag, quality_map["Highest"]), '--merge-output-format', 'mp4']

        if self.metadata_switch.get() == 1:
            command.append('--add-metadata')
        
        command.extend(['--no-progress', '--no-warnings', '-o', output_template, video_item['url']])
        return command

    def update_status(self, message, color="white"):
        color_map = {"red": "#E74C3C", "green": "#2ECC71", "yellow": "#F1C40F", "white": "white"}
        self.after(0, lambda: self.status_label.configure(text=f"Status: {message}", text_color=color_map.get(color, "white")))

# --- Run Application ---
if __name__ == "__main__":
    app = App()
    app.mainloop()

