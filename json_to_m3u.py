import json
import os

INPUT_FILE = "Global_Vision_list.json"
OUTPUT_FILE = "live.m3u"

BASE_URL = "http://192.168.6.16:8080/play?url="


# =========================
# 🟢 1. 精准匹配（最优先）
# =========================
EXACT_ICON_MAP = {
    "TVBS NEWS": "icons/tvbs.png",
    "凤凰卫视资讯台": "icons/fh.png",
    "东森新闻": "icons/ebc.png",
}


# =========================
# 🟡 2. 关键词兜底匹配
# =========================
KEYWORD_ICON_MAP = {
    "TVBS": "icons/tvbs.png",
    "凤凰": "icons/fh.png",
    "东森": "icons/ebc.png",
    "中天": "icons/cti.png",
}


def get_live_list(data):

    if isinstance(data.get("直播"), dict):
        return data["直播"].get("所有直播", [])

    if isinstance(data.get("data"), list):
        return data["data"]

    return []


def get_name(item):
    return (
        item.get("title")
        or item.get("name")
        or item.get("channel")
        or "NO_TITLE"
    )


# =========================
# 🧠 核心：图标解析（关键）
# =========================
def resolve_icon(name):

    # 1️⃣ 精准匹配（优先级最高）
    if name in EXACT_ICON_MAP:
        return EXACT_ICON_MAP[name]

    # 2️⃣ 关键词匹配（兜底）
    for key, icon in KEYWORD_ICON_MAP.items():
        if key in name:
            return icon

    # 3️⃣ 无匹配
    return ""


def main():

    if not os.path.exists(INPUT_FILE):
        print("❌ JSON文件不存在")
        return

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("❌ JSON读取失败:", e)
        return

    live_list = get_live_list(data)

    if not live_list:
        print("⚠️ 没有直播数据")
        return

    lines = ["#EXTM3U"]

    count = 0

    for item in live_list:

        vid = item.get("id")
        if not vid:
            continue

        name = get_name(item)
        group = item.get("group") or "LIVE"

        url = BASE_URL + str(vid)

        icon = resolve_icon(name)

        # =========================
        # 🟢 写 EXTINF
        # =========================
        if icon:
            lines.append(
                f'#EXTINF:-1 tvg-logo="{icon}" group-title="{group}",{name}'
            )
        else:
            lines.append(
                f'#EXTINF:-1 group-title="{group}",{name}'
            )

        lines.append(url)

        count += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ M3U生成完成，共 {count} 条")


if __name__ == "__main__":
    main()
