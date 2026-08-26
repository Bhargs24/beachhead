# Beachhead

**Turn a market thesis into a ranked, evidence-backed target list, from live hiring signal.**

Beachhead is a market-mapping and account-qualification engine for GTM teams. You give it a thesis (a JSON file that says who the buyer is and what signals fit and timing) and a company universe (a CSV). It reads every company's live public job postings, scores each against the thesis, and writes two things:

- a **market map** (`.market-map.md`), segmented and ranked, that a salesperson can read top to bottom and know who to call first
- a **pipeline** (`.pipeline.csv`), the same data as structured rows for a CRM or a sheet

The thesis lives in data, not code, so the same engine retargets to a new sector by editing a file. It scores a universe you curate; it does not invent companies. No dependencies, standard library only.

## Why hiring is the signal

A company's open roles are the cheapest honest read on what it is building right now. An open Head of Autonomy means the autonomy stack is being scaled this quarter. An open RevOps role means cross-tool coordination has outrun headcount. Beachhead anchors every account to one named open role, reads the fit-and-timing signals out of *that* job description, and links straight to it, so the score is evidence you can click, not a black box.

## What it produced (real run)

A live map of the **physical AI and robotics** market: 32 companies across eight segments, scored in about a minute.

| # | Company | Segment | Score | Buyer role open now |
| - | ------- | ------- | ----: | ------------------- |
| 1 | Skydio | drones-aerospace | 89 | Senior Autonomy Engineer, Data Curation |
| 2 | Apptronik | humanoid | 84 | Staff MLOps Engineer |
| 3 | Physical Intelligence | foundation-models | 80 | ML Infra Engineer (Data Systems) |
| 4 | Serve Robotics | service-healthcare | 80 | Lead Machine Learning Engineer |
| 5 | Path Robotics | manufacturing-inspection | 72 | Staff Robotics Software Engineer |

Full output, segmented and linked: **[examples/robotics.market-map.md](examples/robotics.market-map.md)**. A second market, [B2B SaaS ops buyers](examples/b2b-saas-ops.market-map.md), runs off the same engine with a different config, to show the retargeting is real.

## Quickstart

```bash
# score a universe against a market thesis
python -m beachhead run \
  --market markets/robotics.json \
  --universe markets/robotics.universe.csv \
  --out examples/robotics

# confirm every board token resolves before a run
python -m beachhead validate --universe markets/robotics.universe.csv
```

## Retarget to a new market

Two files define a market. To point Beachhead at a new sector, write them and run:

**`universe.csv`** — the companies to score. Segment is yours to define.

```csv
name,segment,ats,token
Figure AI,humanoid,greenhouse,figureai
Physical Intelligence,foundation-models,ashby,physicalintelligence
```

**`market.json`** — the thesis. Name the buyer, the signals, the geography, and the weights.

```json
{
  "market": "Physical AI & Robotics",
  "thesis": "A senior software, autonomy, or data role open now means the stack is being built this quarter, which is when tooling decisions get made.",
  "buyer": { "titles": ["head of autonomy", "machine learning", "data platform"],
             "exclude": ["intern", "recruiter", "assistant"] },
  "signals": {
    "ai_stack":   { "weight": 6, "cap": 36, "terms": ["foundation model", "computer vision", "slam"] },
    "data_scale": { "weight": 6, "cap": 30, "terms": ["data pipeline", "teleoperation", "labeling"] }
  },
  "geo":  { "include": [], "exclude": [] },
  "size": { "large_board_over": 300, "penalty": 15 },
  "weights": { "buyer_role": 40 }
}
```

`validate` first, then `run`. Editing weights and signal terms re-ranks the map, which is how you test one thesis against another.

## How the score works

For each company Beachhead finds the open roles whose title matches the buyer persona and passes the geo filter, picks the most senior as the anchor, and scores:

```
score = buyer_role_weight (if a persona role is open)
      + sum over signal groups of min(matched_terms * weight, cap)   # read from that one role's JD
      - size_penalty                                                 # if the board is very large
```

Signals are read from the single anchor role, not the whole board, so a company is not rewarded for simply having more jobs open, and the evidence link matches the row.

## Layout

```
beachhead/        the engine: sources (ATS adapters), icp, scoring, engine, report, cli
markets/          market definitions: <name>.json + <name>.universe.csv
examples/          committed sample output from real runs
```

## Honest limits

It measures fit and timing from public hiring, not intent to buy. It ranks a universe you curate; sourcing the right companies into that universe is the analyst's judgment, and the hardest part. Keyword signals are a first pass, not a reading of the whole business. Treat the output as the ranked starting point that tells a sales team who to research and call first, not the last word.

---

Built by Bhargav Raghavendra. Code written with AI assistance under my direction; the design, the scoring model, and the market judgment are mine.
