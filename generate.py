"""
Selects the next topic, renders its HTML template to a 1080x1350 PNG,
and saves current_post.json + updated state.json.
"""
import json
import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

load_dotenv()

BASE_DIR = Path(__file__).parent


def load_state() -> dict:
    f = BASE_DIR / "state.json"
    return json.loads(f.read_text()) if f.exists() else {"last_index": -1}


def save_state(state: dict):
    (BASE_DIR / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_topics() -> list:
    return json.loads((BASE_DIR / "content" / "topics.json").read_text())


def select_topic(topics: list, state: dict) -> tuple:
    index = (state["last_index"] + 1) % len(topics)
    return index, topics[index]


def render_html(template_name: str, data: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(BASE_DIR / "templates")),
        autoescape=False,  # allows <strong> tags inside data strings
    )
    template = env.get_template(f"{template_name}.html")
    return template.render(**data)


def generate_image(html: str, output_path: Path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(1500)  # allow fonts and Lucide icons to render
        page.screenshot(
            path=str(output_path),
            clip={"x": 0, "y": 0, "width": 1080, "height": 1350},
        )
        browser.close()


def main():
    topics = load_topics()
    state = load_state()
    index, topic = select_topic(topics, state)

    html = render_html(topic["template"], topic["data"])

    output_dir = BASE_DIR / "output"
    output_dir.mkdir(exist_ok=True)

    today = date.today().isoformat()
    image_path = output_dir / f"post_{today}.png"
    generate_image(html, image_path)

    current_post = {
        "topic_index": index,
        "topic": topic,
        "image_path": str(image_path.relative_to(BASE_DIR)),
        "date": today,
    }
    (BASE_DIR / "current_post.json").write_text(
        json.dumps(current_post, indent=2, ensure_ascii=False)
    )

    state["last_index"] = index
    save_state(state)

    print(f"OK: {image_path.name} (topic #{index}: {topic['caption_theme']})")


if __name__ == "__main__":
    main()
