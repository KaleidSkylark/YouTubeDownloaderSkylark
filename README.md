# Skylark YouTube Downloader

A modern and feature-rich YouTube downloader built with Python and CustomTkinter.

## Features

- Download videos and audio (MP3) from any YouTube link (videos, playlists, music).
- Concurrent downloads to speed up large queues.
- Automatic creation of folders for playlists.
- Embed thumbnails as album art and write file metadata.
- Full suite of customizable settings that can be saved.
- Startup validation to ensure dependencies like FFmpeg are installed.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install customtkinter yt-dlp
    ```

2.  **Install FFmpeg:**
    FFmpeg is required for audio conversion. Download it from [ffmpeg.org](https://ffmpeg.org/download.html) and add its `bin` folder to your system's PATH. The application will check for FFmpeg on startup and guide you if it's missing.

## Usage

Run the application with the following command:
```bash
python skylark_downloader.py