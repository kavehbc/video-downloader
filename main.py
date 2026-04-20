import re
from pathlib import Path
import pandas as pd
import streamlit as st
import yt_dlp

DOWNLOAD_DIR = Path(__file__).parent / "download"
DOWNLOAD_DIR.mkdir(exist_ok=True)
ARCHIVE_FILE = DOWNLOAD_DIR / ".archive.txt"

YOUTUBE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch|shorts|embed|v/)|youtu\.be/)",
    re.IGNORECASE,
)

# Format label -> {format selector, audio_only flag}
YOUTUBE_FORMATS: dict[str, dict] = {
    "Best Quality (MP4)": {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "audio_only": False,
    },
    "1080p (MP4)": {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
        "audio_only": False,
    },
    "720p (MP4)": {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
        "audio_only": False,
    },
    "480p (MP4)": {
        "format": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",
        "audio_only": False,
    },
    "360p (MP4)": {
        "format": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",
        "audio_only": False,
    },
    "Audio Only (MP3)": {
        "format": "bestaudio/best",
        "audio_only": True,
    },
}

# Default format used for non-YouTube URLs
DEFAULT_FORMAT = YOUTUBE_FORMATS["Best Quality (MP4)"]


def is_youtube(url: str) -> bool:
    return bool(YOUTUBE_PATTERN.search(url.strip()))


def fetch_info(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url.strip(), download=False)


def is_youtube_playlist(url: str) -> bool:
    return is_youtube(url) and "list=" in url.strip()


def _is_in_archive(video_id: str) -> bool:
    if not video_id or not ARCHIVE_FILE.exists():
        return False
    needle = f"youtube {video_id}"
    return any(
        line.strip() == needle
        for line in ARCHIVE_FILE.read_text(encoding="utf-8").splitlines()
    )


def fetch_playlist_entries(url: str) -> list[dict]:
    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist"}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url.strip(), download=False)
    entries = []
    for i, entry in enumerate(info.get("entries") or [], start=1):
        video_id = entry.get("id") or ""
        duration_s = entry.get("duration")
        dur_str = ""
        if duration_s:
            m, s = divmod(int(duration_s), 60)
            h, m = divmod(m, 60)
            dur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        status = "✅ Downloaded" if _is_in_archive(video_id) else "⬜ Pending"
        entries.append({
            "#": i,
            "id": video_id,
            "Title": entry.get("title") or f"Video {i}",
            "Duration": dur_str,
            "URL": vid_url,
            "Status": status,
        })
    return entries


def _make_progress_hook(progress_bar, status_text):
    def hook(d: dict) -> None:
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            if total:
                pct = min(downloaded / total, 1.0)
                progress_bar.progress(pct)
                speed_str = f" @ {speed / 1_048_576:.1f} MB/s" if speed else ""
                status_text.text(
                    f"Downloading… {pct * 100:.1f}%  "
                    f"({downloaded / 1_048_576:.1f} / {total / 1_048_576:.1f} MB{speed_str})"
                )
        elif d["status"] == "finished":
            progress_bar.progress(1.0)
            status_text.text("Merging / processing…")

    return hook


def download_video(url: str, fmt: dict, progress_bar, status_text) -> Path:
    ydl_opts: dict = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "format": fmt["format"],
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_make_progress_hook(progress_bar, status_text)],
    }

    if fmt["audio_only"]:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
        del ydl_opts["merge_output_format"]

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url.strip(), download=True)
        base = Path(ydl.prepare_filename(info))
        return base.with_suffix(".mp3" if fmt["audio_only"] else ".mp4")


