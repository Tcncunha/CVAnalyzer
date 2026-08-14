"""
Job description fetcher -- extracts the text of a job posting from a URL.

Some job sites (LinkedIn, Indeed, etc.) block automated access. In those
cases the function returns "" and the UI falls back to manual pasting.
"""

import re

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

MAX_CHARS = 20000

_BLOCK_TAGS = {
    "script", "style", "noscript", "nav", "footer", "header", "aside",
    "form", "button", "iframe", "svg", "meta", "link", "dialog",
}


def fetch_job_description(url: str) -> str:
    """Fetch the given URL and return the main text content (or "" on failure)."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    resp = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=20
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(_BLOCK_TAGS):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    text = main.get_text(" ", strip=True)
    text = re.sub(r"\s{2,}", " ", text)
    return text[:MAX_CHARS]