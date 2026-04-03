import json

INPUT_FILE = "output/Global_Vision_list.json"
OUTPUT_FILE = "output/live.m3u"

BASE_URL = "http://192.168.6.16:8080/play?url="


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        print("❌ JSON读取失败")
        return

    lines = ["#EXTM3U"]

    live_list = data.get("直播", {}).get("所有直播", [])

    if not live_list:
        print("⚠️ 没有直播数据")
        return

    for item in live_list:
        vid = item.get("id")
        title = item.get("title", "NO_TITLE")
        group = item.get("group", "LIVE")

        if not vid:
            continue

        play_url = BASE_URL + vid

        lines.append(f'#EXTINF:-1 group-title="{group}",{title}')
        lines.append(play_url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ M3U生成完成，共 {len(live_list)} 条")


if __name__ == "__main__":
    main()
