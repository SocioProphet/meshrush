#!/usr/bin/env python3
"""Vendor-freshness sentinel — keep vendored schemas from silently drifting.

Every ``vendor/<dep>/PROVENANCE.json`` pins the upstream repo, ref, and per-file
sha256. This tool re-fetches each pinned file from upstream (GitHub contents API)
and compares it to the vendored copy, so a change in an upstream contract cannot
go unnoticed. It is the automatic half of vendoring: the conformance gate proves
we emit valid frames, and this proves the schema we validate against is current.

Modes:
  --check   (default) fail (exit 3) if any vendored file drifts from upstream, or
            if the pinned sha256 no longer matches the vendored bytes (tamper).
  --write   refresh drifted vendored files in place and update PROVENANCE hashes
            (used by the scheduled workflow to open an auto-update PR).

Auth: uses ``GITHUB_TOKEN``/``GH_TOKEN`` if set (required for private upstream).
Covers every vendor/<dep> automatically — add a dep, it is watched with no code change.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor"


def _repo_slug(url: str) -> str:
    return url.rstrip("/").removeprefix("https://github.com/")


def _fetch_upstream(repo: str, ref: str, path: str) -> bytes:
    api = f"https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
    req = urllib.request.Request(api, headers={"Accept": "application/vnd.github.raw+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read()
    # raw media type returns bytes directly; JSON fallback carries base64 content.
    try:
        doc = json.loads(body)
        if isinstance(doc, dict) and doc.get("encoding") == "base64":
            return base64.b64decode(doc["content"])
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return body


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="refresh drifted files + hashes")
    args = ap.parse_args()

    if not VENDOR.exists():
        print("no vendor/ directory; nothing to check")
        return 0

    drift: list[str] = []
    tamper: list[str] = []
    errors: list[str] = []
    changed = False

    for prov_path in sorted(VENDOR.glob("*/PROVENANCE.json")):
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        repo = _repo_slug(prov["vendored_from"])
        ref = prov["ref"]
        dep_dir = prov_path.parent
        for entry in prov.get("files", []):
            vfile = dep_dir / entry["path"]
            upstream_path = entry.get("upstream_path", entry["path"])
            local_bytes = vfile.read_bytes()
            local_sha = _sha256(local_bytes)
            label = f"{dep_dir.name}/{entry['path']}"

            # Tamper: vendored bytes must match the pinned hash.
            if local_sha != entry["sha256"]:
                tamper.append(f"{label}: vendored bytes != pinned sha256")

            try:
                up_bytes = _fetch_upstream(repo, ref, upstream_path)
            except (urllib.error.URLError, KeyError) as exc:
                errors.append(f"{label}: could not fetch upstream {repo}@{ref}:{upstream_path} ({exc})")
                continue
            up_sha = _sha256(up_bytes)
            if up_sha != local_sha:
                drift.append(f"{label}: upstream {up_sha[:12]} != vendored {local_sha[:12]}")
                if args.write:
                    vfile.write_bytes(up_bytes)
                    entry["sha256"] = up_sha
                    changed = True
        if args.write and changed:
            prov_path.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")

    for line in tamper:
        print(f"TAMPER: {line}", file=sys.stderr)
    for line in drift:
        print(f"DRIFT:  {line}", file=sys.stderr)
    for line in errors:
        print(f"ERROR:  {line}", file=sys.stderr)

    if args.write:
        print("refreshed" if changed else "already current")
        return 0
    if tamper or drift or errors:
        print("vendor freshness FAILED (see above); run tools/check_vendor_freshness.py --write", file=sys.stderr)
        return 3
    print("OK: all vendored schemas current and untampered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
