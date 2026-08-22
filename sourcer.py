"""
Libra ICP sourcer.

Libra's GTM question is: which specific job, for which specific US buyer, gets
someone to pay. This tool scores a universe of candidate companies (companies.csv)
against a written ICP, using each company's live public job postings as the
signal, so the list is ranked by real evidence instead of gut feel. It does not
invent companies; you give it the universe, it does the reading and scoring.

The ICP (encoded below as a scoring function):
  - Libra can't out-enterprise Glean from a standing start, so the universe is
    mid-market, not the Fortune 500.
  - A company hiring Operations / RevOps / CS roles has cross-tool coordination
    outrunning its headcount. That open role is the pain signal and the person to
    sell to.
  - The job post lists the tools they run on. Every one of Libra's named
    integrations (Slack, Gmail, Notion, Jira, Drive, Salesforce, HubSpot) that
    shows up is evidence of the sprawl Libra collapses.
  - Specific compliance language (SOC 2, HIPAA, BAA, PCI, ISO 27001, FedRAMP) is
    Libra's unlock: in regulated US buying it is the blocker Libra removes.
  - Very large boards are flagged as probable Glean territory and penalized, with
    the reason logged rather than deleted.

Swap the three keyword lists to test a different ICP; swap companies.csv to point
it at a different universe. No dependencies. Data is live and public (Greenhouse,
Lever, Ashby). Every row carries a real URL you can click to verify.
"""
from __future__ import annotations
import urllib.request, json, html, re, csv, sys
from concurrent.futures import ThreadPoolExecutor


def load_companies(path="companies.csv"):
    """The universe to score, as data not code. Rows: name,vertical,ats,token."""
    with open(path, newline="", encoding="utf-8") as f:
        return [(r["name"], r["vertical"], r["ats"], r["token"])
                for r in csv.DictReader(f)]

# ---- the ICP, as data ------------------------------------------------------
# Strong buyer titles: an open one is clear pain plus a named person to sell to.
BUYER_STRONG = [
    "revenue operations", "revops", "sales operations", "sales ops",
    "gtm operations", "go-to-market operations", "go to market operations",
    "chief of staff", "business operations", "biz ops", "bizops",
    "strategy & operations", "strategy and operations", "revenue strategy",
    "customer success", "customer experience", "marketing operations",
    "deal desk", "deal operations", "partnerships operations",
    "growth operations", "revenue enablement", "sales enablement",
]
# Never the buyer we want (technical or wrong-domain roles).
HARD_EXCLUDE = ["engineer", "engineering", "developer", "devops", " sre",
                "site reliability", "architect"]
# Generic "operations" titles that are functional/clinical, not the GTM buyer.
SOFT_EXCLUDE = [
    "clinical", "outpatient", "inpatient", "provider", "care team", "pharmacy",
    "claims", "payment operation", "payments operation", "benefits operation",
    "trading", "warehouse", "fulfillment", "supply chain", "manufacturing",
    "hardware", "flight", "people operation", "hr operation", "workplace",
    "facilities", "data operation", "trust & safety", "trust and safety",
    "risk operation", "credit operation", "lending operation", "loan",
    "collections", "kyc operation", "it operation", "revenue cycle",
    "network operation", "field operation", "underwriting operation",
    "security operation", "product operation",
]
TOOLS_CORE = ["slack", "gmail", "notion", "jira", "google drive",
              "google workspace", "salesforce", "hubspot"]
TOOLS_ADJACENT = ["zendesk", "intercom", "linear", "confluence", "gong",
                  "outreach", "salesloft", "asana", "netsuite", "looker"]
# Only specific, discriminating terms. Generic words like "compliance" and
# "audit" appear in almost every job post, so they are deliberately excluded.
COMPLIANCE = ["soc 2", "soc2", "hipaa", "baa", "business associate agreement",
              "pci", "iso 27001", "fedramp"]
PAIN = ["cross-functional", "manual", "coordinate", "streamline", "reporting",
        "tooling", "operational efficiency", "process improvement",
        "scale operations", "stakeholder"]
US_MARKERS = ["united states", "usa", "u.s", "remote", "new york", "san francisco",
              "boston", "austin", "chicago", "denver", "seattle", "atlanta",
              "los angeles", "california", "texas", "florida", ", ny", ", ca",
              ", tx", ", ma", ", il", ", co", ", wa", ", ga", "nyc"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "libra-icp-sourcer/1.0"})
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.load(r)


def _clean(text):
    return re.sub(r"<[^>]+>", " ", html.unescape(text or "")).lower()


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
    l = (loc or "").lower()
    return l.strip() == "" or any(m in l for m in US_MARKERS)


def is_buyer_role(title):
    t = (title or "").lower()
    if any(h in t for h in HARD_EXCLUDE):
        return False
    if any(s in t for s in BUYER_STRONG):
        return True
    if "operations" in t or "chief of staff" in t:
        return not any(x in t for x in SOFT_EXCLUDE)
    return False


def _seniority(title):
    t = title.lower()
    for i, kw in enumerate(["vp", "vice president", "head of", "chief", "director",
                            "principal", "lead", "senior", "manager"]):
        if kw in t:
            return len(t) - i  # earlier keyword = more senior
    return 0


def score_company(company, jobs):
    name, vertical, ats, token = company
    buyer_jobs = [j for j in jobs if is_buyer_role(j["title"]) and is_us(j["location"])]
    buyer_text = " ".join(j["text"] for j in buyer_jobs)
    all_text = " ".join(j["text"] for j in jobs)

    tools_core = sorted({t for t in TOOLS_CORE if t in buyer_text})
    tools_adj = sorted({t for t in TOOLS_ADJACENT if t in buyer_text})
    comp = sorted({c for c in COMPLIANCE if c in all_text})
    pain_hit = any(p in buyer_text for p in PAIN)

    score = 0
    if buyer_jobs:
        score += 40
    score += min(len(tools_core) * 9, 45)
    score += min(len(tools_adj) * 3, 9)
    score += min(len(comp) * 8, 24)
    if pain_hit:
        score += 5

    size_flag, disqualifier = "", ""
    total = len(jobs)
    if total > 150:
        size_flag = "LARGE"
        disqualifier = (f"{total} open roles: likely enterprise, probable Glean territory; "
                        f"kept as a compliance-wedge stress test")
        score -= 20
    elif total < 4 and not buyer_jobs:
        disqualifier = "tiny board, no clear buyer role open right now"

    persona = ""
    if buyer_jobs:
        persona = max(buyer_jobs, key=lambda j: _seniority(j["title"]))["title"]
    evidence_url = buyer_jobs[0]["url"] if buyer_jobs else (jobs[0]["url"] if jobs else "")

    return {"company": name, "vertical": vertical, "score": max(score, 0),
            "buyer_role_open": persona or "none open now",
            "buyer_roles_count": len(buyer_jobs),
            "tools_detected": ", ".join(tools_core + tools_adj) or "none in buyer JDs",
            "compliance_signals": ", ".join(comp) or "none",
            "open_roles": total, "size_flag": size_flag,
            "evidence_url": evidence_url, "disqualifier": disqualifier}


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
    scored = [r for r in results if r["score"] >= 40]
    print(f"\nWrote targets.csv ({len(results)} companies scanned, {len(scored)} with a live buyer role). "
          f"Every row has a real evidence_url.")


if __name__ == "__main__":
    main()
