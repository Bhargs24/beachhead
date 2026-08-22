"""
Libra ICP sourcer.

Libra's GTM question is: which specific job, for which specific US buyer, gets
someone to pay. This tool scores a universe of candidate companies (companies.csv)
against a written ICP, using each company's live public job postings as the
signal, and ranks them by fit. You supply the universe and the ICP; it does the
fetching, keyword-scoring, and ranking. It does not invent companies.

Each row is built around one named open role, the buyer. The tools it detects and
the link it shows both come from that single posting, so the evidence matches the
role the row actually names. Compliance is read company-wide, since it is a
company attribute, not a property of one job.

The ICP (edit the keyword lists and WEIGHTS below to test a different buyer):
  - a company hiring an Operations / RevOps / CS role has cross-tool coordination
    outrunning its headcount; that open role is the pain and the person to sell to
  - the role's job post names the tools they run on; Libra's integrations that
    appear are evidence of the sprawl Libra collapses
  - specific compliance language (SOC 2, HIPAA, BAA, PCI, ISO 27001, FedRAMP) is
    Libra's unlock in regulated US buying
  - very large boards are flagged as probable Glean territory and penalized

No dependencies. Data is live and public (Greenhouse, Lever, Ashby). Built with
AI assistance under my direction; the ICP design and the target judgment are mine.
"""
from __future__ import annotations
import urllib.request, json, html, re, csv, sys
from concurrent.futures import ThreadPoolExecutor


def load_companies(path="companies.csv"):
    """The universe to score, as data not code. Rows: name,vertical,ats,token."""
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["name"], r["vertical"], r["ats"], r["token"])
                for r in csv.DictReader(f)]


# ---- the ICP, as data. Edit these lists plus WEIGHTS to test a different buyer.
# Whitelist of GTM/ops buyer titles. Anything not on this list is not the buyer,
# which is safer than trying to blacklist every non-GTM ops role (talent ops,
# legal ops, fulfillment ops, and so on) one by one.
BUYER_STRONG = [
    "revenue operations", "revops", "sales operations", "sales ops",
    "gtm operations", "go-to-market operations", "go to market operations",
    "gtm strategy", "chief of staff", "business operations", "biz ops", "bizops",
    "strategy & operations", "strategy and operations", "revenue strategy",
    "customer success", "customer experience", "customer operations",
    "client operations", "channel operations", "marketing operations",
    "deal desk", "deal operations", "partnerships operations",
    "growth operations", "revenue enablement", "sales enablement",
]
HARD_EXCLUDE = ["engineer", "engineering", "developer", "devops", " sre",
                "site reliability", "architect"]
# Functional / clinical / domain ops that are not the GTM buyer. Applied to every
# candidate title, including strong matches, so junk cannot slip through.
SOFT_EXCLUDE = [
    "clinical", "outpatient", "inpatient", "provider", "care team", "pharmacy",
    "compounding", "claims", "payment operation", "payments operation",
    "benefits operation", "vendor management", "training operation",
    "conversion operation", "temporary", "trading", "warehouse", "fulfillment",
    "supply chain", "manufacturing", "hardware", "flight", "people operation",
    "hr operation", "workplace", "facilities", "data operation",
    "trust & safety", "trust and safety", "risk operation", "credit operation",
    "lending operation", "loan", "collections", "kyc operation", "it operation",
    "revenue cycle", "network operation", "field operation",
    "underwriting operation", "security operation", "product operation",
]
TOOLS_CORE = ["slack", "gmail", "notion", "jira", "google drive",
              "google workspace", "salesforce", "hubspot"]
TOOLS_ADJACENT = ["zendesk", "intercom", "linear", "confluence", "gong",
                  "outreach", "salesloft", "asana", "netsuite", "looker"]
# Only specific, discriminating terms. Generic words like "compliance" and
# "audit" appear in almost every job post, so they are deliberately excluded.
COMPLIANCE = ["soc 2", "hipaa", "baa", "business associate agreement",
              "pci", "iso 27001", "fedramp"]
US_MARKERS = ["united states", "usa", "u.s", "remote", "new york", "san francisco",
              "boston", "austin", "chicago", "denver", "seattle", "atlanta",
              "los angeles", "california", "texas", "florida", ", ny", ", ca",
              ", tx", ", ma", ", il", ", co", ", wa", ", ga", "nyc"]
# Explicit non-US regions override a generic "remote" marker.
NON_US = ["emea", "apac", "united kingdom", " uk", "london", "europe", "india",
          "canada", "germany", "france", "dublin", "singapore", "australia",
          "latam", "ireland", "netherlands", "remote - e"]
# Scoring weights kept as data so the ICP is genuinely tunable.
WEIGHTS = {"buyer_role": 40, "core_tool": 9, "core_cap": 45, "adjacent_tool": 3,
           "adjacent_cap": 9, "compliance": 8, "compliance_cap": 24,
           "large_penalty": 20, "large_board": 150}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "libra-icp-sourcer/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)


def _clean(text):
    t = re.sub(r"<[^>]+>", " ", html.unescape(text or "")).lower()
    return t.replace("soc2", "soc 2")  # normalize so SOC2 and SOC 2 count once


