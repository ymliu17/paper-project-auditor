#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

NUM_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def compare_scalars(a: Any, b: Any, atol: float, rtol: float) -> Dict[str, Any]:
    if is_num(a) and is_num(b):
        av = float(a)
        bv = float(b)
        diff = abs(av - bv)
        tol = atol + rtol * abs(av)
        return {"equal": diff <= tol, "expected": av, "observed": bv, "abs_diff": diff, "tolerance": tol}
    return {"equal": a == b, "expected": a, "observed": b}


def flatten_json(obj: Any, prefix: str = "$") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k in sorted(obj):
            out.update(flatten_json(obj[k], f"{prefix}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(flatten_json(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def read_csv(path: Path, delimiter: str) -> List[List[str]]:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.reader(f, delimiter=delimiter))


def maybe_number(s: str) -> Any:
    t = s.strip()
    try:
        if t and re.fullmatch(NUM_RE, t):
            return float(t)
    except ValueError:
        pass
    return s


def compare_json(a: Path, b: Path, atol: float, rtol: float) -> Dict[str, Any]:
    fa = flatten_json(json.loads(a.read_text(encoding="utf-8")))
    fb = flatten_json(json.loads(b.read_text(encoding="utf-8")))
    keys = sorted(set(fa) | set(fb))
    mismatches = []
    for k in keys:
        if k not in fa or k not in fb:
            mismatches.append({"key": k, "missing_in": "expected" if k not in fa else "observed"})
            continue
        c = compare_scalars(fa[k], fb[k], atol, rtol)
        if not c["equal"]:
            c["key"] = k
            mismatches.append(c)
    return {"kind": "json", "equal": not mismatches, "mismatches": mismatches, "compared_values": len(keys)}


def compare_table(a: Path, b: Path, delimiter: str, atol: float, rtol: float) -> Dict[str, Any]:
    ra = read_csv(a, delimiter)
    rb = read_csv(b, delimiter)
    mismatches = []
    rows = max(len(ra), len(rb))
    for i in range(rows):
        if i >= len(ra) or i >= len(rb):
            mismatches.append({"row": i, "missing_in": "expected" if i >= len(ra) else "observed"})
            continue
        cols = max(len(ra[i]), len(rb[i]))
        for j in range(cols):
            if j >= len(ra[i]) or j >= len(rb[i]):
                mismatches.append({"row": i, "col": j, "missing_in": "expected" if j >= len(ra[i]) else "observed"})
                continue
            c = compare_scalars(maybe_number(ra[i][j]), maybe_number(rb[i][j]), atol, rtol)
            if not c["equal"]:
                c.update({"row": i, "col": j})
                mismatches.append(c)
    return {"kind": "table", "equal": not mismatches, "mismatches": mismatches, "rows_expected": len(ra), "rows_observed": len(rb)}


def compare_text_numbers(a: Path, b: Path, atol: float, rtol: float) -> Dict[str, Any]:
    ta = a.read_text(encoding="utf-8", errors="replace")
    tb = b.read_text(encoding="utf-8", errors="replace")
    na = [float(x) for x in NUM_RE.findall(ta)]
    nb = [float(x) for x in NUM_RE.findall(tb)]
    mismatches = []
    n = max(len(na), len(nb))
    for i in range(n):
        if i >= len(na) or i >= len(nb):
            mismatches.append({"index": i, "missing_in": "expected" if i >= len(na) else "observed"})
            continue
        c = compare_scalars(na[i], nb[i], atol, rtol)
        if not c["equal"]:
            c["index"] = i
            mismatches.append(c)
    return {
        "kind": "text_numeric_sequence",
        "equal": (not mismatches and ta == tb) if not na and not nb else not mismatches,
        "numeric_count_expected": len(na),
        "numeric_count_observed": len(nb),
        "exact_text_equal": ta == tb,
        "mismatches": mismatches,
    }


def compare_numpy(a: Path, b: Path, atol: float, rtol: float) -> Dict[str, Any]:
    try:
        import numpy as np
    except Exception as e:
        return {"kind": "numpy", "equal": False, "error": f"NumPy unavailable: {e!r}"}
    aa = np.load(a, allow_pickle=False)
    bb = np.load(b, allow_pickle=False)
    if hasattr(aa, "files") or hasattr(bb, "files"):
        if not (hasattr(aa, "files") and hasattr(bb, "files")):
            return {"kind": "npz", "equal": False, "error": "One file is NPZ and the other is not"}
        keys = sorted(set(aa.files) | set(bb.files))
        mismatches = []
        for k in keys:
            if k not in aa.files or k not in bb.files:
                mismatches.append({"key": k, "missing_in": "expected" if k not in aa.files else "observed"})
                continue
            x = aa[k]
            y = bb[k]
            if x.shape != y.shape:
                mismatches.append({"key": k, "shape_expected": list(x.shape), "shape_observed": list(y.shape)})
                continue
            if np.issubdtype(x.dtype, np.number) and np.issubdtype(y.dtype, np.number):
                if not np.allclose(x, y, atol=atol, rtol=rtol, equal_nan=True):
                    d = np.abs(x.astype(float) - y.astype(float))
                    mismatches.append({"key": k, "max_abs_diff": float(np.nanmax(d))})
            elif not np.array_equal(x, y):
                mismatches.append({"key": k, "equal": False})
        return {"kind": "npz", "equal": not mismatches, "mismatches": mismatches}
    if aa.shape != bb.shape:
        return {"kind": "npy", "equal": False, "shape_expected": list(aa.shape), "shape_observed": list(bb.shape)}
    if aa.dtype.kind in "biufc" and bb.dtype.kind in "biufc":
        eq = bool(np.allclose(aa, bb, atol=atol, rtol=rtol, equal_nan=True))
        diff = np.abs(aa.astype(float) - bb.astype(float))
        return {"kind": "npy", "equal": eq, "shape": list(aa.shape), "max_abs_diff": float(np.nanmax(diff)) if diff.size else 0.0}
    return {"kind": "npy", "equal": bool(np.array_equal(aa, bb)), "shape": list(aa.shape)}


def compare_one(a: Path, b: Path, atol: float, rtol: float) -> Dict[str, Any]:
    suffix = a.suffix.lower()
    if suffix != b.suffix.lower():
        return {"kind": "extension_mismatch", "equal": False, "expected_suffix": suffix, "observed_suffix": b.suffix.lower()}
    if suffix == ".json":
        return compare_json(a, b, atol, rtol)
    if suffix == ".csv":
        return compare_table(a, b, ",", atol, rtol)
    if suffix == ".tsv":
        return compare_table(a, b, "\t", atol, rtol)
    if suffix in {".npy", ".npz"}:
        return compare_numpy(a, b, atol, rtol)
    return compare_text_numbers(a, b, atol, rtol)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare expected and reproduced result files or matching trees.")
    ap.add_argument("expected")
    ap.add_argument("observed")
    ap.add_argument("--output", required=True)
    ap.add_argument("--atol", type=float, default=1e-8)
    ap.add_argument("--rtol", type=float, default=1e-6)
    args = ap.parse_args()

    expected = Path(args.expected).expanduser().resolve()
    observed = Path(args.observed).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    comparisons = []
    if expected.is_file() and observed.is_file():
        comparisons.append({"path": expected.name, **compare_one(expected, observed, args.atol, args.rtol)})
    elif expected.is_dir() and observed.is_dir():
        efiles = {p.relative_to(expected).as_posix(): p for p in expected.rglob("*") if p.is_file()}
        ofiles = {p.relative_to(observed).as_posix(): p for p in observed.rglob("*") if p.is_file()}
        for rel in sorted(set(efiles) | set(ofiles)):
            if rel not in efiles or rel not in ofiles:
                comparisons.append({"path": rel, "equal": False, "missing_in": "expected" if rel not in efiles else "observed"})
            else:
                comparisons.append({"path": rel, **compare_one(efiles[rel], ofiles[rel], args.atol, args.rtol)})
    else:
        raise SystemExit("Both inputs must be files or both must be directories")

    equal = all(c.get("equal", False) for c in comparisons)
    payload = {
        "expected": str(expected),
        "observed": str(observed),
        "atol": args.atol,
        "rtol": args.rtol,
        "equal": equal,
        "comparisons": comparisons,
    }
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"equal": equal, "comparisons": len(comparisons), "output": str(output)}, indent=2))
    return 0 if equal else 1


if __name__ == "__main__":
    raise SystemExit(main())
