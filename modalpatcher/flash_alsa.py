"""Serve a patched 3-component set to the Modal bootloader over ALSA raw-MIDI (Linux).

Implements the reverse-engineered update handshake:

    host -> dev   identify   F0 00 21 07 64 01 01 F7
    dev  -> host             F0 00 21 07 <model> 01 7D 00 04 01 01 F7
    host -> dev   start      F0 00 21 07 19 01 04 01 F7
    dev  -> host  request    F0 00 21 07 19 7C <type> F7      0=panel 1=master 2=slave
    host -> dev   image      the component's .syx, split on F7
    dev  -> host  progress   CC#127 = 0x78 (received) then 0x77 (installed)
    dev   reboots after all three are served

20 ms per message is the sweet spot: faster causes "missed firmware start packet".
"""
from __future__ import annotations
import argparse
import fcntl
import os
import select
import sys
import time

from . import syx

IDENTIFY = bytes([0xF0, 0x00, 0x21, 0x07, 0x64, 0x01, 0x01, 0xF7])
MODEL = 0x19
NAMES = {0: "panel", 1: "master", 2: "slave"}


# ---------------------------------------------------------------- ALSA helpers
def _cards() -> dict[int, str]:
    out = {}
    try:
        for ln in open("/proc/asound/cards"):
            if ":" in ln and "[" in ln:
                idx = int(ln.split()[0])
                out[idx] = ln
    except OSError:
        pass
    return out


def find_port() -> str | None:
    """Any Modal 8-series USB-MIDI card.  The bootloader (update mode) presents as the
    stock product name; the running application presents as its own (possibly
    cross-flashed) name, so match all of them."""
    want = ("CARBON", "COBALT", "ARGON", "MODAL")
    for idx, desc in _cards().items():
        if any(w in desc.upper() for w in want):
            return f"hw:{idx},0,0"
    return None


def node_for(port: str) -> str:
    a = port.replace("hw:", "").split(",")
    return f"/dev/snd/midiC{a[0]}D{a[1] if len(a) > 1 else 0}"


def wwrite(fd: int, data: bytes) -> None:
    """Write a whole raw-MIDI message, honouring EAGAIN."""
    mv = memoryview(data)
    while mv:
        try:
            n = os.write(fd, mv)
            mv = mv[n:]
        except BlockingIOError:
            select.select([], [fd], [], 0.5)


