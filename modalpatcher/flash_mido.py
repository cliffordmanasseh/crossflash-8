"""Cross-platform flasher using mido + python-rtmidi (Windows / macOS / Linux).

    pip install mido python-rtmidi
    python -m modalpatcher.flash_mido --dir ./out

Same protocol/pacing as the ALSA backend: identify -> start -> serve each component
the bootloader requests, 20 ms per message, answering re-requests immediately.
"""
from __future__ import annotations
import argparse
import os
import sys
import time

from . import syx

IDENTIFY = [0x00, 0x21, 0x07, 0x64, 0x01, 0x01]      # payload without F0 .. F7
MODEL = 0x19
NAMES = {0: "panel", 1: "master", 2: "slave"}


def _sysex(msg) -> bytes:
    return bytes([0xF0]) + bytes(msg.data) + bytes([0xF7])


def flash(src: str, pace_ms: float = 20.0, total: float = 600.0) -> int:
    try:
        import mido
    except ImportError:
        sys.exit("mido not installed: pip install mido python-rtmidi")

    images: dict[int, list[bytes]] = {}
    for t, role in NAMES.items():
        fn = next((f for f in os.listdir(src) if f.lower().endswith(".syx")
                   and role in f.lower()), None)
        if not fn:
            sys.exit(f"no {role} .syx in {src}")
        images[t] = [bytes(p) for p in syx.split_packets(open(os.path.join(src, fn), "rb").read())]

    names = [n for n in mido.get_ioport_names() if "COBALT" in n.upper()]
    if not names:
        names = [n for n in mido.get_ioport_names() if "MODAL" in n.upper()]
    if not names:
        sys.exit("no COBALT MIDI port found; is the synth in UPDATE mode?")
    name = names[0]
    print(f"port {name}")

    pace = pace_ms / 1000.0
    t0 = time.time()
    served: set[int] = set()
    runs: dict[int, int] = {}
    pending = None

    def handle(msg) -> None:
        nonlocal pending
        if msg.type != "sysex":
            return
        m = _sysex(msg)
        t = time.time() - t0
        print(f"[{t:7.1f}] dev {m.hex(' ').upper()}")
        if len(m) >= 7 and m[5] == 0x7C:
            pending = m[6]
        elif len(m) >= 8 and m[5] == 0x7D:
            print(f"        DEVICE ERROR {m[6]} (state {m[7]})")

    def send_image(port, t: int) -> None:
        data = images[t]
        runs[t] = runs.get(t, 0) + 1
        print(f"[{time.time()-t0:7.1f}] ==> sending {NAMES[t]} ({len(data)} msgs)")
        for pkt in data:
            port.send(mido.Message("sysex", data=list(pkt[1:-1])))
            time.sleep(pace)

    with mido.open_ioport(name) as port:
        port.send(mido.Message("sysex", data=IDENTIFY))
        time.sleep(1.0)
        port.send(mido.Message("sysex", data=[0x00, 0x21, 0x07, MODEL, 0x01, 0x04, 0x01]))
        deadline = time.time() + total
        while time.time() < deadline and len(served) < len(images):
            for msg in port.iter_pending():
                handle(msg)
            if pending is not None and pending in images:
                t = pending
                pending = None
                send_image(port, t)
                served.add(t)
            time.sleep(0.02)
        print(f"finished. served {sorted(served)} runs={runs}")
        return 0 if len(served) == len(images) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Flash a patched Modal set over USB-MIDI (mido)")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--pace-ms", type=float, default=20.0)
    ap.add_argument("--total", type=float, default=600.0)
    a = ap.parse_args(argv)
    return flash(a.dir, a.pace_ms, a.total)


if __name__ == "__main__":
    raise SystemExit(main())
