"""Writers: a machine-readable pipeline (CSV) and a human market map (Markdown)."""
from __future__ import annotations
import csv, datetime
from collections import OrderedDict
from .icp import ICP

PIPELINE_COLS = ["rank", "company", "segment", "score", "buyer_role_open",
                 "buyer_roles_count", "signals", "open_roles", "evidence_url", "note"]


def write_pipeline(path: str, results: list[dict]):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PIPELINE_COLS)
        w.writeheader()
        for i, r in enumerate(results, 1):
            w.writerow({"rank": i, **{k: r.get(k, "") for k in PIPELINE_COLS if k != "rank"}})


def _clip(s: str, n: int) -> str:
    """Truncate at a word boundary with an ellipsis, so cells never cut mid-word."""
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(" ,;")
    return cut + " …"


def _by_segment(results: list[dict]) -> "OrderedDict[str, list]":
    seg = OrderedDict()
    for r in results:
        seg.setdefault(r["segment"] or "unsegmented", []).append(r)
    # order segments by their strongest account, so the map reads best-first
    return OrderedDict(sorted(seg.items(),
                              key=lambda kv: max(x["score"] for x in kv[1]), reverse=True))


def write_market_map(path: str, icp: ICP, results: list[dict], universe_size: int):
    scored = [r for r in results if r["score"] > 0]
    today = datetime.date.today().isoformat()
    lines = [
        f"# Market map: {icp.market}", "",
        f"*{icp.thesis}*", "",
        f"Generated {today} by [Beachhead](https://github.com/Bhargs24/beachhead) "
        f"from live Greenhouse / Lever / Ashby postings. "
        f"{universe_size} companies scanned, {len(scored)} with a live buyer signal. "
        "Each account is anchored to one named open role; the link points at that role.",
        "",
        "## Work these first", "",
        "| # | Company | Segment | Score | Buyer role open now | Why now |",
        "| - | ------- | ------- | ----: | ------------------- | ------- |",
    ]
    for i, r in enumerate(scored[:10], 1):
        why = r["signals"] if r["signals"] != "none in role JD" else r["note"]
        link = f"[{r['company']}]({r['evidence_url']})" if r["evidence_url"] else r["company"]
        lines.append(f"| {i} | {link} | {r['segment']} | {r['score']} | "
                     f"{r['buyer_role_open']} | {_clip(why, 90)} |")

    lines += ["", "## The map, by segment", ""]
    for seg, rows in _by_segment(scored).items():
        lines.append(f"### {seg}  ({len(rows)})")
        lines.append("")
        lines.append("| Company | Score | Buyer role open | Signals detected | Link |")
        lines.append("| ------- | ----: | --------------- | ---------------- | ---- |")
        for r in sorted(rows, key=lambda x: x["score"], reverse=True):
            link = f"[role]({r['evidence_url']})" if r["evidence_url"] else "—"
            lines.append(f"| {r['company']} | {r['score']} | {r['buyer_role_open']} | "
                         f"{_clip(r['signals'], 70)} | {link} |")
        lines.append("")

    quiet = [r["company"] for r in results if r["score"] == 0]
    if quiet:
        lines += ["## No live signal this scan", "",
                  "In the universe but showing no matching open role right now, so lower "
                  "priority until that changes: " + ", ".join(quiet) + ".", ""]

    lines += [
        "---", "",
        "**How to read this.** Score = a buyer-persona role open now, plus weighted "
        "keyword signals read from that role's job description, minus a size penalty "
        "for very large boards. It measures fit and timing from public hiring, not "
        "intent to buy. It ranks a curated universe; it does not discover companies. "
        "Treat it as the first pass that tells the sales team who to research and call "
        "first, not the last word.", "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
