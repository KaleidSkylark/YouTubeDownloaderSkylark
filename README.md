<h1 align="center">Skylark Downloader</h1>

<p align="center">
  A sleek, modern, and powerful GUI for downloading YouTube videos and playlists.
  <br>
  Built with Python and CustomTkinter, Skylark Downloader wraps the power of <code>yt-dlp</code> in a user-friendly, feature-rich interface.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet" alt="CustomTkinter">
  <img src="https://img.shields.io/badge/Engine-yt--dlp-red" alt="yt-dlp">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License: MIT">
</p>

<table align="center">
  <tr>
    <td align="center"><b>Main Interface</b></td>
    <td align="center"><b>Settings Panel</b></td>
  </tr>
  <tr>
    <td><img src="https://scontent-hkg4-1.xx.fbcdn.net/v/t1.15752-9/566538909_797779849753637_209001358120840595_n.png?_nc_cat=100&ccb=1-7&_nc_sid=9f807c&_nc_eui2=AeFSOeIKYrrLcZGe6N1aj4esNv7Hns4LusQ2_seezgu6xAy2QDKQ6XfltzeM1rKgZP_xAwqyBEsmtsTVuvf3y68K&_nc_ohc=8N73BapkYHAQ7kNvwEQ2bzm&_nc_oc=Adnfax3S_GCPfONeHxWjuXYCKn8pvMvV9WMEIeQqjRevMuinjrqjGAXDI-X8U8SHl9Y&_nc_zt=23&_nc_ht=scontent-hkg4-1.xx&oh=03_Q7cD3gEX8S3M-4cpXHultDKnB7wbUtOCQXzuHYWXp3K0pUjWrQ&oe=691C1A3D" alt="Main Application Interface" width="400"></td>
    <td><img src="https://scontent-hkg4-2.xx.fbcdn.net/v/t1.15752-9/568714691_1207446937893876_6997447706613012963_n.png?_nc_cat=111&ccb=1-7&_nc_sid=9f807c&_nc_eui2=AeFwQnYHyClguwmu2iAElZFohtUiTpY-6CeG1SJOlj7oJwq48AqoCLXu3GjZTPe1ap9sfcXxeuhFd717fyH8L_98&_nc_ohc=kNDWzk3gWlEQ7kNvwG3pRta&_nc_oc=AdkX96PgE9U618cR9PPprgtzKR0gHPL0aXD02-sFDAeegwQA_-JkhABNCUCnr8Qu1RQ&_nc_zt=23&_nc_ht=scontent-hkg4-2.xx&oh=03_Q7cD3gFS0BLGljhTKA0kZdESF492gNKOLtwGv_7VmEK7Qkkd2A&oe=691C1CE2" alt="Settings Panel" width="400"></td>
  </tr>
</table>

---

## ✨ Features
* **🌐 Universal YouTube Support:** Download from any YouTube link – single videos, full playlists, or YouTube Music tracks.
* **⚡ High-Performance:**
    * **Concurrent Downloads:** Speed up your process by downloading multiple files simultaneously (up to 5 configurable).
    * **Efficient Backend:** Powered by `yt-dlp` for reliable and fast media fetching.
* **📁 Intelligent File Management:**
    * **Custom Filenaming:** Add custom prefixes and automatic numbering (`01 -`, `02 -`) for organized libraries.
    * **Playlist Folders:** Automatically creates dedicated sub-folders named after playlists.
    * **Default Save Location:** Set a default download folder to skip prompts, or choose one for each session.
* **🖼️ Rich Media Files:**
    * **Embed Thumbnails:** Automatically embeds video thumbnails as album art into MP3 files.
    * **Embed Metadata:** Writes relevant metadata (title, artist, etc.) directly into downloaded files.
* **🔊 Flexible Output Options:**
    * **Format Selection:** Choose between MP4 video or MP3 audio.
    * **Video Quality:** Select specific video resolutions (1080p, 720p, etc.).
    * **Audio Bitrate:** Set MP3 audio quality (128K, 192K, 256K, 320K) for perfect sound.
* **🚀 Seamless Experience:**
    * **Modern UI:** A clean, rounded, and intuitive graphical interface.
    * **Collapsible Settings:** Keep the main window clutter-free with a hideable settings panel.
    * **Smart Validations:** Prevents invalid URLs, duplicate queue entries, and confirms critical actions.
    * **Dependency Check:** Validates `yt-dlp` and `ffmpeg` on startup, guiding users if tools are missing.
    * **In-App Updates:** Easily update the `yt-dlp` engine directly from the application.
    * **Persistent Settings:** Your preferences are saved and loaded automatically.
    * **"Open Folder" Button:** Quick access to your downloaded files.

---

## ⚙️ Setup
To get Skylark Downloader up and running, follow these simple steps:

1.  **Clone the Repository (or Download):**
    ```sh
    git clone [https://github.com/KaleidSkylark/Skylark-Downloader.git](https://github.com/KaleidSkylark/Skylark-Downloader.git)
    cd Skylark-Downloader
    ```
    *(Note: You had `Skylark-YouTube-Downloader.git` in your text, I'm using the repo name from your first `README` request. Adjust the URL as needed.)*

2.  **Install Python Dependencies:**
    Make sure you have Python 3.8+ installed. Then, install the required libraries using `pip`:
    ```sh
    pip install -r requirements.txt
    ```
    *(You will need to create a `requirements.txt` file containing `customtkinter`)*

3.  **Install FFmpeg (Crucial for MP3 Conversion):**
    FFmpeg is a vital external tool required for converting video streams into MP3 audio.
    * **Download:** Visit [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
    * **Installation:** Unzip the downloaded file and add the `bin` folder to your system's **PATH** environment variable.
    *(The application will check for FFmpeg on startup and provide instructions if it's not found.)*

---

## ▶️ Usage
Once setup is complete, navigate to the project directory in your terminal or command prompt and run the application:

```sh
python skylark_downloader.py
