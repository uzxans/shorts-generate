import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_demo_video(html, duration, w=1080, h=1920):
    """Render an HTML snippet as a webm video by recording the page.

    Returns the path to the recorded webm file.
    """
    record_dir = tempfile.mkdtemp(prefix="demo_")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": w, "height": h},
            record_video_dir=record_dir,
            record_video_size={"width": w, "height": h},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_content(html, wait_until="load")
        page.wait_for_timeout(int(duration * 1000))
        context.close()
        browser.close()

    webm_files = sorted(Path(record_dir).glob("*.webm"))
    if not webm_files:
        raise RuntimeError("Playwright did not produce a video file")
    return str(webm_files[0])
