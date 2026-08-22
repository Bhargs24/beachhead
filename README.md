# libra-sourcer

Turns a set of candidate companies into a ranked, evidence-backed target list for Libra, scored on live hiring signal. You supply the companies and the ICP; it does the fetching, keyword-scoring, and ranking in minutes.

## What it does

Reads companies' live job postings (Greenhouse, Lever, Ashby) and scores each on fit with Libra's buyer:

- an open RevOps / CS / ops role (the pain, and the person to sell to)
- the tools their job posts name (Slack, Jira, Salesforce, HubSpot, the sprawl Libra collapses)
- SOC 2 / HIPAA / BAA language (the compliance wedge Libra's certs clear)

Each row is built around one named open role, and the link and the detected tools both come from that exact posting. Compliance is read company-wide, since it is a company attribute, not a job's.

```bash
python sourcer.py      # no dependencies, standard library only
```

The company universe lives in `companies.csv` (name, vertical, ATS, token), so you point it at any set of accounts by editing data, not code. The ICP is the keyword lists and the `WEIGHTS` at the top of `sourcer.py`; edit them and the list re-ranks for a different buyer, which is how you test one hypothesis against another.

## What it found (live)

49 companies scanned, 23 with an open buyer role. Top of the list: Drata, Sardine, Counterpart, Vanta, Persona. Full ranked output in `targets.csv`.

Built by Bhargav Raghavendra, with AI assistance under my direction. The ICP design and the target judgment are mine.
