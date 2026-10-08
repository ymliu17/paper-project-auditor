#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

ROLE_HINTS = {
    "manuscript": {".pdf", ".tex", ".docx"},
    "code": {".py", ".ipynb", ".r", ".R", ".m", ".jl", ".cpp", ".cc", ".c", ".h", ".hpp", ".java", ".scala", ".sh", ".bash", ".zsh", ".ps1"},
    "config": {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".xml"},
    "data": {".csv", ".tsv", ".parquet", ".feather", ".h5", ".hdf5", ".mat", ".npy", ".npz", ".pkl", ".pickle", ".jsonl"},
    "checkpoint": {".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".onnx"},
    "result": {".log", ".out", ".metrics", ".results"},
    "figure": {".png", ".jpg", ".jpeg", ".svg", ".eps", ".tif", ".tiff"},
    "archive": {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar"},
}

NAME_HINTS = {
    "manuscript": ["manuscript", "paper", "submission", "camera_ready", "camera-ready", "main.tex"],
    "supplement": ["supp", "supplement", "appendix"],
    "config": ["config", "args", "params", "hyperparam"],
    "result": ["result", "metric", "score", "eval", "evaluation", "table"],
    "figure": ["figure", "fig", "plot"],
    "environment": ["requirements", "environment", "lock", "dockerfile", "makefile", "pyproject", "setup.py", "setup.cfg", "renv", "sessioninfo"],
    "split": ["split", "fold"],
}

TEXT_EXTS = {
    ".txt", ".md", ".rst", ".tex", ".bib", ".py", ".ipynb", ".r", ".R", ".m", ".jl", ".c", ".cc", ".cpp", ".h", ".hpp", ".java", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".yaml", ".yml", ".json", ".jsonl", ".toml", ".ini", ".cfg", ".conf", ".xml", ".csv", ".tsv", ".log"
}


def sha256_file(path: Path, max_bytes: int) -> Optional[str]:
    try:
        if path.stat().st_size > max_bytes:
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def classify(rel: str, suffix: str) -> List[str]:
    low = rel.lower()
    roles = []
    for role, exts in ROLE_HINTS.items():
        if suffix in exts:
            roles.append(role)
    for role, hints in NAME_HINTS.items():
        if any(h in low for h in hints):
            roles.append(role)
    stem = Path(rel).stem.lower()
    if suffix in {".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".txt"} and stem in {"train", "val", "valid", "validation", "test"}:
        roles.append("split")
    if suffix in {".md", ".rst"} and any(h in low for h in ["manuscript", "paper", "submission"]):
        roles.append("manuscript")
    # De-duplicate while preserving order.
    seen = set()
    return [x for x in roles if not (x in seen or seen.add(x))]


def file_entry(root: Path, path: Path, hash_max_bytes: int) -> Dict:
    rel = path.relative_to(root).as_posix()
    try:
        st = path.lstat()
        is_link = path.is_symlink()
        target = os.readlink(path) if is_link else None
        suffix = path.suffix.lower()
        return {
            "path": rel,
            "name": path.name,
            "suffix": suffix,
            "size_bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns,
            "mode_octal": oct(st.st_mode & 0o7777),
            "is_symlink": is_link,
            "symlink_target": target,
            "sha256": None if is_link else sha256_file(path, hash_max_bytes),
            "hash_skipped": (not is_link and st.st_size > hash_max_bytes),
            "likely_text": suffix in TEXT_EXTS,
            "role_hints": classify(rel, suffix),
        }
    except OSError as e:
        return {"path": rel, "error": repr(e), "role_hints": classify(rel, path.suffix.lower())}


def main() -> int:
    p = argparse.ArgumentParser(description="Inventory every filesystem entry under a research project root.")
    p.add_argument("root", help="Project root directory")
    p.add_argument("--output", required=True, help="Output JSON path")
    p.add_argument("--hash-max-mb", type=float, default=256.0, help="Hash files up to this size; larger files are still inventoried")
    args = p.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    hash_max_bytes = int(args.hash_max_mb * 1024 * 1024)

    files = []
    dirs = []
    errors = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        d = Path(dirpath)
        for dn in sorted(dirnames):
            dp = d / dn
            rel = dp.relative_to(root).as_posix()
            try:
                st = dp.lstat()
                dirs.append({
                    "path": rel,
                    "is_symlink": dp.is_symlink(),
                    "symlink_target": os.readlink(dp) if dp.is_symlink() else None,
                    "mtime_ns": st.st_mtime_ns,
                })
            except OSError as e:
                errors.append({"path": rel, "error": repr(e)})
        for fn in sorted(filenames):
            fp = d / fn
            entry = file_entry(root, fp, hash_max_bytes)
            files.append(entry)
            if "error" in entry:
                errors.append({"path": entry["path"], "error": entry["error"]})

    role_counts: Dict[str, int] = {}
    for f in files:
        for role in f.get("role_hints", []):
            role_counts[role] = role_counts.get(role, 0) + 1

    payload = {
        "root": str(root),
        "file_count": len(files),
        "directory_count": len(dirs),
        "total_file_bytes": sum(int(f.get("size_bytes", 0)) for f in files),
        "hash_max_bytes": hash_max_bytes,
        "git_present": (root / ".git").exists(),
        "role_counts": role_counts,
        "directories": dirs,
        "files": files,
        "errors": errors,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "root": str(root),
        "files": len(files),
        "directories": len(dirs),
        "errors": len(errors),
        "role_counts": role_counts,
        "output": str(output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
