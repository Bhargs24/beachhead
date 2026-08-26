"""Score one company against an ICP, using its live postings as the signal.

The design choice that matters: every account is built around a single named
buyer role. Signals are read from that one posting, not the whole board, so a
company is not rewarded simply for having more jobs open, and the evidence link
always points at the exact role the row names.
"""
from __future__ import annotations
from .icp import ICP

_TIERS = ["chief", "vp", "vice president", "head of", "director",
          "principal", "staff", "senior", "lead", "manager"]


def _seniority(title: str) -> int:
    t = title.lower()
    for rank, kw in enumerate(_TIERS):
        if kw in t:
            return len(_TIERS) - rank
    return 0


def _geo_ok(icp: ICP, loc: str) -> bool:
    l = (loc or "").lower().strip()
    if icp.geo_exclude and any(x in l for x in icp.geo_exclude):
        return False
    if not icp.geo_include:
        return True
    return any(m in l for m in icp.geo_include) or (l == "" and "remote" in icp.geo_include)


def _is_buyer(icp: ICP, title: str) -> bool:
    t = (title or "").lower()
    if any(x in t for x in icp.buyer_exclude):
        return False
    return any(s in t for s in icp.buyer_titles)


def score_company(icp: ICP, company: dict, jobs: list[dict]) -> dict:
    buyer_jobs = [j for j in jobs if _is_buyer(icp, j["title"]) and _geo_ok(icp, j["location"])]
    persona = max(buyer_jobs, key=lambda j: _seniority(j["title"])) if buyer_jobs else None
    role_text = persona["text"] if persona else ""

    score = icp.weight_buyer_role if persona else 0
    hits = {}
    for sig in icp.signals:
        found = sorted({term for term in sig.terms if term in role_text})
        if found:
            hits[sig.name] = found
            score += min(len(found) * sig.weight, sig.cap)

    note, total = "", len(jobs)
    if icp.large_board_over and total > icp.large_board_over:
        score -= icp.size_penalty
        note = f"{total} open roles: likely late-stage, longer procurement; kept as a stress case"
    elif not buyer_jobs:
        note = "no buyer role open right now; low intent this scan"

    signal_str = "; ".join(f"{k}: {', '.join(t.strip() for t in v)}"
                           for k, v in hits.items()) or "none in role JD"
    return {
        "company": company["name"], "segment": company.get("segment", ""),
        "score": max(score, 0),
        "buyer_role_open": persona["title"] if persona else "none open now",
        "buyer_roles_count": len(buyer_jobs),
        "signals": signal_str,
        "open_roles": total,
        "evidence_url": persona["url"] if persona else "",
        "note": note,
    }
