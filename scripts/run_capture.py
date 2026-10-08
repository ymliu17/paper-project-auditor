#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Optional


def sha256_file(path: Path, max_bytes: int) -> Optional[str]:
    try:
        if path.is_symlink() or path.stat().st_size > max_bytes:
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def snapshot(root: Path, max_hash_bytes: int) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    for p in root.rglob("*"):
        if not p.is_file() and not p.is_symlink():
            continue
        try:
            st = p.lstat()
            rel = p.relative_to(root).as_posix()
            out[rel] = {
                "size": st.st_size,
                "mtime_ns": st.st_mtime_ns,
                "is_symlink": p.is_symlink(),
                "sha256": sha256_file(p, max_hash_bytes),
            }
        except OSError:
            continue
    return out


def diff_snapshots(before: Dict[str, Dict], after: Dict[str, Dict]) -> Dict[str, list]:
    b = set(before)
    a = set(after)
    created = sorted(a - b)
    deleted = sorted(b - a)
    modified = []
    for k in sorted(a & b):
        if before[k] != after[k]:
            modified.append(k)
    return {"created": created, "modified": modified, "deleted": deleted}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one command without a shell and capture reproducibility metadata.")
    ap.add_argument("--cwd", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--timeout", type=float, default=3600.0)
    ap.add_argument("--snapshot-hash-max-mb", type=float, default=64.0)
    ap.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")
    args = ap.parse_args()

    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("No command supplied. Example: run_capture.py --cwd . --log run.json -- python train.py")

    cwd = Path(args.cwd).expanduser().resolve()
    if not cwd.is_dir():
        raise SystemExit(f"Not a directory: {cwd}")
    log_path = Path(args.log).expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    max_hash_bytes = int(args.snapshot_hash_max_mb * 1024 * 1024)

    before = snapshot(cwd, max_hash_bytes)
    start_wall = datetime.now(timezone.utc)
    start_mono = time.monotonic()
    timed_out = False
    exc = None
    stdout = ""
    stderr = ""
    returncode = None
    try:
        cp = subprocess.run(
            command,
            cwd=str(cwd),
            shell=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout,
            env=os.environ.copy(),
        )
        stdout = cp.stdout
        stderr = cp.stderr
        returncode = cp.returncode
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        returncode = 124
        exc = f"TimeoutExpired after {args.timeout} seconds"
    except Exception as e:
        returncode = 125
        exc = repr(e)

    end_wall = datetime.now(timezone.utc)
    duration = time.monotonic() - start_mono
    after = snapshot(cwd, max_hash_bytes)

    env_keys = [
        "PYTHONHASHSEED", "CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
        "CONDA_DEFAULT_ENV", "VIRTUAL_ENV", "R_ENVIRON_USER", "JULIA_PROJECT"
    ]
    selected_env = {k: os.environ[k] for k in env_keys if k in os.environ}

    payload = {
        "argv": command,
        "cwd": str(cwd),
        "start_utc": start_wall.isoformat(),
        "end_utc": end_wall.isoformat(),
        "duration_seconds": duration,
        "timeout_seconds": args.timeout,
        "timed_out": timed_out,
        "returncode": returncode,
        "exception": exc,
        "stdout": stdout,
        "stderr": stderr,
        "runtime": {
            "python_executable": sys.executable,
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "selected_environment": selected_env,
        "filesystem_changes": diff_snapshots(before, after),
    }
    log_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_seconds": round(duration, 6),
        "filesystem_changes": payload["filesystem_changes"],
        "log": str(log_path),
    }, indent=2))
    return int(returncode or 0)


if __name__ == "__main__":
    raise SystemExit(main())
