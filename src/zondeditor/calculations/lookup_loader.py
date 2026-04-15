"""Lookup CSV loader for SP 446 static sounding calculation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
import csv

from .preview_model import LOOKUP_RELATIVE_PATH


class LookupFileError(FileNotFoundError):
    """Raised when the external lookup CSV cannot be resolved."""


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_lookup_path(relative_path: str = LOOKUP_RELATIVE_PATH) -> Path:
    candidate = _project_root() / relative_path
    if candidate.exists():
        return candidate
    raise LookupFileError(
        f"Не найден lookup-файл расчёта: {relative_path}. "
        f"Ожидался файл в папке проекта: {_project_root()}"
    )


def _parse_decimal(value: str) -> Decimal | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


@dataclass(frozen=True)
class LookupRule:
    rule_id: str
    edition_mode: str
    method: str
    appendix_table: str
    soil_group: str
    soil_kind_ru: str
    genetic_group: str
    state_or_consistency: str
    water_saturation: str
    depth_from_m: Decimal | None
    depth_to_m: Decimal | None
    qc_from_mpa: Decimal | None
    qc_to_mpa: Decimal | None
    output_param: str
    output_value_text: str
    output_value_num: Decimal | None
    calc_mode: str
    requires_checkbox: str
    result_status: str
    note_code: str
    priority: int


@dataclass(frozen=True)
class LookupDataset:
    source_path: Path
    rules: tuple[LookupRule, ...]


def _read_rows(path: Path) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline="") as handle:
                return list(csv.DictReader(handle, delimiter=";"))
        except UnicodeError:
            continue
    raise UnicodeError(f"Не удалось прочитать lookup CSV: {path}")


@lru_cache(maxsize=4)
def load_lookup_dataset(relative_path: str = LOOKUP_RELATIVE_PATH) -> LookupDataset:
    path = resolve_lookup_path(relative_path)
    raw_rows = _read_rows(path)
    rules: list[LookupRule] = []
    for raw in raw_rows:
        output_text = str(raw.get("output_value") or "").strip()
        rules.append(
            LookupRule(
                rule_id=str(raw.get("rule_id") or "").strip(),
                edition_mode=str(raw.get("edition_mode") or "").strip(),
                method=str(raw.get("method") or "").strip(),
                appendix_table=str(raw.get("appendix_table") or "").strip(),
                soil_group=str(raw.get("soil_group") or "").strip(),
                soil_kind_ru=str(raw.get("soil_kind_ru") or "").strip(),
                genetic_group=str(raw.get("genetic_group") or "").strip(),
                state_or_consistency=str(raw.get("state_or_consistency") or "").strip(),
                water_saturation=str(raw.get("water_saturation") or "").strip(),
                depth_from_m=_parse_decimal(str(raw.get("depth_from_m") or "")),
                depth_to_m=_parse_decimal(str(raw.get("depth_to_m") or "")),
                qc_from_mpa=_parse_decimal(str(raw.get("qc_from_mpa") or "")),
                qc_to_mpa=_parse_decimal(str(raw.get("qc_to_mpa") or "")),
                output_param=str(raw.get("output_param") or "").strip(),
                output_value_text=output_text,
                output_value_num=_parse_decimal(output_text),
                calc_mode=str(raw.get("calc_mode") or "").strip(),
                requires_checkbox=str(raw.get("requires_checkbox") or "").strip(),
                result_status=str(raw.get("result_status") or "").strip(),
                note_code=str(raw.get("note_code") or "").strip(),
                priority=int(str(raw.get("priority") or "0").strip() or 0),
            )
        )
    return LookupDataset(source_path=path, rules=tuple(rules))
