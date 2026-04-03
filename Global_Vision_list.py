import json
import subprocess

# ===============================
# 输出文件（GitHub Actions 环境）
# ===============================
OUTPUT_FILE = "Global_Vision_list.json"

# ===============================
# 节目分组
# ===============================
GROUPS = {
    "全球大視野": [
        "https://www.youtube.com/playlist?list=PLvHT0yeWYIuDyLVv1yDiIxhtk1ZQ92_RY"
    ],
    "國際直球對決": [
        "https://www.youtube.com/watch?v=L3QdmF68ibk&list=PLvHT0yeWYIuASUZjoW8OXe4e_UkgP7qDU"
    ],
    "新聞大白話": [
        "https://www.youtube.com/watch?v=gXL7xfVhgxU&list=PLh9lJwqeOuvNPqHfKf10o5Ql9M-OEnoLy"
    ],
    "世界財經周報": [
        "https://www.youtube.com/watch?v=b8iJF64rC-k&list=PLyvXVH_86VfblqpVtRq7D9vRyQMl6o2E8"
    ],
    "文茜的世界周報": [
        "https://www.youtube.com/watch?v=denoskP4brc&list=PLyvXVH_86VfZ7g9Xb5SYIVhpO09Pg2zVI"
    ],
    "孤烟暮蝉": [
        "https://www.youtube.com/@guyanmuchan01/videos?view=0&sort=dd"
    ]
}

# ===============================
# 直播频道
# ===============================
LIVE_CHANNELS = [
    "https://www.youtube.com/@ctitv",
    "https://www.youtube.com/@globalnewstw",
    "https://www.youtube.com/@ettv32",
    "https://www.youtube.com/@newsebc",
    "https://www.youtube.com/@ftvnews",
    "https://www.youtube.com/@tvbsnews01",
    "https://www.youtube.com/@setnews",
    "https://www.youtube.com/@trtworld",
    "https://www.youtube.com/@aljazeeraenglish",
    "https://www.youtube.com/@abcnews",
    "https://www.youtube.com/@nbcnews"
]

# ===============================
# JSON 结构
# ===============================
final_data = {
    "直播": {"所有直播": []},
    "節目": {}
}

# ===============================
# 1️⃣ 抓直播
# ===============================
print("开始抓直播...")

all_live = []

for url in LIVE_CHANNELS:
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--flat-playlist",
            url + "/streams"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=25)

        if result.returncode != 0:
            continue

        for line in result.stdout.splitlines():
            if not line:
                continue

            data = json.loads(line)

            if not data.get("is_live"):
                continue

            vid = data.get("id")
            title = data.get("title", "")

            thumb = ""
            if data.get("thumbnails"):
                thumb = data["thumbnails"][-1]["url"]

            all_live.append({
                "videoId": vid,
                "title": title,
                "thumbnail": thumb
            })

    except Exception as e:
        print("直播错误:", e)

final_data["直播"]["所有直播"] = all_live

# ===============================
# 2️⃣ 抓节目
# ===============================
for group, urls in GROUPS.items():
    print("处理:", group)

    videos = []
    seen = set()

    for url in urls:
        try:
            cmd = ["yt-dlp", "--flat-playlist", "-J", url]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                continue

            data = json.loads(result.stdout)

            entries = data.get("entries", [])

            for e in entries:
                vid = e.get("id")
                title = e.get("title")

                if not vid or not title:
                    continue

                if vid in seen:
                    continue

                if "Private" in title or "Deleted" in title:
                    continue

                videos.append({
                    "videoId": vid,
                    "title": title,
                    "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                })

                seen.add(vid)

        except Exception as e:
            print("节目错误:", e)

    final_data["節目"][group] = videos

# ===============================
# 3️⃣ 输出 JSON
# ===============================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print("完成：", OUTPUT_FILE)
