import customtkinter as ctk
from customtkinter import filedialog, CTkImage
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
from typing import List, Dict, Any
from PIL import Image
import requests
from io import BytesIO

class AppConfig:
    NAME = "Skylark Downloader"
    VERSION = "6.1"
    WIDTH = 700
    MIN_HEIGHT = 580
    MAX_HEIGHT = 900
    STATE_NORMAL = "normal"
    STATE_DISABLED = "disabled"
    STATE_READONLY = "readonly"
    COLOR_MAP = {
        "red": "#E74C3C", "green": "#2ECC71", "yellow": "#F1C40F",
        "white": "white", "disabled": "gray50"
    }
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    SETTINGS_FILE = os.path.join(SCRIPT_DIR, "settings.json")
    LANGUAGE_OPTIONS = [
        "English (en)", "Spanish (es)", "French (fr)", "German (de)",
        "Japanese (ja)", "Korean (ko)", "Chinese (zh)", "Russian (ru)",
        "Portuguese (pt)", "Italian (it)", "Arabic (ar)", "Hindi (hi)"
    ]
    QUALITY_MAP = {
        "Highest": ("bestvideo", "bestaudio"), "1080p": ("bestvideo[height<=1080]", "bestaudio"),
        "720p": ("bestvideo[height<=720]", "bestaudio"), "480p": ("bestvideo[height<=480]", "bestaudio"),
        "Lowest": ("worstvideo", "worstaudio"),
    }

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

        ctk.CTkLabel(self, text="FFmpeg Installation Required", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        info_text = "FFmpeg is required for converting videos to MP3s. Please install it to enable full functionality."
        ctk.CTkLabel(self, text=info_text, wraplength=400, justify="left").grid(row=1, column=0, padx=20, pady=10)
        instructions_text = ("How to install:\n1. Click the button below to open the download page.\n2. Unzip the downloaded file.\n3. Add the 'bin' folder to your system's PATH.")
        ctk.CTkLabel(self, text=instructions_text, justify="left", font=ctk.CTkFont(family="monospace")).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        ctk.CTkButton(self, text="Open FFmpeg Download Page", command=self.open_ffmpeg_link).grid(row=3, column=0, padx=20, pady=10)
        ctk.CTkButton(self, text="Exit Application", command=self.close_app, fg_color="#C0392B", hover_color="#E74C3C").grid(row=4, column=0, padx=20, pady=(10, 20))
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def open_ffmpeg_link(self):
        webbrowser.open("https://ffmpeg.org/download.html")

    def close_app(self):
        self.parent.destroy()

class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)
        self.transient(parent)
        self.title(title)
        self.geometry("350x150")
        self.configure(fg_color="#1E1E1E")
        self.resizable(False, False)
        self.grab_set()
        self.result = False
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self, text=message, font=ctk.CTkFont(size=14), wraplength=300).grid(row=0, column=0, columnspan=2, padx=20, pady=20, sticky="ew")
        ctk.CTkButton(self, text="No", command=self.on_no, fg_color="#585858", hover_color="#686868").grid(row=1, column=0, padx=(20, 10), pady=20, sticky="ew")
        ctk.CTkButton(self, text="Yes", command=self.on_yes).grid(row=1, column=1, padx=(10, 20), pady=20, sticky="ew")
    
    def on_yes(self):
        self.result = True
        self.destroy()

    def on_no(self):
        self.result = False
        self.destroy()

    def wait_for_response(self) -> bool:
        self.wait_window()
        return self.result

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#3E3E3E", relief='solid', borderwidth=1,
                         wraplength=200, foreground="white", font=("Arial", 10, "normal"))
        label.pack(ipadx=2, ipady=2)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.download_queue: List[Dict[str, Any]] = []
        self.is_downloading = False
        self.settings_visible = False
        self.last_save_path = ""
        self.default_save_path = tk.StringVar(value="No default folder selected.")
        
        self.title(f"{AppConfig.NAME} v{AppConfig.VERSION}")
        self.geometry(f"{AppConfig.WIDTH}x{AppConfig.MIN_HEIGHT}")
        self.minsize(AppConfig.WIDTH, AppConfig.MIN_HEIGHT)
        self.configure(fg_color="#121212")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._create_header_widgets()
        self._create_url_entry_widgets()
        self._create_queue_widgets()
        self._create_settings_panel()
        self._create_format_quality_widgets()
        self._create_controls_widgets()

        self.load_settings()
        self.after(100, self._check_dependencies)

    def _create_header_widgets(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text=AppConfig.NAME, font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header_frame, text="Note: Best use is to have VPN to avoid ERROR:Sign in/Not Robot/Age-restricted",
                     font=ctk.CTkFont(size=10, slant="italic")).grid(row=1, column=0, columnspan=2, pady=(5, 0), sticky="w")
        ctk.CTkButton(header_frame, text="⚙", font=ctk.CTkFont(size=20), width=40, command=self.toggle_settings).grid(row=0, column=1, sticky="e")

    def _create_url_entry_widgets(self):
        entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        entry_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        entry_frame.grid_columnconfigure(0, weight=1)
        self.url_entry = ctk.CTkEntry(entry_frame, placeholder_text="Paste YouTube URL here (Video or Playlist)", font=ctk.CTkFont(size=14), height=40, border_width=1, corner_radius=10)
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self.add_button = ctk.CTkButton(entry_frame, text="Add to Queue", font=ctk.CTkFont(size=14, weight="bold"), command=self.add_to_queue, height=40, corner_radius=10)
        self.add_button.grid(row=0, column=1, padx=(10, 0))

    def _create_queue_widgets(self):
        queue_container = ctk.CTkFrame(self, fg_color="transparent")
        queue_container.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        queue_container.grid_columnconfigure(0, weight=1)
        queue_container.grid_rowconfigure(1, weight=1)
        
        queue_header_frame = ctk.CTkFrame(queue_container, fg_color="transparent")
        queue_header_frame.grid(row=0, column=0, sticky="ew")
        queue_header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(queue_header_frame, text="Download Queue", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(queue_header_frame, text="Clear All", command=self.confirm_clear_queue, fg_color="#585858", hover_color="#686868").grid(row=0, column=1, sticky="e")
        
        self.queue_frame = ctk.CTkScrollableFrame(queue_container, corner_radius=10, fg_color="#1E1E1E")
        self.queue_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(5, 0))

    def _create_format_quality_widgets(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=3, column=0, padx=20, pady=0, sticky="ew")
        frame.grid_columnconfigure((0, 2), weight=1)
        
        ctk.CTkLabel(frame, text="Format:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, sticky="e", padx=(0, 10))
        self.format_selector = ctk.CTkOptionMenu(frame, values=["MP4 - Video", "MP3 - Audio Only"], font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8, command=self.toggle_quality_selector)
        self.format_selector.grid(row=0, column=1, sticky="w")
        
        self.quality_label = ctk.CTkLabel(frame, text="Quality:", font=ctk.CTkFont(size=14))
        self.quality_label.grid(row=0, column=2, sticky="e", padx=(20, 10))
        self.quality_selector = ctk.CTkOptionMenu(frame, values=list(AppConfig.QUALITY_MAP.keys()), font=ctk.CTkFont(size=14), dropdown_font=ctk.CTkFont(size=14), corner_radius=8)
        self.quality_selector.grid(row=0, column=3, sticky="w")
        self.toggle_quality_selector(self.format_selector.get())

    def _create_controls_widgets(self):
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="ew")
        controls_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_bar = ctk.CTkProgressBar(controls_frame, corner_radius=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(controls_frame, text="Status: Initializing...", font=ctk.CTkFont(size=12), anchor="w")
        self.status_label.grid(row=1, column=0, sticky="w")
        
        self.open_folder_button = ctk.CTkButton(controls_frame, text="Open Folder", command=self.open_last_folder)
        
        self.download_button = ctk.CTkButton(controls_frame, text="Start Download", font=ctk.CTkFont(size=16, weight="bold"), command=self.start_download_thread, height=45, corner_radius=10, state=AppConfig.STATE_DISABLED)
        self.download_button.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _create_settings_panel(self):
        self.settings_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=10)
        self.settings_frame.grid_columnconfigure((0, 1), weight=1)
        padx, pady = (10, 10), (0, 8)

        left = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        left.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="new")
        left.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(left, text="File & Naming", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(5, 10), sticky="w")
        ctk.CTkLabel(left, text="Filename Prefix:", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=padx, pady=pady, sticky="w")
        self.prefix_entry = ctk.CTkEntry(left, font=ctk.CTkFont(size=12), corner_radius=8)
        self.prefix_entry.grid(row=1, column=1, padx=padx, pady=pady, sticky="ew")
        self.numbering_switch = ctk.CTkSwitch(left, text="Add Numbering (01, 02...)", font=ctk.CTkFont(size=12))
        self.numbering_switch.grid(row=2, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")
        self.playlist_folder_switch = ctk.CTkSwitch(left, text="Create folder for playlists", font=ctk.CTkFont(size=12))
        self.playlist_folder_switch.grid(row=3, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")
        
        ctk.CTkLabel(left, text="Save Location", font=ctk.CTkFont(size=14, weight="bold")).grid(row=4, column=0, columnspan=2, pady=(15, 10), sticky="w")
        ctk.CTkButton(left, text="Select Default Folder", command=self.select_default_path, font=ctk.CTkFont(size=12)).grid(row=5, column=0, columnspan=2, padx=padx, pady=pady, sticky="ew")
        ctk.CTkEntry(left, textvariable=self.default_save_path, font=ctk.CTkFont(size=12), corner_radius=8, state=AppConfig.STATE_READONLY).grid(row=6, column=0, columnspan=2, padx=padx, pady=(0, pady[1]), sticky="ew")
        self.use_default_path_switch = ctk.CTkSwitch(left, text="Always save to default (no prompt)", font=ctk.CTkFont(size=12))
        self.use_default_path_switch.grid(row=7, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")
        
        right = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        right.grid(row=0, column=1, padx=(5, 10), pady=5, sticky="new")
        right.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(right, text="Download & Format", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(5, 10), sticky="w")
        ctk.CTkLabel(right, text="Concurrent Jobs:", font=ctk.CTkFont(size=12)).grid(row=1, column=0, padx=padx, pady=pady, sticky="w")
        self.concurrency_selector = ctk.CTkOptionMenu(right, values=[str(i) for i in range(1, 6)], font=ctk.CTkFont(size=12), dropdown_font=ctk.CTkFont(size=12), corner_radius=8, width=80)
        self.concurrency_selector.grid(row=1, column=1, padx=padx, pady=pady, sticky="e")
        ctk.CTkLabel(right, text="Audio Bitrate (MP3):", font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=padx, pady=pady, sticky="w")
        self.bitrate_selector = ctk.CTkOptionMenu(right, values=["128K", "192K", "256K", "320K"], font=ctk.CTkFont(size=12), dropdown_font=ctk.CTkFont(size=12), corner_radius=8, width=80)
        self.bitrate_selector.grid(row=2, column=1, padx=padx, pady=pady, sticky="e")
        self.metadata_switch = ctk.CTkSwitch(right, text="Embed file metadata", font=ctk.CTkFont(size=12))
        self.metadata_switch.grid(row=3, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")
        
        ctk.CTkLabel(right, text="Note: Recommended to keep on.", font=ctk.CTkFont(size=10, slant="italic")).grid(row=4, column=0, columnspan=2, padx=(padx[0]+20, padx[1]), pady=(0, pady[1]), sticky="w")

        self.thumbnail_switch = ctk.CTkSwitch(right, text="Embed thumbnail (for MP3)", font=ctk.CTkFont(size=12))
        self.thumbnail_switch.grid(row=5, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")

        ctk.CTkLabel(right, text="Subtitles", font=ctk.CTkFont(size=14, weight="bold")).grid(row=6, column=0, columnspan=2, pady=(15, 10), sticky="w")
        self.subtitle_switch = ctk.CTkSwitch(right, text="Download subtitle if available", font=ctk.CTkFont(size=12), command=self._toggle_subtitle_options)
        self.subtitle_switch.grid(row=7, column=0, columnspan=2, padx=padx, pady=pady, sticky="w")
        self.subtitle_all_switch = ctk.CTkSwitch(right, text="Download all languages", font=ctk.CTkFont(size=12), command=lambda: self._toggle_lang_selector(self.subtitle_all_switch, self.subtitle_lang_selector, parent_enabled=self.subtitle_switch.get()))
        self.subtitle_all_switch.grid(row=8, column=0, columnspan=2, padx=(padx[0] + 20, padx[1]), pady=pady, sticky="w")
        self.srt_caution_label = ctk.CTkLabel(right, text="Note: Embeds best with VLC.", font=ctk.CTkFont(size=10, slant="italic"))
        self.srt_caution_label.grid(row=9, column=0, columnspan=2, padx=(padx[0] + 20, padx[1]), pady=(0, pady[1]), sticky="w")
        ctk.CTkLabel(right, text="Language:", font=ctk.CTkFont(size=12)).grid(row=10, column=0, padx=(padx[0] + 20, padx[1]), pady=pady, sticky="w")
        self.subtitle_lang_selector = ctk.CTkOptionMenu(right, font=ctk.CTkFont(size=12), corner_radius=8, values=AppConfig.LANGUAGE_OPTIONS, dropdown_font=ctk.CTkFont(size=12))
        self.subtitle_lang_selector.grid(row=10, column=1, padx=padx, pady=pady, sticky="ew")

        action_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        action_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        self.update_yt_dlp_button = ctk.CTkButton(action_frame, text="Update Downloader Engine (yt-dlp)", command=self.start_update_thread)
        self.update_yt_dlp_button.grid(row=0, column=0, columnspan=2, padx=padx, pady=(pady[1] * 2, pady[1]), sticky="ew")
        ctk.CTkButton(action_frame, text="Save Settings", command=self.save_settings).grid(row=1, column=0, columnspan=2, padx=padx, pady=(0, pady[1] + 5), sticky="ew")

    def toggle_settings(self):
        if self.settings_visible:
            self.settings_frame.grid_remove()
            self.geometry(f"{AppConfig.WIDTH}x{AppConfig.MIN_HEIGHT}")
        else:
            self.settings_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
            self.geometry(f"{AppConfig.WIDTH}x{AppConfig.MAX_HEIGHT}")
        self.settings_visible = not self.settings_visible

    def toggle_quality_selector(self, choice: str):
        is_video = "Audio" not in choice
        self.quality_selector.configure(state=AppConfig.STATE_NORMAL if is_video else AppConfig.STATE_DISABLED)
        
        self.subtitle_switch.configure(state=AppConfig.STATE_NORMAL if is_video else AppConfig.STATE_DISABLED)
        if not is_video:
            self.subtitle_switch.deselect()
        
        self._toggle_subtitle_options()

    def _toggle_subtitle_options(self):
        is_video = "Audio" not in self.format_selector.get()
        is_enabled = self.subtitle_switch.get() == 1 and is_video

        state = AppConfig.STATE_NORMAL if is_enabled else AppConfig.STATE_DISABLED
        color = AppConfig.COLOR_MAP["white"] if is_enabled else AppConfig.COLOR_MAP["disabled"]
        
        self.subtitle_all_switch.configure(state=state)
        self.srt_caution_label.configure(state=state, text_color=color)
        
        if not is_enabled:
             self.subtitle_all_switch.deselect()

        self._toggle_lang_selector(self.subtitle_all_switch, self.subtitle_lang_selector, parent_enabled=is_enabled)
        
    def _toggle_lang_selector(self, all_switch: ctk.CTkSwitch, lang_selector: ctk.CTkOptionMenu, parent_enabled: bool = True):
        is_all = all_switch.get() == 1
        if parent_enabled and not is_all:
            lang_selector.configure(state=AppConfig.STATE_NORMAL)
        else:
            lang_selector.configure(state=AppConfig.STATE_DISABLED)
            
    def _check_dependencies(self):
        if not shutil.which("ffmpeg"):
            FFmpegMissingDialog(self)
            return
        if not shutil.which("yt-dlp"):
            self.update_status("Error: yt-dlp not found. Please install it.", "red")
            self.add_button.configure(state=AppConfig.STATE_DISABLED)
        else:
            self.update_status("Ready. Paste a URL to begin.", "green")
        self.deiconify()

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
            "embed_thumbnail": self.thumbnail_switch.get(),
            "download_subtitles": self.subtitle_switch.get(),
            "download_all_subtitles": self.subtitle_all_switch.get(),
            "subtitle_lang": self.subtitle_lang_selector.get(),
            "quality": self.quality_selector.get(),
        }
        try:
            with open(AppConfig.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            self.update_status("Settings saved successfully!", "green")
        except IOError as e:
            self.update_status(f"Error saving settings: {e}", "red")

    def load_settings(self):
        try:
            if not os.path.exists(AppConfig.SETTINGS_FILE):
                return
            with open(AppConfig.SETTINGS_FILE, 'r') as f:
                settings = json.load(f)

            def apply_setting(widget, key, default):
                value = settings.get(key, default)
                if isinstance(widget, (ctk.CTkOptionMenu, tk.StringVar)):
                    widget.set(value)
                elif isinstance(widget, ctk.CTkEntry):
                    widget.delete(0, 'end')
                    widget.insert(0, value)
                elif isinstance(widget, ctk.CTkSwitch):
                    if value: widget.select()
                    else: widget.deselect()

            apply_setting(self.concurrency_selector, "concurrent_downloads", "3")
            apply_setting(self.prefix_entry, "prefix_text", "Skylark")
            apply_setting(self.numbering_switch, "add_numbering", False)
            apply_setting(self.default_save_path, "default_save_path", "No default folder selected.")
            apply_setting(self.use_default_path_switch, "use_default_path", False)
            apply_setting(self.playlist_folder_switch, "create_playlist_folder", True)
            apply_setting(self.bitrate_selector, "audio_bitrate", "192K")
            apply_setting(self.metadata_switch, "embed_metadata", True)
            apply_setting(self.thumbnail_switch, "embed_thumbnail", True)
            apply_setting(self.subtitle_switch, "download_subtitles", False)
            apply_setting(self.subtitle_all_switch, "download_all_subtitles", False)
            apply_setting(self.subtitle_lang_selector, "subtitle_lang", "English (en)")
            apply_setting(self.quality_selector, "quality", "1080p")
        except (json.JSONDecodeError, KeyError):
            self.update_status("Settings file corrupted, using defaults.", "yellow")
        except Exception as e:
            self.update_status(f"Error loading settings: {e}", "red")
        
        self._toggle_subtitle_options()

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_status("Error: Please enter a URL.", "red")
            return
        
        youtube_regex = r'^(https?://)?(www\.)?((music\.)?youtube\.com|youtu\.be)/.+$'
        if not re.match(youtube_regex, url):
            self.update_status("Error: Invalid YouTube URL format.", "red")
            return

        # Simple check to prevent adding the same playlist/video while it's being fetched
        if self.add_button.cget('state') == AppConfig.STATE_DISABLED:
            return
        
        self.update_status("Fetching info...", "yellow")
        self.add_button.configure(state=AppConfig.STATE_DISABLED)
        threading.Thread(target=self._fetch_url_metadata, args=(url,), daemon=True).start()

    def _fetch_url_metadata(self, url: str):
        """
        Fetches metadata from a URL.
        For playlists, it uses --flat-playlist for a very fast initial list,
        then fetches detailed metadata for each video in the background.
        For single videos, it fetches all data in one go.
        """
        try:
            command = ['yt-dlp', '-j', '--flat-playlist', '--ignore-errors', '--no-warnings', url]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            video_entries_to_process = []
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    try:
                        video_entries_to_process.append(json.loads(line))
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse JSON line: {line}")
            
            self.after(0, self._process_and_add_entries, video_entries_to_process)

            process.stdout.close()
            return_code = process.wait()
            stderr_output = process.stderr.read()
            process.stderr.close()

            if return_code != 0 and not video_entries_to_process:
                last_error = stderr_output.strip().splitlines()[-1] if stderr_output else "Unknown yt-dlp error."
                self.after(0, self.update_status, f"Error: {last_error}", "red")

        except FileNotFoundError:
            self.after(0, self.update_status, "Error: yt-dlp not found.", "red")
        except Exception as e:
            self.after(0, self.update_status, f"An unexpected error occurred: {e}", "red")
        finally:
            self.after(10, self._update_ui_after_fetch)
    
    def _process_and_add_entries(self, entries: List[Dict[str, Any]]):
        """Processes the fetched entries and adds them to the queue and UI."""
        if not entries:
            self.update_status("No videos found at the URL.", "yellow")
            return

        is_playlist = len(entries) > 1 or 'entries' in entries[0]
        items_added = 0
        skipped_count = 0

        for info in entries:
            # Filter out private or deleted videos based on their title
            if info.get('title') in ["[Deleted video]", "[Private video]"]:
                skipped_count += 1
                continue

            # Check for duplicates before adding
            url = info.get('webpage_url', info.get('url'))
            if any(item['url'] == url for item in self.download_queue):
                continue
            
            needs_details = 'duration' not in info

            thumbnail_url = info.get('thumbnail')
            if not needs_details:
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    best_thumb = next((t['url'] for t in reversed(thumbnails) if t.get('width', 0) and t['width'] <= 480), None)
                    if best_thumb:
                        thumbnail_url = best_thumb
                    elif thumbnails:
                        thumbnail_url = thumbnails[-1].get('url')

            video_entry = {
                'url': url,
                'title': info.get('title', 'Untitled'),
                'playlist_title': info.get('playlist_title'),
                'uploader': info.get('uploader', 'N/A'),
                'subtitles': sorted(list(info.get('subtitles', {}).keys())),
                'thumbnail_url': thumbnail_url,
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'needs_details': needs_details
            }
            self.download_queue.append(video_entry)
            self._add_queue_item_ui(video_entry)
            items_added += 1

        if items_added > 0:
            status_msg = f"Added {items_added} item(s) to the queue."
            if is_playlist:
                if any(e.get('needs_details') for e in self.download_queue):
                    status_msg += " Fetching details in background..."
                if skipped_count > 0:
                    status_msg += f" (Skipped {skipped_count} private/deleted)"
            self.update_status(status_msg, "green")
            self.url_entry.delete(0, 'end')
        else:
            self.update_status("URL already in queue or no new items found.", "yellow")

    def _fetch_and_update_details(self, item_data: Dict[str, Any], item_frame: ctk.CTkFrame):
        """Fetches full metadata for a single item and schedules a UI update."""
        try:
            command = ['yt-dlp', '-j', item_data['url']]
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if process.returncode != 0:
                print(f"Failed to fetch details for {item_data['url']}: {process.stderr}")
                self.after(0, lambda: item_frame.uploader_label.configure(text="Error fetching details."))
                return

            info = json.loads(process.stdout)

            thumbnail_url = info.get('thumbnail')
            thumbnails = info.get('thumbnails', [])
            if thumbnails:
                best_thumb = next((t['url'] for t in reversed(thumbnails) if t.get('width', 0) and t['width'] <= 480), None)
                if best_thumb:
                    thumbnail_url = best_thumb
                elif thumbnails:
                    thumbnail_url = thumbnails[-1].get('url')

            item_data.update({
                'uploader': info.get('uploader', 'N/A'),
                'subtitles': sorted(list(info.get('subtitles', {}).keys())),
                'thumbnail_url': thumbnail_url,
                'duration': info.get('duration', 0),
                'view_count': info.get('view_count', 0),
                'needs_details': False
            })

            self.after(0, self._update_queue_item_ui, item_data, item_frame)
        except Exception as e:
            print(f"Exception fetching details for {item_data['url']}: {e}")
            self.after(0, lambda: item_frame.uploader_label.configure(text="Error processing details."))
    
    def _update_queue_item_ui(self, item_data: Dict[str, Any], item_frame: ctk.CTkFrame):
        """Updates a specific queue item's UI with new data. Must be called from the main thread."""
        item_frame.uploader_label.configure(text=item_data['uploader'])
        item_frame.duration_label.configure(text=f"🕒 {self._format_duration(item_data.get('duration', 0))}")
        item_frame.views_label.configure(text=f"👁️ {self._format_views(item_data.get('view_count', 0))}")
        
        if item_data.get('thumbnail_url'):
            threading.Thread(target=self._load_thumbnail, args=(item_frame.thumbnail_label, item_data['thumbnail_url']), daemon=True).start()
        else:
            item_frame.thumbnail_label.configure(text="No Thumbnail", image=None)


        if hasattr(item_frame, 'sub_indicator'):
            item_frame.sub_indicator.destroy()
            delattr(item_frame, 'sub_indicator')
            
        if item_data.get('subtitles'):
            info_frame = item_frame.views_label.master
            sub_indicator = ctk.CTkLabel(info_frame, text="S", font=ctk.CTkFont(size=11, weight="bold"), text_color="white", fg_color="#555555", corner_radius=5, width=20, height=20)
            sub_indicator.pack(side="left", padx=(10,0), anchor="w")
            tooltip_text = "Available Subtitles:\n" + "\n".join(item_data['subtitles'])
            Tooltip(sub_indicator, tooltip_text)
            item_frame.sub_indicator = sub_indicator

    def _add_queue_item_ui(self, item_data: Dict[str, Any]):
        item_frame = ctk.CTkFrame(self.queue_frame, corner_radius=8, fg_color="#333333")
        item_frame.pack(fill="x", padx=5, pady=(0, 5))
        item_frame.grid_columnconfigure(1, weight=1)

        thumbnail_label = ctk.CTkLabel(item_frame, text="Loading...", width=120, height=68, fg_color="#2b2b2b", corner_radius=6)
        thumbnail_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        item_frame.thumbnail_label = thumbnail_label

        details_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        details_frame.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="new")
        details_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(details_frame, text=item_data['title'], wraplength=420, justify="left", anchor="w", font=ctk.CTkFont(size=14, weight="bold"))
        title_label.grid(row=0, column=0, sticky="ew")

        uploader_label = ctk.CTkLabel(details_frame, text=item_data['uploader'], justify="left", anchor="w", font=ctk.CTkFont(size=12), text_color="gray")
        uploader_label.grid(row=1, column=0, sticky="w", pady=(2, 0))
        item_frame.uploader_label = uploader_label

        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="sew")

        duration_str = self._format_duration(item_data.get('duration', 0))
        views_str = self._format_views(item_data.get('view_count', 0))

        duration_label = ctk.CTkLabel(info_frame, text=f"🕒 {duration_str}", font=ctk.CTkFont(size=12))
        duration_label.pack(side="left", anchor="w")
        item_frame.duration_label = duration_label

        views_label = ctk.CTkLabel(info_frame, text=f"👁️ {views_str}", font=ctk.CTkFont(size=12))
        views_label.pack(side="left", padx=(10, 0), anchor="w")
        item_frame.views_label = views_label

        if item_data.get('needs_details', False):
            uploader_label.configure(text="Fetching details...")
            duration_label.configure(text="🕒 --:--")
            views_label.configure(text="👁️ --")
            threading.Thread(target=self._fetch_and_update_details, args=(item_data, item_frame), daemon=True).start()
        else:
            if item_data.get('thumbnail_url'):
                threading.Thread(target=self._load_thumbnail, args=(thumbnail_label, item_data['thumbnail_url']), daemon=True).start()
            if item_data.get('subtitles'):
                sub_indicator = ctk.CTkLabel(info_frame, text="S", font=ctk.CTkFont(size=11, weight="bold"), text_color="white", fg_color="#555555", corner_radius=5, width=20, height=20)
                sub_indicator.pack(side="left", padx=(10,0), anchor="w")
                tooltip_text = "Available Subtitles:\n" + "\n".join(item_data['subtitles'])
                Tooltip(sub_indicator, tooltip_text)
                item_frame.sub_indicator = sub_indicator

        remove_button = ctk.CTkButton(item_frame, text="✕", font=ctk.CTkFont(size=16), width=30, height=30, fg_color="#C0392B", hover_color="#E74C3C")
        remove_button.configure(command=lambda f=item_frame, u=item_data['url']: self._remove_queue_item(f, u))
        remove_button.grid(row=0, column=2, rowspan=2, padx=10, pady=10)

    def _load_thumbnail(self, label_widget: ctk.CTkLabel, url: str):
        try:
            if url.startswith('//'):
                url = 'https:' + url

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            with requests.get(url, stream=True, timeout=10, headers=headers) as r:
                r.raise_for_status()
                img_data = r.content
            
            pil_image = Image.open(BytesIO(img_data))
            ctk_image = CTkImage(pil_image, size=(120, 68))
            
            def update_ui_with_thumbnail():
                if label_widget.winfo_exists():
                    label_widget.configure(image=ctk_image, text="")
                    label_widget.image = ctk_image

            self.after(0, update_ui_with_thumbnail)
            
        except requests.exceptions.RequestException as e:
            print(f"Network error loading thumbnail: {e}")
            self.after(0, lambda: label_widget.configure(text="Network Error", image=None) if label_widget.winfo_exists() else None)
        except Exception as e:
            print(f"Error processing thumbnail: {e}")
            self.after(0, lambda: label_widget.configure(text="No Thumbnail", image=None) if label_widget.winfo_exists() else None)

    def _format_duration(self, seconds: int) -> str:
        if not isinstance(seconds, (int, float)) or seconds < 0: return "N/A"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        if hours > 0: return f"{hours:d}:{minutes:02d}:{seconds:02d}"
        else: return f"{minutes:02d}:{seconds:02d}"

    def _format_views(self, views: int) -> str:
        if not isinstance(views, (int, float)) or views < 0: return "N/A"
        views = int(views)
        if views < 1000: return str(views)
        elif views < 1_000_000: return f"{views / 1000:.1f}K"
        elif views < 1_000_000_000: return f"{views / 1_000_000:.1f}M"
        else: return f"{views / 1_000_000_000:.1f}B"

    def _remove_queue_item(self, item_frame: ctk.CTkFrame, url: str):
        self.download_queue = [item for item in self.download_queue if item['url'] != url]
        item_frame.destroy()
        if not self.download_queue:
            self.download_button.configure(state=AppConfig.STATE_DISABLED)

    def confirm_clear_queue(self):
        if not self.download_queue: return
        dialog = ConfirmationDialog(self, title="Confirm", message="Are you sure you want to clear the entire queue?")
        if dialog.wait_for_response():
            self.download_queue.clear()
            for widget in self.queue_frame.winfo_children():
                widget.destroy()
            self.download_button.configure(state=AppConfig.STATE_DISABLED)
            self.update_status("Queue cleared.", "yellow")

    def _update_ui_after_fetch(self):
        self.add_button.configure(state=AppConfig.STATE_NORMAL)
        if self.download_queue and not self.is_downloading:
            self.download_button.configure(state=AppConfig.STATE_NORMAL)
        else:
            self.download_button.configure(state=AppConfig.STATE_DISABLED)

    def start_download_thread(self):
        if self.is_downloading or not self.download_queue:
            return
        self.open_folder_button.grid_remove()
        threading.Thread(target=self.run_download_process, daemon=True).start()
    
    def run_download_process(self):
        self.is_downloading = True
        self.after(0, lambda: self.download_button.configure(state=AppConfig.STATE_DISABLED, text="Downloading..."))
        self.after(0, lambda: self.progress_bar.set(0))
        
        use_default = self.use_default_path_switch.get() == 1
        default_path = self.default_save_path.get()
        save_path = default_path if use_default and os.path.isdir(default_path) else filedialog.askdirectory()

        if not save_path:
            self.update_status("Download cancelled: No folder selected.", "yellow")
            self.is_downloading = False
            self.after(0, self._update_ui_after_fetch)
            self.after(0, lambda: self.download_button.configure(text="Start Download"))
            return
        
        self.last_save_path = save_path
        queue_copy = list(self.download_queue)
        max_workers = int(self.concurrency_selector.get())

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._download_single_video, item, save_path, idx): item for idx, item in enumerate(queue_copy)}
            
            for i, _ in enumerate(concurrent.futures.as_completed(futures), 1):
                self.after(0, self.update_overall_progress, i, len(queue_copy))
        
        self.is_downloading = False
        self.download_queue.clear()
        self.after(0, lambda: [w.destroy() for w in self.queue_frame.winfo_children()])
        self.after(0, lambda: self.download_button.configure(text="Start Download", state=AppConfig.STATE_DISABLED))
        self.update_status("All downloads completed!", "green")
        self.after(0, lambda: self.open_folder_button.grid(row=1, column=1, sticky="e"))

    def _download_single_video(self, video_item: Dict, save_path: str, idx: int):
        try:
            command = self._build_yt_dlp_command(video_item, save_path, idx)
            
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            stderr = process.stderr
            print(f"--- Running for '{video_item['title']}' ---\nCommand: {' '.join(command)}\nstderr:\n{stderr}\n--- End ---")

            if process.returncode != 0:
                error_msg = f"Download failed for {video_item['title'][:30]}..."
                if "ffmpeg" in stderr.lower() and "not found" in stderr.lower():
                    error_msg = "Error: FFmpeg is required for MP3 conversion."
                elif stderr:
                    error_msg = stderr.strip().split('\n')[-1]
                self.update_status(f"Failed: {error_msg}", "red")
                return

            sub_requested = self.subtitle_switch.get() == 1
            warning_messages = []
            if sub_requested and "has no subtitles" in stderr:
                warning_messages.append("subtitles not found")

            if warning_messages:
                self.update_status(f"Downloaded '{video_item['title'][:20]}...' but {', '.join(warning_messages)}.", "yellow")

        except Exception as e:
            self.update_status(f"An unexpected error occurred for '{video_item['title'][:20]}...': {e}", "red")

    def _get_lang_code(self, lang_string: str) -> str:
        match = re.search(r'\((\w+)\)', lang_string)
        return match.group(1) if match else "en"

    def _build_yt_dlp_command(self, video_item: Dict, save_path: str, idx: int) -> List[str]:
        prefix = self.prefix_entry.get().strip()
        sane_prefix = "".join(i for i in prefix if i not in r'\/:*?"<>|')
        filename_prefix = f"[{sane_prefix}] " if sane_prefix else ""
        number_prefix = f"{idx + 1:02d} - " if self.numbering_switch.get() == 1 else ""
        
        final_path = save_path
        if self.playlist_folder_switch.get() and video_item.get('playlist_title'):
            sane_playlist_title = "".join(i for i in video_item['playlist_title'] if i not in r'\/:*?"<>|')
            final_path = os.path.join(save_path, sane_playlist_title)
        
        filename = f"{number_prefix}{filename_prefix}%(title)s"
        
        command = ['yt-dlp']
        is_audio = "Audio" in self.format_selector.get()
        if is_audio:
            command.extend(['-x', '--audio-format', 'mp3', '-f', 'bestaudio', '--audio-quality', self.bitrate_selector.get()])
            if self.thumbnail_switch.get():
                command.append('--embed-thumbnail')
        else:
            quality = self.quality_selector.get()
            filename += f" - {quality}"
            video_format, audio_format = AppConfig.QUALITY_MAP.get(quality, AppConfig.QUALITY_MAP["Highest"])
            format_string = f"{video_format}+{audio_format}"
            command.extend(['-f', format_string, '--merge-output-format', 'mp4'])

        if self.metadata_switch.get():
            command.append('--add-metadata')
            
        if self.subtitle_switch.get() and not is_audio:
            command.append('--embed-subs')
            command.extend(['--convert-subs', 'srt'])
            if self.subtitle_all_switch.get():
                command.append('--all-subs')
            else:
                sub_lang_code = self._get_lang_code(self.subtitle_lang_selector.get())
                command.extend(['--sub-langs', sub_lang_code])

        output_template = os.path.join(final_path, f"{filename}.%(ext)s")
        command.extend(['--ignore-errors', '--no-progress', '-o', output_template, video_item['url']])
        return command

    def start_update_thread(self):
        self.update_yt_dlp_button.configure(state=AppConfig.STATE_DISABLED)
        threading.Thread(target=self._run_yt_dlp_update, daemon=True).start()

    def _run_yt_dlp_update(self):
        self.update_status("Updating yt-dlp...", "yellow")
        try:
            command = ['yt-dlp', '-U']
            process = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            if process.returncode == 0:
                msg = "yt-dlp is already up to date."
                if "Updating to" in process.stdout:
                    msg = "yt-dlp updated successfully!"
                self.update_status(msg, "green")
            else:
                self.update_status(f"Update failed: {process.stderr.strip()}", "red")
        except Exception as e:
            self.update_status(f"Update error: {e}", "red")
        finally:
            self.update_yt_dlp_button.configure(state=AppConfig.STATE_NORMAL)

    def open_last_folder(self):
        if self.last_save_path and os.path.isdir(self.last_save_path):
            try:
                if sys.platform == "win32":
                    os.startfile(self.last_save_path)
                else:
                    opener = "open" if sys.platform == "darwin" else "xdg-open"
                    subprocess.Popen([opener, self.last_save_path])
            except Exception as e:
                self.update_status(f"Error opening folder: {e}", "red")

    def update_overall_progress(self, completed: int, total: int):
        self.progress_bar.set(completed / total)
        self.update_status(f"Downloading... ({completed}/{total}) complete")
        
    def update_status(self, message: str, color: str = "white"):
        text_color = AppConfig.COLOR_MAP.get(color, "white")
        self.after(0, lambda: self.status_label.configure(text=f"Status: {message}", text_color=text_color))

if __name__ == "__main__":
    app = App()
    app.mainloop()