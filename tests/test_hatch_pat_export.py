import importlib.util
import json
from pathlib import Path


_MODULE_PATH = Path("tools/references/hatching/hatch_editor_live_v4_blob.py")
_SPEC = importlib.util.spec_from_file_location("hatch_editor_live_v4_blob", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
row_to_pat_descriptor = _MOD.row_to_pat_descriptor


def _load_graviy_rows():
    payload = json.loads(Path("src/zondeditor/assets/hatches/graviy.json").read_text(encoding="utf-8"))
    return payload["rows"]


def test_graviy_pat_row_keeps_local_origin_without_swap():
    row = _load_graviy_rows()[0]
    line = row_to_pat_descriptor(row, swap_local_axes=False)
    # angle, x, y, dx, dy, dash, gap
    parts = [x.strip() for x in line.split(",")]
    assert parts[:5] == ["45.000000", "4.136575", "0.318198", "0.000000", "-6.363961"]


def test_graviy_pat_row_changes_origin_if_forced_legacy_swap():
    row = _load_graviy_rows()[0]
    line = row_to_pat_descriptor(row, swap_local_axes=True)
    parts = [x.strip() for x in line.split(",")]
    assert parts[:5] == ["45.000000", "0.318198", "4.136575", "0.000000", "-6.363961"]
