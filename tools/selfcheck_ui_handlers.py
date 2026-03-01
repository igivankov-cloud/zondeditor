from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR_PATH = ROOT / "src" / "zondeditor" / "ui" / "editor.py"
RIBBON_PATH = ROOT / "src" / "zondeditor" / "ui" / "ribbon.py"


def _self_attr_names(node: ast.AST) -> set[str]:
    names: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Attribute(self, n: ast.Attribute) -> None:
            if isinstance(n.value, ast.Name) and n.value.id == "self":
                names.add(n.attr)
            self.generic_visit(n)

    Visitor().visit(node)
    return names


def extract_editor_command_handlers() -> dict[str, set[str]]:
    tree = ast.parse(EDITOR_PATH.read_text(encoding="utf-8"), filename=str(EDITOR_PATH))
    handlers_by_key: dict[str, set[str]] = {}

    class Visitor(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign) -> None:
            if any(isinstance(t, ast.Name) and t.id == "commands" for t in node.targets) and isinstance(node.value, ast.Dict):
                for k_node, v_node in zip(node.value.keys, node.value.values):
                    if not isinstance(k_node, ast.Constant) or not isinstance(k_node.value, str):
                        continue
                    key = k_node.value
                    handlers_by_key.setdefault(key, set()).update(_self_attr_names(v_node))
            self.generic_visit(node)

    Visitor().visit(tree)
    return handlers_by_key


def extract_ribbon_command_keys() -> set[str]:
    tree = ast.parse(RIBBON_PATH.read_text(encoding="utf-8"), filename=str(RIBBON_PATH))
    keys: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Attribute) and node.func.attr == "_add_btn":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    keys.add(node.args[1].value)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "_add_qat_btn":
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                    keys.add(node.args[1].value)
            self.generic_visit(node)

    Visitor().visit(tree)
    return keys


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from src.zondeditor.ui.editor import GeoCanvasEditor

    ribbon_keys = extract_ribbon_command_keys()
    handlers_by_key = extract_editor_command_handlers()

    print("[INFO] UI handler selfcheck")
    print(f"[INFO] Ribbon command keys: {len(ribbon_keys)}")

    errors = 0
    for key in sorted(ribbon_keys):
        names = sorted(handlers_by_key.get(key, set()))
        if key not in handlers_by_key:
            print(f"ERR key={key}: no mapping in editor.commands")
            errors += 1
            continue
        if not names:
            print(f"OK  key={key}: inline callable/lambda")
            continue
        for name in names:
            method = getattr(GeoCanvasEditor, name, None)
            if callable(method):
                print(f"OK  key={key}: self.{name}")
            else:
                print(f"ERR key={key}: self.{name} (missing/non-callable)")
                errors += 1

    extra_keys = sorted(set(handlers_by_key) - ribbon_keys)
    if extra_keys:
        print(f"[WARN] commands mapped but not used by Ribbon: {', '.join(extra_keys)}")

    if errors:
        print(f"[FAIL] UI handlers check failed: {errors} issue(s)")
        return 1

    print("[OK] UI handlers check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
