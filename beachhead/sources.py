"""Adapters for public applicant-tracking systems.

Each adapter takes a company's board token and returns a normalized list of
postings: {title, location, url, text}. Everything downstream is source-agnostic,
so adding a new ATS is a matter of writing one more adapter here.
"""
from __future__ import annotations
import urllib.request, json, html, re, sys

_UA = {"User-Agent": "beachhead/0.2 (+https://github.com/Bhargs24/beachhead)"}
SUPPORTED = ("greenhouse", "lever", "ashby")


def _get(url):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)


def _clean(text: str) -> str:
    """Strip HTML, unescape entities, lower-case, normalize a few token variants."""
    t = re.sub(r"<[^>]+>", " ", html.unescape(text or "")).lower()
    t = re.sub(r"\s+", " ", t)
    return t.replace("soc2", "soc 2")


def fetch(ats: str, token: str) -> list[dict]:
    """Return normalized postings for one company board. Empty list on any error."""
    try:
        if ats == "greenhouse":
            data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
            return [{"title": j.get("title", ""),
                     "location": (j.get("location") or {}).get("name", ""),
                     "url": j.get("absolute_url", ""),
                     "text": _clean(j.get("content", ""))}
                    for j in data.get("jobs", [])]
        if ats == "lever":
            data = _get(f"https://api.lever.co/v0/postings/{token}?mode=json")
            return [{"title": j.get("text", ""),
                     "location": (j.get("categories") or {}).get("location", ""),
                     "url": j.get("hostedUrl", ""),
                     "text": _clean(j.get("descriptionPlain") or j.get("description", ""))}
                    for j in data]
        if ats == "ashby":
            data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false")
            return [{"title": j.get("title", ""),
                     "location": j.get("location", ""),
                     "url": j.get("jobUrl", ""),
                     "text": _clean(j.get("descriptionPlain") or j.get("descriptionHtml", ""))}
                    for j in data.get("jobs", []) if j.get("isListed", True)]
    except Exception as e:  # network, 404 on a wrong token, malformed payload
        print(f"  ! {ats}:{token} fetch failed ({type(e).__name__})", file=sys.stderr)
    return []
