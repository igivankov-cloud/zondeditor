from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class NormativeProfile:
    profile_id: str
    profile_name: str
    documents: list[dict[str, Any]]
    calc_mode: str
    comments: str
    enabled_methods: list[str]
    applicability_rules_profile: str


def _profiles_path() -> Path:
    return Path(__file__).with_name("normative_profiles.json")


def load_normative_profiles() -> dict[str, NormativeProfile]:
    raw = json.loads(_profiles_path().read_text(encoding="utf-8"))
    out: dict[str, NormativeProfile] = {}
    for item in list(raw.get("profiles") or []):
        prof = NormativeProfile(
            profile_id=str(item.get("profile_id") or ""),
            profile_name=str(item.get("profile_name") or ""),
            documents=list(item.get("documents") or []),
            calc_mode=str(item.get("calc_mode") or ""),
            comments=str(item.get("comments") or ""),
            enabled_methods=[str(x) for x in (item.get("enabled_methods") or [])],
            applicability_rules_profile=str(item.get("applicability_rules_profile") or "RU_AUTO_CPT_V1"),
        )
        if prof.profile_id:
            out[prof.profile_id] = prof
    return out


def list_normative_profiles() -> list[NormativeProfile]:
    return list(load_normative_profiles().values())
