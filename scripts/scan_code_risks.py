#!/usr/bin/env python3
import argparse
import ast
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

CODE_EXTS = {".py", ".sh", ".bash", ".zsh", ".ps1", ".r", ".R", ".m", ".jl", ".ipynb"}
MAX_TEXT_BYTES = 8 * 1024 * 1024

PATTERNS: List[Tuple[str, str, str]] = [
    ("destructive_delete", r"\brm\s+-[A-Za-z]*r[A-Za-z]*f|shutil\.rmtree\s*\(|os\.(remove|unlink)\s*\(|Path\([^\n]*\)\.unlink\s*\(", "HIGH"),
    ("shell_execution", r"subprocess\.|os\.system\s*\(|shell\s*=\s*True|Runtime\.getRuntime\(\)\.exec", "MEDIUM"),
    ("dynamic_code", r"\beval\s*\(|\bexec\s*\(|importlib\.|__import__\s*\(", "MEDIUM"),
    ("network_http", r"requests\.(get|post|put|delete|request)\s*\(|urllib\.request|httpx\.|aiohttp\.|curl\s+|wget\s+", "MEDIUM"),
    ("network_socket", r"\bsocket\.(socket|create_connection)\s*\(", "MEDIUM"),
    ("external_download", r"torch\.hub\.load|hf_hub_download|snapshot_download|from_pretrained\s*\(|gdown\.|git\s+clone", "MEDIUM"),
    ("package_install", r"pip\s+install|conda\s+install|mamba\s+install|install\.packages\s*\(", "MEDIUM"),
    ("credential_access", r"AWS_(ACCESS_KEY|SECRET)|GOOGLE_APPLICATION_CREDENTIALS|api[_-]?key|secret[_-]?key|token\s*=\s*os\.environ|keyring\.", "HIGH"),
    ("absolute_user_path", r"/(home|Users)/[^/\s]+/|[A-Za-z]:\\Users\\", "LOW"),
]

RESULTISH_NAME = re.compile(r"(result|metric|score|table|figure|plot|report|paper)", re.I)
RESULTISH_VAR = re.compile(r"(result|metric|score|acc|accuracy|auc|f1|precision|recall|mean|std|table|figure)", re.I)


def iter_text_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink() and p.suffix in CODE_EXTS:
            try:
                if p.stat().st_size <= MAX_TEXT_BYTES:
                    yield p
            except OSError:
                continue


def numeric_literal_count(node: ast.AST) -> int:
    count = 0
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)) and not isinstance(child.value, bool):
            count += 1
    return count


def target_names(node: ast.AST) -> List[str]:
    out = []
    if isinstance(node, ast.Name):
        out.append(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for elt in node.elts:
            out.extend(target_names(elt))
    elif isinstance(node, ast.Attribute):
        out.append(node.attr)
    return out


def python_literal_findings(path: Path, text: str, rel: str) -> List[Dict]:
    findings = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return findings
    resultish_file = bool(RESULTISH_NAME.search(path.name))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None or not isinstance(value, (ast.List, ast.Tuple, ast.Dict, ast.Set, ast.Call)):
            continue
        nnums = numeric_literal_count(value)
        if nnums < 5:
            continue
        names = []
        if isinstance(node, ast.Assign):
            for t in node.targets:
                names.extend(target_names(t))
        else:
            names.extend(target_names(node.target))
        resultish_var = any(RESULTISH_VAR.search(n or "") for n in names)
        if resultish_file or resultish_var:
            findings.append({
                "category": "embedded_numeric_results_candidate",
                "severity": "LOW",
                "path": rel,
                "line": getattr(node, "lineno", None),
                "detail": f"Assignment contains {nnums} numeric literals; verify whether these are legitimate constants or manually embedded results.",
                "variables": names,
            })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Heuristic static scan for unsafe execution and result-provenance risks.")
    ap.add_argument("root")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    findings: List[Dict] = []
    scanned = 0
    unreadable = []
    for path in iter_text_files(root):
        scanned += 1
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            unreadable.append({"path": rel, "error": repr(e)})
            continue
        lines = text.splitlines()
        for category, regex, severity in PATTERNS:
            rx = re.compile(regex, re.I)
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    findings.append({
                        "category": category,
                        "severity": severity,
                        "path": rel,
                        "line": i,
                        "detail": line.strip()[:500],
                    })
        if path.suffix == ".py":
            findings.extend(python_literal_findings(path, text, rel))

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda x: (severity_order.get(x["severity"], 99), x["path"], x.get("line") or 0))
    payload = {
        "root": str(root),
        "scanned_code_files": scanned,
        "finding_count": len(findings),
        "note": "Heuristic findings are review leads, not conclusions. Confirm semantic behavior before assigning an audit status.",
        "findings": findings,
        "unreadable": unreadable,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"scanned_code_files": scanned, "findings": len(findings), "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