def main() -> None:
    st.set_page_config(
        page_title="Video Downloader",
        page_icon="🎬",
        layout="centered",
    )
    st.title("🎬 Video Downloader")
    st.caption(
        "Download videos from YouTube, X (Twitter), Facebook, Instagram, TikTok, and more."
    )

    for key in ("info", "info_url", "downloaded_file", "downloaded_file_url", "playlist_entries", "playlist_url"):
        if key not in st.session_state:
            st.session_state[key] = None

    url: str = st.text_input(
        "Video URL",
        placeholder="https://www.youtube.com/watch?v=...",
    )

    yt = is_youtube(url) if url else False
    is_playlist = is_youtube_playlist(url) if url else False

    # --- Format selector (YouTube only) ---
    fmt = DEFAULT_FORMAT
    if yt:
        st.markdown("**Download Format**")
        fmt_label: str = st.selectbox(
            "Download format:",
            options=list(YOUTUBE_FORMATS.keys()),
            label_visibility="collapsed",
        )
        fmt = YOUTUBE_FORMATS[fmt_label]
        if fmt["audio_only"]:
            st.caption(
                "⚠️ MP3 conversion requires **FFmpeg** on your PATH. "
                "[Download FFmpeg](https://ffmpeg.org/download.html)"
            )
        else:
            st.caption(
                "ℹ️ Merging video + audio streams requires **FFmpeg**. "
                "[Download FFmpeg](https://ffmpeg.org/download.html)"
            )

    # --- Action buttons ---
    if is_playlist:
        # ── Playlist mode ──────────────────────────────────────────────────
        col_fetch, col_dl = st.columns(2)
        with col_fetch:
            fetch_btn = st.button(
                "📋 Fetch Playlist",
                use_container_width=True,
                disabled=not url,
            )
        with col_dl:
            download_all_btn = st.button(
                "⬇️ Download All",
                type="primary",
                use_container_width=True,
                disabled=not url,
            )

        # Clear stale entries when the URL changes
        if st.session_state.playlist_url != url:
            st.session_state.playlist_entries = None

        if fetch_btn and url:
            with st.spinner("Fetching playlist info…"):
                try:
                    st.session_state.playlist_entries = fetch_playlist_entries(url)
                    st.session_state.playlist_url = url
                except Exception as exc:
                    st.error(f"Could not fetch playlist: {exc}")

        entries: list | None = st.session_state.playlist_entries
        if entries:
            df_slot = st.empty()

            def _render_df(ents: list) -> None:
                rows = [
                    {"#": e["#"], "Title": e["Title"], "Duration": e["Duration"], "Status": e["Status"]}
                    for e in ents
                ]
                df_slot.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            _render_df(entries)
            downloaded_count = sum(1 for e in entries if e["Status"] == "✅ Downloaded")
            st.caption(f"{downloaded_count} / {len(entries)} downloaded")

            if download_all_btn:
                st.session_state.downloaded_file = None
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                pending_indices = [
                    i for i, e in enumerate(entries) if e["Status"] != "✅ Downloaded"
                ]
                total_pending = len(pending_indices)
                for step, idx in enumerate(pending_indices):
                    entries[idx]["Status"] = "⏳ In Progress"
                    st.session_state.playlist_entries = entries
                    _render_df(entries)
                    try:
                        status_text.text(
                            f"({step + 1}/{total_pending}) {entries[idx]['Title']}"
                        )
                        download_video(entries[idx]["URL"], fmt, progress_bar, status_text)
                        entries[idx]["Status"] = "✅ Downloaded"
                        # Update archive so future sessions detect this as downloaded
                        with open(ARCHIVE_FILE, "a", encoding="utf-8") as af:
                            af.write(f"youtube {entries[idx]['id']}\n")
                    except Exception as exc:  # noqa: BLE001
                        entries[idx]["Status"] = "❌ Failed"
                    st.session_state.playlist_entries = entries
                    _render_df(entries)
                progress_bar.empty()
                status_text.empty()
                failed = sum(1 for e in entries if "❌" in e["Status"])
                if failed:
                    st.warning(
                        f"⚠️ {failed} video(s) failed. {total_pending - failed} downloaded."
                    )
                else:
                    st.success(f"✅ All {total_pending} video(s) downloaded!")

    else:
        # ── Single-video mode ──────────────────────────────────────────────
        col_prev, col_dl = st.columns(2)
        with col_prev:
            preview_btn = st.button("🔍 Preview", use_container_width=True, disabled=not url)
        with col_dl:
            download_btn = st.button(
                "⬇️ Download",
                type="primary",
                use_container_width=True,
                disabled=not url,
            )

        # --- Preview ---
        if preview_btn and url:
            with st.spinner("Fetching video info…"):
                try:
                    st.session_state.info = fetch_info(url)
                    st.session_state.info_url = url
                except Exception as exc:
                    st.error(f"Could not fetch video info: {exc}")
                    st.session_state.info = None
                    st.session_state.info_url = None

        if st.session_state.info and st.session_state.info_url == url:
            info: dict = st.session_state.info
            st.divider()
            c_thumb, c_meta = st.columns([1, 2])
            with c_thumb:
                if info.get("thumbnail"):
                    st.image(info["thumbnail"], use_container_width=True)
            with c_meta:
                st.subheader(info.get("title") or "—")
                uploader = info.get("uploader") or info.get("channel")
                if uploader:
                    st.caption(f"By {uploader}")
                if info.get("duration"):
                    m, s = divmod(int(info["duration"]), 60)
                    st.caption(f"Duration: {m}:{s:02d}")
                if info.get("view_count"):
                    st.caption(f"Views: {info['view_count']:,}")

        # --- Download ---
        if download_btn and url:
            st.session_state.downloaded_file = None
            progress_bar = st.progress(0.0)
            status = st.empty()
            try:
                status.text("Starting download…")
                out_path = download_video(url, fmt, progress_bar, status)
                progress_bar.progress(1.0)
                status.empty()
                st.session_state.downloaded_file = out_path
                st.session_state.downloaded_file_url = url
                st.success(f"✅ Download complete: **{out_path.name}**")
            except yt_dlp.utils.DownloadError as exc:
                progress_bar.empty()
                status.empty()
                st.error(f"Download failed: {exc}")
            except Exception as exc:
                progress_bar.empty()
                status.empty()
                st.error(f"Unexpected error: {exc}")

        # --- Save-to-device link ---
        dl_file: Path | None = st.session_state.get("downloaded_file")
        if dl_file and st.session_state.get("downloaded_file_url") == url and dl_file.exists():
            mime = "audio/mpeg" if dl_file.suffix == ".mp3" else "video/mp4"
            with open(dl_file, "rb") as fh:
                st.download_button(
                    label="💾 Save to your device",
                    data=fh,
                    file_name=dl_file.name,
                    mime=mime,
                    use_container_width=True,
                )


if __name__ == "__main__":
    main()
