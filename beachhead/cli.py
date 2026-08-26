"""Command line: `run` a market, or `validate` a universe's board tokens."""
from __future__ import annotations
import argparse, os, sys
from . import __version__
from .icp import ICP
from .engine import load_universe, run, probe
from .report import write_pipeline, write_market_map


def _run(args):
    icp = ICP.load(args.market)
    universe = load_universe(args.universe)
    print(f"Beachhead: scoring {len(universe)} companies against '{icp.market}' ...",
          file=sys.stderr)
    results = run(icp, universe, workers=args.workers)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    write_pipeline(args.out + ".pipeline.csv", results)
    write_market_map(args.out + ".market-map.md", icp, results, len(universe))

    scored = [r for r in results if r["score"] > 0]
    print(f"\n{'#':>2}  {'company':22} {'seg':16} {'score':>5}  buyer role open")
    print("-" * 78)
    for i, r in enumerate(scored[:15], 1):
        print(f"{i:>2}  {r['company'][:22]:22} {r['segment'][:16]:16} "
              f"{r['score']:>5}  {r['buyer_role_open'][:30]}")
    print(f"\nWrote {args.out}.pipeline.csv and {args.out}.market-map.md "
          f"({len(scored)}/{len(universe)} with live signal).")


def _validate(args):
    universe = load_universe(args.universe)
    rows = probe(universe, workers=args.workers)
    ok = [r for r in rows if r["ok"]]
    print(f"{'company':24} {'ats':10} {'token':22} {'roles':>6}  status")
    print("-" * 72)
    for r in sorted(rows, key=lambda x: (not x["ok"], x["name"])):
        status = "ok" if r["ok"] else "NO BOARD / wrong token"
        print(f"{r['name'][:24]:24} {r['ats']:10} {r['token'][:22]:22} "
              f"{r['open_roles']:>6}  {status}")
    print(f"\n{len(ok)}/{len(rows)} board tokens resolve.")
    if len(ok) != len(rows):
        sys.exit(1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="beachhead", description=__doc__)
    p.add_argument("--version", action="version", version=f"beachhead {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="score a universe against a market thesis")
    r.add_argument("--market", required=True, help="path to the ICP JSON")
    r.add_argument("--universe", required=True, help="path to the universe CSV")
    r.add_argument("--out", required=True, help="output path prefix (no extension)")
    r.add_argument("--workers", type=int, default=12)
    r.set_defaults(func=_run)

    v = sub.add_parser("validate", help="check that every board token resolves")
    v.add_argument("--universe", required=True)
    v.add_argument("--workers", type=int, default=12)
    v.set_defaults(func=_validate)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
