import argparse
import json
import os

from core.video import build_video

OUT = "output"
os.makedirs(OUT, exist_ok=True)


def process_topic(topic):
    print(f"🚀 {topic['title']}")
    output_path = f"{OUT}/{topic['id']}.mp4"
    build_video(topic, output_path)
    print(f"✅ готово: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=int, help="render only the topic with this id")
    args = parser.parse_args()

    with open("topics.json", encoding="utf-8") as f:
        data = json.load(f)

    topics = data["topics"]
    if args.topic is not None:
        topics = [t for t in topics if t["id"] == args.topic]
        if not topics:
            raise SystemExit(f"topic id {args.topic} not found in topics.json")

    for topic in topics:
        process_topic(topic)


if __name__ == "__main__":
    main()