def fetch(company):
    """Return list of {title, location, url, text} for one company's live board."""
    name, vertical, ats, token = company
    out = []
    try:
        if ats == "greenhouse":
            data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
            for j in data.get("jobs", []):
                out.append({"title": j.get("title", ""),
                            "location": (j.get("location") or {}).get("name", ""),
                            "url": j.get("absolute_url", ""),
                            "text": _clean(j.get("content", ""))})
        elif ats == "lever":
            data = _get(f"https://api.lever.co/v0/postings/{token}?mode=json")
            for j in data:
                cats = j.get("categories") or {}
                out.append({"title": j.get("text", ""),
                            "location": cats.get("location", ""),
                            "url": j.get("hostedUrl", ""),
                            "text": _clean(j.get("descriptionPlain") or j.get("description", ""))})
        elif ats == "ashby":
            data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false")
            for j in data.get("jobs", []):
                if not j.get("isListed", True):
                    continue
                out.append({"title": j.get("title", ""),
                            "location": j.get("location", ""),
                            "url": j.get("jobUrl", ""),
                            "text": _clean(j.get("descriptionPlain") or j.get("descriptionHtml", ""))})
    except Exception as e:
        print(f"  ! {name}: fetch failed ({type(e).__name__})", file=sys.stderr)
    return out


def is_us(loc):
    l = (loc or "").lower().strip()
    if not l or any(x in l for x in NON_US):   # blank or an explicit foreign region
        return False
    return any(m in l for m in US_MARKERS)


def is_buyer_role(title):
    t = (title or "").lower()
    if any(h in t for h in HARD_EXCLUDE):
        return False
    if any(x in t for x in SOFT_EXCLUDE):
        return False
    return any(s in t for s in BUYER_STRONG)


def _seniority(title):
    """Rank by seniority tier, most senior first. Not title length."""
    t = title.lower()
    tiers = ["chief", "vp", "vice president", "head of", "director",
             "principal", "senior", "lead", "manager"]
    for rank, kw in enumerate(tiers):
        if kw in t:
            return len(tiers) - rank
    return 0


def score_company(company, jobs):
    name, vertical, ats, token = company
    buyer_jobs = [j for j in jobs if is_buyer_role(j["title"]) and is_us(j["location"])]
    persona_job = max(buyer_jobs, key=lambda j: _seniority(j["title"])) if buyer_jobs else None

    # Tools come from the one role we name, so the evidence matches the row and
    # the score is not simply a reward for having more open postings. Compliance
    # is read company-wide, since it is a company attribute, not a job's.
    role_text = persona_job["text"] if persona_job else ""
    all_text = " ".join(j["text"] for j in jobs)
    tools_core = sorted({t for t in TOOLS_CORE if t in role_text})
    tools_adj = sorted({t for t in TOOLS_ADJACENT if t in role_text})
    comp = sorted({c for c in COMPLIANCE if c in all_text})

    score = 0
    if buyer_jobs:
        score += WEIGHTS["buyer_role"]
    score += min(len(tools_core) * WEIGHTS["core_tool"], WEIGHTS["core_cap"])
    score += min(len(tools_adj) * WEIGHTS["adjacent_tool"], WEIGHTS["adjacent_cap"])
    score += min(len(comp) * WEIGHTS["compliance"], WEIGHTS["compliance_cap"])

    size_flag, disqualifier = "", ""
    total = len(jobs)
    if total > WEIGHTS["large_board"]:
        size_flag = "LARGE"
        disqualifier = (f"{total} open roles: likely enterprise, probable Glean "
                        f"territory; kept as a wedge stress test")
        score -= WEIGHTS["large_penalty"]
    elif total < 4 and not buyer_jobs:
        disqualifier = "tiny board, no clear buyer role open right now"

    return {"company": name, "vertical": vertical, "score": max(score, 0),
            "buyer_role_open": persona_job["title"] if persona_job else "none open now",
            "buyer_roles_count": len(buyer_jobs),
            "tools_detected": ", ".join(tools_core + tools_adj) or "none in role JD",
            "compliance_signals": ", ".join(comp) or "none",
            "open_roles": total, "size_flag": size_flag,
            "evidence_url": persona_job["url"] if persona_job else "",
            "disqualifier": disqualifier}


def main():
    companies = load_companies()
    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(lambda c: score_company(c, fetch(c)), companies))
    results.sort(key=lambda r: r["score"], reverse=True)

    cols = ["rank", "company", "vertical", "score", "buyer_role_open",
            "buyer_roles_count", "tools_detected", "compliance_signals",
            "open_roles", "size_flag", "evidence_url", "disqualifier"]
    with open("targets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(results, 1):
            w.writerow({"rank": i, **{k: r.get(k, "") for k in cols if k != "rank"}})

    print(f"\n{'#':>2}  {'company':18} {'vert':10} {'score':>5}  {'buyer role open':42} {'compliance':20}")
    print("-" * 108)
    for i, r in enumerate(results, 1):
        print(f"{i:>2}  {r['company']:18} {r['vertical']:10} {r['score']:>5}  "
              f"{r['buyer_role_open'][:41]:42} {r['compliance_signals'][:19]:20}")
    with_buyer = sum(1 for r in results if r["buyer_roles_count"] > 0)
    print(f"\nWrote targets.csv ({len(results)} companies scanned, {with_buyer} with an "
          f"open buyer role). The evidence URL points at the exact role named.")


if __name__ == "__main__":
    main()
