# Entry point. Run with: python -m sweepstake
# Launches the PyWebView native window.

from __future__ import annotations

import logging
import sys
from pathlib import Path

import webview

from sweepstake.app import SweepstakeAPI
from sweepstake.storage.repository import Repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def _web_dir() -> str:
    # Works both in development (source tree) and inside a PyInstaller bundle.
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent
    return str(base / "web")


def main() -> None:
    repo = Repository()
    repo.connect()

    api = SweepstakeAPI(repo)

    web_dir = _web_dir()
    index_html = Path(web_dir) / "index.html"

    window = webview.create_window(
        title="World Cup 2026 Sweepstake",
        url=str(index_html),
        js_api=api,
        width=1100,
        height=750,
        min_size=(800, 600),
        background_color="#1a1a2e",
    )

    webview.start(debug=False)
    repo.close()


if __name__ == "__main__":
    main()
