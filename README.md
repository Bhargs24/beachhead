# libra-sourcer

Builds a target account list for Libra from live hiring signal. Point it at an ICP, it returns a scored, evidence-linked list of companies in minutes.

## What it does

Reads companies' live job postings (Greenhouse, Lever, Ashby) and scores each on fit with Libra's buyer:

- an open RevOps / CS / ops role (the pain, and the person to sell to)
- the tools their job posts name (Slack, Jira, Salesforce, HubSpot, the sprawl Libra collapses)
- SOC 2 / HIPAA / BAA language (the compliance wedge Libra's certs clear)

Every row links to the real posting.

```bash
python sourcer.py      # no dependencies, standard library only
```

The ICP is three keyword lists at the top of `sourcer.py`. Swap them and the list rebuilds for a different buyer, which is how you test one hypothesis against another.

## What it found (live)

49 companies scanned, 28 with an open buyer role. Top of the list: Counterpart, Abnormal Security, Sardine, Drata, Checkr. Full ranked output in `targets.csv`.

Built by Bhargav Raghavendra.
