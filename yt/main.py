import yt_dlp
import os

PLAYLIST_URL = "https://www.youtube.com/playlist?list=YOUR_PLAYLIST_ID"  # 改成你的链接

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "playlist.m3u")

def main():
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(PLAYLIST_URL, download=False)

    entries = list(info.get('entries', []))
    print(f"Found {len(entries)} videos")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for entry in entries:
            if not entry:
                continue
            video_url = entry.get('url') or entry.get('webpage_url')
            title = entry.get('title', 'Unknown')
            if video_url and not video_url.startswith('http'):
                video_url = f"https://www.youtube.com/watch?v={video_url}"
            if video_url:
                f.write(f"#EXTINF:-1,{title}\n{video_url}\n")

    print(f"Generated {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
