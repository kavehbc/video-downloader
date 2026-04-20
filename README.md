# 🎬 Video Downloader

A Streamlit web app for downloading videos from YouTube, X (Twitter), Facebook, Instagram, TikTok, and hundreds of other sites powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- **Single video downloads** — paste any supported URL and download in your chosen format
- **YouTube quality selector** — Best, 1080p, 720p, 480p, 360p, or Audio Only (MP3)
- **YouTube playlist support** — fetches the full playlist into a live-updating dataframe showing each video's status (Pending / In Progress / Downloaded / Failed)
- **Persistent archive** — already-downloaded playlist videos are remembered across sessions via a local archive file
- **In-browser save** — a download button appears after each completed download so you can save the file directly from the browser
- **FFmpeg integration** — automatic merging of separate video and audio streams; MP3 extraction for audio-only downloads
- **Docker ready** — multi-stage Dockerfile and Docker Compose for one-command deployment

## Requirements

### Running locally

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) on your `PATH`

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Running with Docker

- [Docker](https://docs.docker.com/get-docker/) (FFmpeg is installed automatically in the image)

## Usage

### Local

```bash
streamlit run main.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Docker Compose

```bash
docker compose up --build
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

Downloaded files are stored in a named Docker volume (`downloads`) and persist across container restarts. To stop:

```bash
docker compose down
```

Add `-v` to also remove the downloads volume:

```bash
docker compose down -v
```

## Project Structure

```
video-downloader/
├── main.py              # Streamlit app (UI + download logic)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Multi-stage Docker image with FFmpeg
├── docker-compose.yml   # Build and run with a single command
├── download/            # Downloaded files (git-ignored)
│   └── .archive.txt     # Tracks downloaded playlist video IDs
└── src/                 # Reserved for additional modules
```

## Supported Sites

Any site supported by yt-dlp — including YouTube, X (Twitter), Facebook, Instagram, TikTok, Vimeo, Twitch, Reddit, and [1000+ more](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md). Quality/format options are only shown for YouTube URLs; other sites download at the best available quality automatically.

## Notes

- Merging video and audio streams (1080p and above) requires FFmpeg. If FFmpeg is not installed locally, use the Docker setup instead.
- Downloaded files are saved to the `download/` directory relative to `main.py`.
- The in-browser **Save to your device** button reads the file from the server and streams it to your browser — it only appears after a successful download.
