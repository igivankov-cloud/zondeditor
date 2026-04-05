from src.zondeditor.io.excel_import_detect import MODE_BLOCKS_RIGHT, MODE_VERTICAL
from src.zondeditor.io.excel_importer import (
    ExcelImportConfig,
    WorkbookSheet,
    build_import_preview,
    make_unique_names,
)


def test_vertical_type1_import():
    rows = [
        ["служебная", None, None],
        ["Глубина", "Лоб", "Общее"],
        [0.0, 10, 12],
        [0.2, 11, 13],
    ]
    sheet = WorkbookSheet(name="Лист1", rows=rows)
    cfg = ExcelImportConfig(
        mode=MODE_VERTICAL,
        header_row=2,
        data_start_row=3,
        column_roles={0: "depth", 1: "lob", 2: "obshee"},
    )
    preview = build_import_preview(sheet, cfg, fallback_name="demo")
    assert preview.detected_type == 1
    assert len(preview.soundings) == 1
    assert preview.soundings[0].rows[0].values["lob"] == 10


def test_blocks_right_qc_fs_multiple_soundings():
    rows = [
        ["Глубина", "qc", "fs", "qc", "fs"],
        [0.0, 1.0, 2.0, 10.0, 20.0],
        [0.1, 1.1, 2.1, 10.1, 20.1],
    ]
    sheet = WorkbookSheet(name="Sheet", rows=rows)
    cfg = ExcelImportConfig(
        mode=MODE_BLOCKS_RIGHT,
        header_row=1,
        data_start_row=2,
        column_roles={0: "depth", 1: "qc_mpa", 2: "fs_kpa"},
        repeat_first_block=True,
    )
    preview = build_import_preview(sheet, cfg, fallback_name="demo")
    assert preview.detected_type == 3
    assert len(preview.soundings) == 2


def test_empty_cells_preserved_as_none():
    rows = [["Глубина", "Лоб", "Общее"], [0.0, 1, None], [0.2, None, 3]]
    sheet = WorkbookSheet(name="Sheet", rows=rows)
    cfg = ExcelImportConfig(
        mode=MODE_VERTICAL,
        header_row=1,
        data_start_row=2,
        column_roles={0: "depth", 1: "lob", 2: "obshee"},
    )
    preview = build_import_preview(sheet, cfg, fallback_name="demo")
    assert preview.soundings[0].rows[0].values["obshee"] is None
    assert preview.soundings[0].rows[1].values["lob"] is None


def test_repeated_header_inside_data_is_skipped():
    rows = [
        ["Глубина", "qc", "fs"],
        [0.0, 1, 2],
        ["Глубина", "qc", "fs"],
        [0.1, 1.2, 2.3],
    ]
    sheet = WorkbookSheet(name="Sheet", rows=rows)
    cfg = ExcelImportConfig(
        mode=MODE_VERTICAL,
        header_row=1,
        data_start_row=2,
        column_roles={0: "depth", 1: "qc_mpa", 2: "fs_kpa"},
    )
    preview = build_import_preview(sheet, cfg, fallback_name="demo")
    assert len(preview.soundings[0].rows) == 2


def test_duplicate_names_are_suffixed():
    out = make_unique_names({"СЗ-2"}, ["СЗ-1", "СЗ-2", "СЗ-2"])
    assert out == ["СЗ-1", "СЗ-2 (2)", "СЗ-2 (3)"]
