"""Modal 8-series .syx container: split into packets, pack/unpack payload, re-seal.

Packet framing (as produced by the official updater):

    start : F0 00 21 07 <MODEL> 00 <CHIP> 7F <cntL> <cntM> F7
    data  : F0 00 21 07 <MODEL> 00 <CHIP> 00 <idxL> <idxM> <payload155> <h> F7
    end   : F0 00 21 07 <MODEL> 00 <CHIP> 7E F7

MODEL is a single byte at offset 4 of every packet.
The byte before the terminating F7 of a data packet is the *high nibble* of an
integrity value computed from the payload only; the low nibble lives in the
low bits of the last payload byte.  It is a non-cryptographic checksum:

    cs = sum(unpack(payload)) & 0xFF
    h  = cs >> 4
    last_payload_byte = (last_payload_byte & 0x70) | (cs & 0x0F)

Editing a payload byte therefore requires re-sealing that packet.
"""
from __future__ import annotations


def split_packets(raw: bytes) -> list[bytearray]:
    out: list[bytearray] = []
    i = 0
    while i < len(raw):
        if raw[i] != 0xF0:
            raise ValueError(f"expected F0 at {i}, got {raw[i]:#x}")
        j = raw.index(0xF7, i)
        out.append(bytearray(raw[i:j + 1]))
        i = j + 1
    return out


def join_packets(packets: list[bytearray]) -> bytes:
    return b"".join(bytes(p) for p in packets)


def unpack(payload: bytes) -> bytes:
    """8 payload bytes (7-bit) -> 7 firmware bytes (8-bit)."""
    out = bytearray()
    for i in range(0, len(payload) - 7, 8):
        grp = payload[i:i + 8]
        msb = grp[7]
        for j in range(7):
            out.append(grp[j] | (((msb >> (6 - j)) & 1) << 7))
    return bytes(out)


def pack(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 7):
        grp = data[i:i + 7]
        while len(grp) < 7:
            grp += b"\x00"
        msb = 0
        for j, b in enumerate(grp):
            if b & 0x80:
                msb |= 1 << (6 - j)
        out += bytes(b & 0x7F for b in grp)
        out.append(msb)
    return bytes(out)


def packet_is_data(pkt: bytearray) -> bool:
    return len(pkt) >= 11 and pkt[7] == 0x00


def reseal(pkt: bytearray) -> None:
    """Recompute and store the payload integrity value of a data packet."""
    payload = bytearray(pkt[10:-2])
    cs = sum(unpack(bytes(payload))) & 0xFF
    payload[-1] = (payload[-1] & 0x70) | (cs & 0x0F)
    pkt[10:-2] = payload
    pkt[-2] = (cs >> 4) & 0x0F


def set_model_byte(packets: list[bytearray], model: int) -> int:
    n = 0
    for p in packets:
        if len(p) > 4 and p[4] != model:
            p[4] = model
            n += 1
    return n


def verify_seals(packets: list[bytearray]) -> int:
    bad = 0
    for p in packets:
        if not packet_is_data(p):
            continue
        payload = bytes(p[10:-2])
        cs = sum(unpack(payload)) & 0xFF
        if ((p[-2] << 4) | (payload[-1] & 0x0F)) & 0xFF != cs:
            bad += 1
    return bad