# ------------------------------------------------------------------- protocol
class Session:
    def __init__(self, fd: int, images: dict[int, list[bytes]], pace_ms: float):
        self.fd = fd
        self.images = images
        self.pace = pace_ms / 1000.0
        self.buf = b""
        self.t0 = time.time()
        self.served: set[int] = set()
        self.runs: dict[int, int] = {}
        self.pending: int | None = None
        self.saw_hello = False

    def feeds(self, data: bytes):
        self.buf += data
        b = self.buf
        i = 0
        while i < len(b):
            x = b[i]
            if x == 0xF0:
                j = b.find(b"\xF7", i + 1)
                if j < 0:
                    break
                yield ("sysex", b[i:j + 1])
                i = j + 1
            elif x >= 0xF8:
                i += 1
            elif x & 0x80:
                hi = x & 0xF0
                need = {0x80: 2, 0x90: 2, 0xA0: 2, 0xB0: 2, 0xC0: 1, 0xD0: 1, 0xE0: 2}.get(hi)
                if need is None or i + 1 + need > len(b):
                    i += 1
                    continue
                d = b[i + 1:i + 1 + need]
                if hi == 0xB0:
                    yield ("cc", x & 0x0F, d[0], d[1])
                i += 1 + need
            else:
                i += 1
        self.buf = b[i:]

    def handle(self, e) -> None:
        t = time.time() - self.t0
        if e[0] == "cc":
            _, ch, num, val = e
            print(f"[{t:7.1f}] dev CC #{num} = {val:#04x}")
        else:
            m = e[1]
            print(f"[{t:7.1f}] dev {m.hex(' ').upper()}")
            if len(m) >= 7 and m[5] == 0x7C:
                self.pending = m[6]
            elif len(m) >= 7 and m[5] == 0x01 and m[6] == 0x7D:
                self.saw_hello = True
            elif len(m) >= 8 and m[5] == 0x7D:
                print(f"        DEVICE ERROR {m[6]} (state {m[7]})")
            elif len(m) >= 7 and m[5] == 0x01 and m[6] == 0x02:
                wwrite(self.fd, bytes([0xF0, 0x00, 0x21, 0x07, MODEL, 0x01, 0x04, 0x01, 0xF7]))

    def pump(self, sec: float, stop_on_request: bool = True) -> None:
        end = time.time() + sec
        while time.time() < end:
            if stop_on_request and self.pending is not None:
                return
            r, _, _ = select.select([self.fd], [], [], 0.02)
            if not r:
                continue
            try:
                for e in self.feeds(os.read(self.fd, 16384)):
                    self.handle(e)
            except OSError:
                return

    def send_image(self, t: int) -> None:
        data = self.images[t]
        self.runs[t] = self.runs.get(t, 0) + 1
        print(f"[{time.time()-self.t0:7.1f}] ==> sending {NAMES[t]} "
              f"({len(data)} msgs @ {self.pace*1000:.0f} ms)")
        for m in data:
            wwrite(self.fd, m)
            time.sleep(self.pace)
        print(f"[{time.time()-self.t0:7.1f}] <== {NAMES[t]} sent")
        # brief listen; answer any request immediately (retry or next component)
        self.pump(0.30)


def flash(src: str, pace_ms: float = 20.0, total: float = 600.0) -> int:
    import os.path
    images: dict[int, list[bytes]] = {}
    for t, role in NAMES.items():
        fn = next((f for f in os.listdir(src) if f.lower().endswith(".syx")
                   and role in f.lower()), None)
        if not fn:
            sys.exit(f"no {role} .syx in {src}")
        images[t] = [bytes(p) for p in syx.split_packets(open(os.path.join(src, fn), "rb").read())]

    port = find_port()
    if not port:
        sys.exit("no COBALT sound card found; is the synth in UPDATE mode?")
    node = node_for(port)
    print(f"port {port} ({node})")
    fd = os.open(node, os.O_RDWR | os.O_NONBLOCK)
    try:
        s = Session(fd, images, pace_ms)
        for _ in range(5):                       # identify + confirm update mode
            wwrite(fd, IDENTIFY)
            s.pump(0.5)
            if s.saw_hello:
                break
        if not s.saw_hello:
            sys.exit("device did not answer the update handshake — put it in UPDATE mode "
                     "(power on holding SHIFT/INIT until it says 'waiting for MODALapp "
                     "connection') and retry")
        print("device is in update mode")
        wwrite(fd, bytes([0xF0, 0x00, 0x21, 0x07, MODEL, 0x01, 0x04, 0x01, 0xF7]))
        deadline = time.time() + total
        while time.time() < deadline and len(s.served) < len(images):
            s.pump(0.05, stop_on_request=False)
            if s.pending is not None and s.pending in images:
                t = s.pending
                s.pending = None
                s.send_image(t)
                s.served.add(t)
        print(f"finished. served {sorted(s.served)} runs={s.runs}")
        return 0 if len(s.served) == len(images) else 1
    finally:
        os.close(fd)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Flash a patched Modal set over USB-MIDI (Linux/ALSA)")
    ap.add_argument("--dir", required=True)
    ap.add_argument("--pace-ms", type=float, default=20.0)
    ap.add_argument("--total", type=float, default=600.0)
    a = ap.parse_args(argv)
    return flash(a.dir, a.pace_ms, a.total)


if __name__ == "__main__":
    raise SystemExit(main())
