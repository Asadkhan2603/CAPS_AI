from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS_DIR = ROOT / "backend" / "app" / "api" / "v1" / "endpoints"

FILES_FOR_UNREACHABLE_SCAN = [
    ROOT / "backend" / "app" / "api" / "v1" / "endpoints",
    ROOT / "backend" / "app" / "core",
    ROOT / "backend" / "app" / "services",
]

GOVERNANCE_DELETE_FILES = {
    "departments.py": "delete_department",
    "branches.py": "delete_branch",
    "years.py": "delete_year",
    "courses.py": "delete_course",
    "classes.py": "delete_class",
}


def iter_python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def is_terminal(stmt: ast.stmt) -> bool:
    return isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break))


def scan_stmt_list(statements: list[ast.stmt], path: Path, errors: list[str]) -> None:
    found_terminal = False
    for stmt in statements:
        if found_terminal and not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            errors.append(
                f"{path.relative_to(ROOT)}:{stmt.lineno}: unreachable statement after terminal control flow"
            )
            found_terminal = False

        if isinstance(stmt, ast.If):
            scan_stmt_list(stmt.body, path, errors)
            scan_stmt_list(stmt.orelse, path, errors)
        elif isinstance(stmt, (ast.For, ast.AsyncFor, ast.While)):
            scan_stmt_list(stmt.body, path, errors)
            scan_stmt_list(stmt.orelse, path, errors)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            scan_stmt_list(stmt.body, path, errors)
        elif isinstance(stmt, ast.Try):
            scan_stmt_list(stmt.body, path, errors)
            for handler in stmt.handlers:
                scan_stmt_list(handler.body, path, errors)
            scan_stmt_list(stmt.orelse, path, errors)
            scan_stmt_list(stmt.finalbody, path, errors)
        elif isinstance(stmt, ast.Match):
            for case in stmt.cases:
                scan_stmt_list(case.body, path, errors)

        if is_terminal(stmt):
            found_terminal = True


def scan_unreachable_code(errors: list[str]) -> None:
    for file_path in iter_python_files(FILES_FOR_UNREACHABLE_SCAN):
        module = ast.parse(file_path.read_text(encoding="utf-8-sig"), filename=str(file_path))
        scan_stmt_list(module.body, file_path, errors)


def has_delete_decorator(node: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
            if decorator.func.attr == "delete":
                return True
        elif isinstance(decorator, ast.Attribute) and decorator.attr == "delete":
            return True
    return False


def function_calls_name(node: ast.AST, function_name: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            target = child.func
            if isinstance(target, ast.Name) and target.id == function_name:
                return True
            if isinstance(target, ast.Attribute) and target.attr == function_name:
                return True
    return False


def scan_governance_delete_contract(errors: list[str]) -> None:
    for file_name, function_name in GOVERNANCE_DELETE_FILES.items():
        path = ENDPOINTS_DIR / file_name
        module = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        matched_function: ast.AsyncFunctionDef | ast.FunctionDef | None = None

        for node in module.body:
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == function_name:
                matched_function = node
                break

        if matched_function is None:
            errors.append(f"{path.relative_to(ROOT)}: missing expected delete handler {function_name}")
            continue

        if not has_delete_decorator(matched_function):
            errors.append(
                f"{path.relative_to(ROOT)}:{matched_function.lineno}: {function_name} is not decorated as a delete route"
            )

        arg_names = [arg.arg for arg in matched_function.args.args]
        kwonly_names = [arg.arg for arg in matched_function.args.kwonlyargs]
        if "review_id" not in {*arg_names, *kwonly_names}:
            errors.append(
                f"{path.relative_to(ROOT)}:{matched_function.lineno}: {function_name} is missing review_id parameter"
            )

        if not function_calls_name(matched_function, "enforce_review_approval"):
            errors.append(
                f"{path.relative_to(ROOT)}:{matched_function.lineno}: {function_name} does not enforce governance approval"
            )


def main() -> int:
    errors: list[str] = []
    scan_unreachable_code(errors)
    scan_governance_delete_contract(errors)

    if errors:
        print("Backend safety checks failed:")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Backend safety checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
