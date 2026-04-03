import json

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "playlist.m3u"

def build_m3u():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = ["#EXTM3U"]

    live_list = data.get("直播", {}).get("所有直播", [])

    for item in live_list:
        title = item.get("title", "NO_TITLE")
        url = item.get("url", "")
        group = item.get("group", "LIVE")

        if not url:
            continue

        # IPTV标准格式
        lines.append(f'#EXTINF:-1 group-title="{group}",{title}')
        lines.append(url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"完成：生成 {OUTPUT_FILE}，数量 {len(live_list)}")


if __name__ == "__main__":
    build_m3u()
