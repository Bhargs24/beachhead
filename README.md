# libra-sourcer

A tool that turns any ICP hypothesis into a scored, evidence-backed target list for Libra, built from live hiring signal so you can test which buyer is real instead of guessing.

## Why this exists

Libra's open question is which US buyer pays. That is a hypothesis problem, not a list problem. So I didn't hand-type a list. I built something that takes an ICP written as code and returns a ranked list in minutes, so competing hypotheses can be tested head to head.

## What it does

Reads companies' live public job postings (Greenhouse, Lever, Ashby) and scores each company against an ICP defined at the top of the file. The default hypothesis it ships with:

- A company hiring a RevOps / CS / ops role has cross-tool coordination outrunning its headcount. That open role is the pain, and the person to sell to.
- The job post names the tools they run on. Every Libra integration that appears (Slack, Jira, Salesforce, HubSpot, Notion, Drive) is evidence of the sprawl Libra collapses.
- SOC 2 / HIPAA / BAA language is the compliance wedge Libra's certs unlock.
- Very large boards get flagged as probable Glean territory and penalised, with the reason logged.

Every row links to the real posting so you can check it. Run:

```bash
python sourcer.py      # no dependencies, standard library only
```

It writes `targets.csv` and prints a ranked table.

## This is one hypothesis, not the answer

The scoring above is a bet: regulated mid-market, compliance is the unlock. I don't actually know it's right, and nobody does yet, that is the job. The point of the tool is that the ICP is three keyword lists at the top of `sourcer.py`. Change them and the list rebuilds for a different hypothesis. That is how I would run the wedge test:

| Hypothesis | What changes in the ICP | What a reply would prove |
|---|---|---|
| H1 Compliance wedge | regulated verticals, SOC 2 / BAA weighted high | mid-market regulated buyers reply to "clears your security review" |
| H2 Tool-sprawl pain | drop compliance, weight tool-count high, any vertical | the message that lands is "one layer over your 8 tools," not compliance |
| H3 Bottoms-up | small boards, founder / chief-of-staff titles, no vertical filter | Libra's real pull is small teams and founders, matching the early-access motion, not enterprise |

Founder-signed cold email for each, every reply coded (interested / wrong problem / wrong person / no budget / silence), and the data picks the ICP instead of me asserting it.

## What it does not do, on purpose

It finds companies and open buyer roles fast. It does not verify the named human, that still takes a person on LinkedIn, and that is the part that actually matters. The tool exists so the hours go to verifying and writing, not to finding.

## Honest limitations (v1)

- The role matcher is keyword-based. The top of the list is clean; a few lower rows still catch functional-ops titles (clinical ops, payment ops). Tightening the include/exclude lists is a small edit, and one I would make against real reply data, not guesses.
- Coverage is Greenhouse, Lever, and Ashby. Workday and custom boards are the next adapters.
- Matching is literal. An embedding pass would catch tools named indirectly.

## What it found (live, the day I ran it)

Scanned 49 mid-market regulated companies; 28 had a live buyer role. Top of the list: Counterpart, Abnormal Security, Sardine, Drata, Checkr, each hiring the person who will spend month one stitching tools together, each on a compliance stack where Libra's BAAs matter. Full ranked output in `targets.csv`.

Built by Bhargav Raghavendra.
