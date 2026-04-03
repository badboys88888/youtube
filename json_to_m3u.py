import json

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "playlist.m3u"

# ===== 你的本地解析服务 =====
BASE_URL = "http://192.168.6.16:8080/play?url="


def build_m3u():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = ["#EXTM3U"]

    for item in data.get("直播", {}).get("所有直播", []):
        title = item.get("title", "NO_TITLE")
        video_id = item.get("id")
        group = item.get("group", "LIVE")

        if not video_id:
            continue

        # ✔ 核心改动：用你的本地解析接口
        play_url = BASE_URL + video_id

        lines.append(f'#EXTINF:-1 group-title="{group}",{title}')
        lines.append(play_url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"完成：生成 {OUTPUT_FILE}")


if __name__ == "__main__":
    build_m3u()
