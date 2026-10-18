"""Apply a cross-flash patch to *user-supplied* official Modal .syx files.

Nothing copyrighted is shipped with this tool: the user points it at the official
firmware they already have, the tool verifies the SHA-256, edits a handful of
bytes, re-seals the affected packet, and writes a flashable set.

    python -m modalpatcher.patcher \
        --patches patches/carbon8_1-1_to_cobalt8.json \
        --from ~/Downloads/carbon8_firmware \
        --out  ./out
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys

from . import syx


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_input(src_dir: str, filename: str) -> str | None:
    for root, _dirs, files in os.walk(os.path.expanduser(src_dir)):
        if filename in files:
            return os.path.join(root, filename)
    return None


def apply_file(src: str, spec: dict, out_dir: str) -> str:
    want = spec.get("sha256")
    got = sha256_file(src)
    if want and got != want:
        raise SystemExit(
            f"checksum mismatch for {os.path.basename(src)}\n"
            f"  expected {want}\n  got      {got}\n"
            f"This is a different firmware revision; refusing to patch."
        )
    packets = syx.split_packets(open(src, "rb").read())

    model = spec.get("model_byte")
    if model is not None:
        n = syx.set_model_byte(packets, model)
        print(f"  {spec['role']:6}: set model byte on {n} packets -> {model:#04x}")

    data_idx = [i for i, p in enumerate(packets) if syx.packet_is_data(p)]
    for e in spec.get("edits", []):
        dp = e["data_packet"]
        if dp >= len(data_idx):
            raise SystemExit(f"{spec['role']}: data packet {dp} out of range")
        p = packets[data_idx[dp]]
        payload = bytearray(p[10:-2])
        pidx = e["payload_index"]
        old = payload[pidx]
        payload[pidx] = e["value"]
        p[10:-2] = payload
        if e.get("reseal", True):
            syx.reseal(p)
        print(f"  {spec['role']:6}: packet {dp} payload[{pidx}] "
              f"{old:#04x} -> {e['value']:#04x}  ({e.get('what','')})")

    bad = syx.verify_seals(packets)
    if bad:
        raise SystemExit(f"{spec['role']}: {bad} packets failed re-seal")

    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, os.path.basename(src))
    open(dst, "wb").write(syx.join_packets(packets))
    print(f"  {spec['role']:6}: wrote {dst}")
    return dst


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Patch official Modal .syx for cross-flash")
    ap.add_argument("--patches", required=True)
    ap.add_argument("--from", dest="src", required=True, help="folder holding the official .syx files")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    spec = json.load(open(args.patches))
    print(f"patch: {spec['description']}")
    print(f"target: {spec['target_model_name']} (model byte {spec['target_model_byte']:#04x})")
    for f in spec["files"]:
        f = dict(f, model_byte=spec["target_model_byte"])
        src = find_input(args.src, f["filename"])
        if not src:
            sys.exit(f"could not find {f['filename']} under {args.src}")
        apply_file(src, f, args.out)
    print("\ndone. out/ contains a flashable set (panel, master, slave).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
