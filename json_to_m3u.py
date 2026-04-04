import json
import os

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "live.m3u"

BASE_URL = "http://192.168.6.16:8080/play?url="


def main():

    # 🚨 1. 文件检查
    if not os.path.exists(INPUT_FILE):
        print("❌ JSON文件不存在:", INPUT_FILE)
        return

    # 🚨 2. 读取 JSON
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("❌ JSON读取失败:", e)
        return

    # 🚨 3. 统一数据结构（关键修复）
    live_list = data.get("data", [])

    if not live_list:
        print("⚠️ 没有直播数据（data为空）")
        return

    lines = ["#EXTM3U"]

    count = 0

    for item in live_list:

        vid = item.get("id")
        name = item.get("name", "NO_TITLE")

        if not vid:
            continue

        play_url = BASE_URL + vid

        lines.append(f'#EXTINF:-1 group-title="LIVE",{name}')
        lines.append(play_url)

        count += 1

    # 🚨 4. 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ M3U生成完成，共 {count} 条")


if __name__ == "__main__":
    main()
