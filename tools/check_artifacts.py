"""Offline artifact gate: verify the analysed binaries are still the recorded build.

Every VA, RVA and bit-width site in `data/` and `reports/` is bound to one exact
build of three DLLs. This script recomputes SHA-256 and size for each of them and
reports whether the recorded coordinates are still valid for what is on disk.

The game install is read-only; nothing here writes to it.

  python tools/check_artifacts.py            # verify
  python tools/check_artifacts.py --record    # write full hashes back for the current files

Exit codes:
  0  every recorded file matched (and every expected hash is a full hash)
  1  a recorded file exists but its digest or size differs from the record
  2  a recorded file is missing (external drive not mounted, or install moved)
  3  unmatched record only because an expected full hash has not been recorded yet

`data/artifacts.json` is the record. A field may legitimately be `null` while it
has not been captured yet; such a field is reported as unrecorded rather than as
a match, so the gate never turns "I did not check" into "it is fine".
"""
import argparse
import hashlib
import json
import os
import sys

import config

RECORD = os.path.join(config.DATA, "artifacts.json")

# record key -> resolved path from config
PATHS = {
    "engine.dll": config.ENGINE_DLL,
    "server.dll": config.SERVER_DLL,
    "client.dll": config.CLIENT_DLL,
}

CHUNK = 1 << 20


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def load_record():
    if not os.path.isfile(RECORD):
        raise SystemExit(
            "missing record: %s\n"
            "the repository ships it; restore it from git:\n"
            "  git checkout -- data/artifacts.json" % RECORD
        )
    with open(RECORD, "r", encoding="utf-8") as f:
        return json.load(f)


def save_record(record):
    with open(RECORD, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
        f.write("\n")


def inspect(entry, path):
    """Compare one file against its record. Returns (status, detail)."""
    if not os.path.isfile(path):
        return "missing", path

    size = os.path.getsize(path)
    digest = sha256_of(path)

    want_size = entry.get("size")
    want_hash = entry.get("sha256")
    want_prefix = entry.get("sha256_prefix")

    if want_size is not None and size != want_size:
        return "mismatch", "size %d != recorded %d" % (size, want_size)

    if want_hash:
        if digest != want_hash:
            return "mismatch", "sha256 %s.. != recorded %s.." % (digest[:16], want_hash[:16])
        return "match", "%d B, sha256 %s.." % (size, digest[:16])

    if want_prefix:
        if not digest.startswith(want_prefix):
            return "mismatch", "sha256 %s.. does not start with %s" % (digest[:16], want_prefix)
        return "prefix-only", "%d B, sha256 %s.. (full hash unrecorded)" % (size, digest[:16])

    return "unrecorded", "%d B, sha256 %s.. (no expectation stored)" % (size, digest[:16])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--record",
        action="store_true",
        help="write the observed size and full sha256 back into data/artifacts.json",
    )
    args = ap.parse_args()

    record = load_record()
    files = record.setdefault("files", {})

    print("build %s  record %s" % (record.get("build", "?"), os.path.relpath(RECORD)))
    print()

    worst = 0  # 0 ok, 3 unrecorded/prefix, 2 missing, 1 mismatch
    observed = {}

    for name, path in PATHS.items():
        entry = files.setdefault(name, {})
        status, detail = inspect(entry, path)
        observed[name] = detail

        marker = {
            "match": "OK      ",
            "prefix-only": "PREFIX  ",
            "unrecorded": "NO-REC  ",
            "missing": "MISSING ",
            "mismatch": "MISMATCH",
        }[status]
        print("%s %-11s %s" % (marker, name, detail))

        if status == "mismatch":
            worst = max(worst, 1)
        elif status == "missing":
            worst = max(worst, 2)
        elif status in ("prefix-only", "unrecorded"):
            worst = max(worst, 3)

    print()

    if args.record:
        for name, path in PATHS.items():
            if not os.path.isfile(path):
                continue
            entry = files.setdefault(name, {})
            entry["size"] = os.path.getsize(path)
            entry["sha256"] = sha256_of(path)
            entry.pop("sha256_prefix", None)
        save_record(record)
        print("recorded full size + sha256 for every file present on disk")
        return 0

    if worst == 0:
        print("all recorded coordinates are valid for this build")
    elif worst == 1:
        print("a file differs from the record: every VA / RVA / bit-width site is stale")
    elif worst == 2:
        print("a file is missing: mount the install drive, then run --record only after")
        print("confirming the build is still 23990068")
    else:
        print("at least one file has no full hash in the record")
        print("run --record once on a build you have already confirmed, then commit the record")

    return worst


if __name__ == "__main__":
    sys.exit(main())
