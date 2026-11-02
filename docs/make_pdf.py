"""Turn docs/instrukcja.md into docs/instrukcja.pdf, looking like the preview in Visual Studio Code.

It converts the Markdown to HTML (screenshots embedded, links inside the document kept), and lets Chrome or Edge
print that page to PDF. It is a tool for whoever updates the guide, not part of the bot, so it needs nothing from
the project:

    python -m pip install markdown
    python docs/make_pdf.py

Chrome or Edge must be installed. Pass another file as an argument to convert it (the PDF goes next to it).
"""

import base64
import html
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "google-chrome",
    "chromium",
    "microsoft-edge",
]

CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; font-size: 11pt;
       line-height: 1.55; color: #24292f; max-width: 100%; }
h1 { font-size: 22pt; border-bottom: 1px solid #d0d7de; padding-bottom: .3em; margin-top: 0; }
h2 { font-size: 16pt; border-bottom: 1px solid #d0d7de; padding-bottom: .25em; margin-top: 1.6em; page-break-after: avoid; }
h3 { font-size: 13pt; margin-top: 1.4em; page-break-after: avoid; }
p, li { orphans: 3; widows: 3; }
a { color: #0969da; text-decoration: none; }
code { font-family: Consolas, "Courier New", monospace; font-size: 90%; background: #eff1f3; padding: .15em .35em; border-radius: 4px; }
pre { background: #f6f8fa; padding: 10px 12px; border-radius: 6px; overflow-x: auto; page-break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 9.5pt; white-space: pre-wrap; word-break: break-word; }
table { border-collapse: collapse; margin: 1em 0; width: 100%; font-size: 10pt; page-break-inside: auto; }
th, td { border: 1px solid #d0d7de; padding: 5px 9px; vertical-align: top; }
th { background: #f6f8fa; text-align: left; }
tr { page-break-inside: avoid; }
blockquote { border-left: 4px solid #d0d7de; color: #57606a; margin: 1em 0; padding: 0 1em; }
img { max-width: 100%; border: 1px solid #d0d7de; border-radius: 6px; display: block; margin: .8em 0; page-break-inside: avoid; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 2em 0; }
"""


def slug(text: str, separator: str = "-") -> str:
    """The anchor GitHub and Visual Studio Code give a heading: lower case, letters (Polish ones too), digits and dashes."""
    text = re.sub(r"<[^>]+>", "", html.unescape(text)).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s", separator, text)


def embed_images(page: str, folder: Path) -> str:
    """Put every local image into the page itself, so the PDF does not depend on the files being next to it."""

    def replace(match: re.Match) -> str:
        source = match.group(1)
        if source.startswith(("http://", "https://", "data:")):
            return match.group(0)
        path = (folder / source).resolve()
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        data = base64.b64encode(path.read_bytes()).decode()
        return f'src="data:{mime};base64,{data}"'

    return re.sub(r'src="([^"]+)"', replace, page)


def find_browser() -> str:
    for candidate in BROWSERS:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise SystemExit("Chrome or Edge is needed to print the PDF, and neither was found.")


def build(source: Path) -> Path:
    body = markdown.markdown(
        source.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
        extension_configs={"toc": {"slugify": slug}},
    )
    page = f'<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>{source.stem}</title><style>{CSS}</style></head><body>{body}</body></html>'
    page = embed_images(page, source.parent)
    pdf = source.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as temp:
        html_file = Path(temp) / "guide.html"
        html_file.write_text(page, encoding="utf-8")
        subprocess.run(
            [find_browser(), "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", html_file.as_uri()],
            check=True,
            capture_output=True,
        )
    return pdf


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("instrukcja.md")
    print(f"Wrote {build(target)}")
