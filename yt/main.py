import yt_dlp
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PLAYLIST_FILE = os.path.join(BASE_DIR, "playlists.txt")
OUTPUT_FILE = os.path.join(BASE_DIR, "playlist.m3u")

PLAYLIST_END = 100  # 每个列表只取最新的前 100 个


def get_playlist_configs():
    """
    读取 playlists.txt，格式为：
        分组名|播放列表URL
    以 # 开头的行和空行会被忽略。
    没有写分组名时，用 "未分组" 兜底。
    """
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


def process_playlist(url):
    """提取单个播放列表的条目（扁平模式，只取前 100 个）"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlistend": PLAYLIST_END,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info.get("entries", []) or []


def normalize_url(entry):
    """扁平模式下 url 有时只是视频 ID，需要补全"""
    video_url = entry.get("url") or entry.get("webpage_url")
    if not video_url:
        return None
    if not video_url.startswith("http"):
        video_url = f"https://www.youtube.com/watch?v={video_url}"
    return video_url


def main():
    configs = get_playlist_configs()
    if not configs:
        print("错误：playlists.txt 里没有有效的播放列表配置")
        sys.exit(1)

    total = 0
    failed = []

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

        for group_title, url in configs:
            print(f"Processing [{group_title}]: {url}")
            try:
                entries = [e for e in process_playlist(url) if e]
            except Exception as e:
                print(f"  失败：{e}")
                failed.append((group_title, url, str(e)))
                continue

            print(f"  -> {len(entries)} videos")

            for entry in entries:
                video_url = normalize_url(entry)
                if not video_url:
                    continue

                title = entry.get("title") or "Unknown Title"
                # 标题里的换行会破坏 M3U 结构，替换掉
                title = title.replace("\n", " ").replace("\r", " ").strip()

                f.write(f'#EXTINF:-1 group-title="{group_title}",{title}\n')
                f.write(f"{video_url}\n")
                total += 1

    print(f"\n完成：生成 {OUTPUT_FILE}，共 {total} 个条目")

    if failed:
        print(f"\n有 {len(failed)} 个列表处理失败：")
        for group_title, url, err in failed:
            print(f"  [{group_title}] {url}\n    {err}")
        # 有失败时以非零退出码结束，方便在 Actions 里看到红色标记
        sys.exit(1)


if __name__ == "__main__":
    main()
