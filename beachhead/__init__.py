"""
Beachhead: a market-mapping and account-qualification engine.

Give it a market thesis (a JSON config) and a company universe (a CSV). It reads
each company's live, public job postings, scores them against the thesis using
hiring as the buying signal, and returns a ranked market map plus a qualified
target pipeline the sales team can work.

The thesis lives in data, not code, so the same engine points at a new sector by
editing config. It scores a universe you curate; it does not invent companies.

Live sources: Greenhouse, Lever, Ashby. Standard library only, no dependencies.
"""

__version__ = "0.2.0"
