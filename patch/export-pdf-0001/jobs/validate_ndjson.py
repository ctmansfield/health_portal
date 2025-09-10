#!/usr/bin/env python3
import argparse, json, gzip, sys
from typing import IO


def opener(path: str) -> IO[bytes]:
    return gzip.open(path, "rb") if path.endswith(".gz") else open(path, "rb")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    total = bad = obs = pats = 0
    first_error = None
    with opener(args.file) as f:
        for i, bline in enumerate(f, start=1):
            try:
                obj = json.loads(bline.decode("utf-8"))
            except Exception as e:
                bad += 1
                if not first_error:
                    first_error = f"line {i}: {e}"
                continue
            total += 1
            rt = obj.get("resourceType")
            if rt == "Observation":
                obs += 1
            if rt == "Patient":
                pats += 1
            if not rt or not obj.get("id"):
                bad += 1
                if not first_error:
                    first_error = f"line {i}: missing resourceType or id"
    print(f"total={total} obs={obs} patient={pats} bad={bad}")
    if first_error:
        print(f"first_error={first_error}", file=sys.stderr)
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
