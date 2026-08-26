"""The market thesis, loaded from JSON into a validated object.

An ICP file answers four questions for a given market:
  who is the buyer      -> buyer.titles / buyer.exclude
  what signals fit+timing -> signals (named keyword groups, each weighted)
  where do we sell      -> geo.include / geo.exclude
  how do we rank        -> weights and size handling

Keeping this in data means the same engine maps a new sector by editing a file.
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field


@dataclass
class Signal:
    name: str
    weight: int
    cap: int
    terms: list[str]


@dataclass
class ICP:
    market: str
    thesis: str
    buyer_titles: list[str]
    buyer_exclude: list[str]
    signals: list[Signal]
    geo_include: list[str]
    geo_exclude: list[str]
    large_board_over: int
    size_penalty: int
    weight_buyer_role: int
    raw_path: str = ""

    @staticmethod
    def load(path: str) -> "ICP":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        low = lambda xs: [s.lower() for s in xs]
        buyer = d.get("buyer", {})
        signals = [Signal(name, s["weight"], s.get("cap", 10 ** 6), low(s["terms"]))
                   for name, s in d.get("signals", {}).items()]
        geo = d.get("geo", {})
        size = d.get("size", {})
        icp = ICP(
            market=d["market"], thesis=d.get("thesis", ""),
            buyer_titles=low(buyer.get("titles", [])),
            buyer_exclude=low(buyer.get("exclude", [])),
            signals=signals,
            geo_include=low(geo.get("include", [])),
            geo_exclude=low(geo.get("exclude", [])),
            large_board_over=size.get("large_board_over", 0),
            size_penalty=size.get("penalty", 0),
            weight_buyer_role=d.get("weights", {}).get("buyer_role", 40),
            raw_path=path,
        )
        icp.validate()
        return icp

    def validate(self):
        if not self.buyer_titles:
            raise ValueError(f"{self.raw_path}: buyer.titles is empty; name the persona to sell to")
        if not self.signals:
            raise ValueError(f"{self.raw_path}: no signals defined; a thesis needs at least one")
