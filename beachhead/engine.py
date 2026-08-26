"""Orchestration: load a universe, fetch every board in parallel, score, rank."""
from __future__ import annotations
import csv
from concurrent.futures import ThreadPoolExecutor
from .sources import fetch, SUPPORTED
from .scoring import score_company
from .icp import ICP


def load_universe(path: str) -> list[dict]:
    """Rows: name, segment, ats, token. The set of companies to score."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = [dict(r) for r in csv.DictReader(f)]
    bad = [r["name"] for r in rows if r.get("ats") not in SUPPORTED]
    if bad:
        raise ValueError(f"{path}: unsupported ATS for {', '.join(bad)}; use one of {SUPPORTED}")
    return rows


def _score_one(icp: ICP, company: dict) -> dict:
    jobs = fetch(company["ats"], company["token"])
    row = score_company(icp, company, jobs)
    row["_reachable"] = bool(jobs)
    return row


def run(icp: ICP, universe: list[dict], workers: int = 12) -> list[dict]:
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(lambda c: _score_one(icp, c), universe))
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def probe(universe: list[dict], workers: int = 12) -> list[dict]:
    """Validate that each board token resolves. Used by the `validate` command."""
    def check(c):
        jobs = fetch(c["ats"], c["token"])
        return {"name": c["name"], "ats": c["ats"], "token": c["token"],
                "ok": bool(jobs), "open_roles": len(jobs)}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(check, universe))
