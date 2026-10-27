import yt_dlp
import os
import re
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_FILE = os.path.join(BASE_DIR, "playlists.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "playlist.m3u")

PLAYLIST_END = 100
VIDEO_URL_TEMPLATE = "http://192.168.6.7:28000/yt/{id}.mp4"

MAX_RETRIES = 3
RETRY_DELAY = 5


def sanitize(text, fallback="Unknown"):
    if not text:
        return fallback
    text = str(text).replace("\r", " ").replace("\n", " ")
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = text.strip()
    return text or fallback


def get_playlist_configs():
    if not os.path.exists(PLAYLIST_FILE):
        print(f"错误：找不到配置文件 {PLAYLIST_FILE}")
        sys.exit(1)

    configs = []
    with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                group, url = line.split("|", 1)
                group, url = group.strip(), url.strip()
                if not url:
                    print(f"警告：第 {line_no} 行 URL 为空，已跳过")
                    continue
                configs.append((group or "未分组", url))
            else:
                configs.append(("未分组", line))
    return configs


def extract_playlist_once(url):
    """单次提取，返回 entries 列表（可能为空）"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": PLAYLIST_END,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        print("  DEBUG: extract_info 返回 None")
        return []

    entries = info.get("entries")
    print(f"  DEBUG: info keys = {list(info.keys())[:10]}")
    print(f"  DEBUG: entries 类型 = {type(entries)}, 长度 = {len(entries) if entries else 0}")

    return entries or []


def process_playlist_with_retry(url):
    """带重试的提取，空列表也触发重试"""
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  尝试 {attempt}/{MAX_RETRIES}...")
        try:
            entries = extract_playlist_once(url)
            if entries:
                return entries
            print(f"  返回 0 条，{RETRY_DELAY} 秒后重试")
        except Exception as e:
            print(f"  异常：{e}")
            if attempt == MAX_RETRIES:
                raise

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    return []


def get_video_id(entry):
    vid = entry.get("id")
    if vid and isinstance(vid, str) and len(vid) == 11:
        return vid

    for key in ("url", "webpage_url"):
        raw = entry.get(key)
        if not raw:
            continue
        if "v=" in raw:
            return raw.split("v=", 1)[1].split("&", 1)[0]
        if "youtu.be/" in raw:
            return raw.split("youtu.be/", 1)[1].split("?", 1)[0]
        if len(raw) == 11 and "/" not in raw and "?" not in raw:
            return raw
    return None


def get_station(entry, fallback_group):
    for key in ("uploader", "channel", "channel_title"):
        val = entry.get(key)
        if val:
            return sanitize(val, fallback_group)
    return sanitize(fallback_group, "Unknown")


def get_filename(entry):
    return sanitize(entry.get("title"), "Unknown Title")


def main():
    configs = get_playlist_configs()
    if not configs:
        print("错误：playlists.txt 里没有有效的播放列表配置")
        sys.exit(1)

    total = 0
    skipped = 0
    empty_playlists = []

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for group_title, url in configs:
            print(f"\nProcessing [{group_title}]: {url}")
            try:
                entries = process_playlist_with_retry(url)
            except Exception as e:
                print(f"  最终失败：{e}")
                empty_playlists.append((group_title, url))
                continue

            if not entries:
                print(f"  重试 {MAX_RETRIES} 次后仍为 0 条")
                empty_playlists.append((group_title, url))
                continue

            print(f"  -> 获取到 {len(entries)} 个视频")
            for entry in entries:
                if not entry:
                    continue
                video_id = get_video_id(entry)
                if not video_id:
                    skipped += 1
                    continue

                video_url = VIDEO_URL_TEMPLATE.format(id=video_id)
                station = get_station(entry, group_title)
                filename = get_filename(entry)
                display_title = f"[{station}] {filename}"

                f.write(f'#EXTINF:-1 group-title="{group_title}",{display_title}\n')
                f.write(f"{video_url}\n")
                total += 1

    print(f"\n完成：生成 {OUTPUT_FILE}，共 {total} 个条目")
    if skipped:
        print(f"跳过 {skipped} 个无法提取 ID 的条目")
    if empty_playlists:
        print(f"\n以下 {len(empty_playlists)} 个列表获取失败（0 条）：")
        for g, u in empty_playlists:
            print(f"  [{g}] {u}")


if __name__ == "__main__":
    main()
