from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._data_loader import load_data_file


@dataclass
class NormativeProfile:
    profile_id: str
    profile_name: str
    documents: list[dict[str, Any]]
    calc_mode: str
    comments: str
    enabled_methods: list[str]
    applicability_rules_profile: str


def load_normative_profiles() -> dict[str, NormativeProfile]:
    raw = load_data_file("normative_profiles.json")
    out: dict[str, NormativeProfile] = {}
    for item in list(raw.get("profiles") or []):
        p = NormativeProfile(
            profile_id=str(item.get("profile_id") or ""),
            profile_name=str(item.get("profile_name") or ""),
            documents=list(item.get("documents") or []),
            calc_mode=str(item.get("calc_mode") or "AUTO"),
            comments=str(item.get("comments") or ""),
            enabled_methods=[str(x) for x in (item.get("enabled_methods") or [])],
            applicability_rules_profile=str(item.get("applicability_rules_profile") or "DEFAULT_CURRENT"),
        )
        if p.profile_id:
            out[p.profile_id] = p
    return out
