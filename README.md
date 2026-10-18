# crossflash-8

Run **Carbon 8** (and, by the same technique, **Argon 8**) firmware on a **Cobalt 8 / 8X**
unit over USB‑MIDI — **without shipping a single byte of Modal Electronics' firmware**.

This repository contains **only tooling**: a patcher that applies a handful of byte edits
to firmware files *you* already have, and a flasher that talks to the synth's bootloader.
No `.syx`/`.bin` firmware is included, and none ever needs to be.

---

## Read this first (legal)

* This is an **unofficial, community interoperability tool**. It is not affiliated with or
  endorsed by Modal Electronics.
* **You must supply your own official firmware.** This repo ships no firmware. The patcher
  verifies the SHA‑256 of your file and refuses anything it wasn't built for.
* The patch is **tiny and non‑expressive**: one header field on every packet plus **one
  instruction**. It contains no Modal source or significant code.
* Reverse engineering was done for **interoperability**, from **unencrypted** `.syx` files
  (plain MIDI SysEx, a non‑cryptographic checksum, no signature). No cryptographic
  protection was broken.
* **Cross‑flashing may void your warranty**, may prevent vendor servicing, and can brick the
  unit if interrupted. You do it entirely at your own risk. See `DISCLAIMER.md`.
* Modal's EULA may restrict running firmware on non‑corresponding hardware. That is a
  contract matter between you and Modal; this repo only provides tooling.
* This project is **not legal advice**.

---

## What the patch actually changes

| component | change |
|---|---|
| panel | packet **model byte** `0x1D → 0x19` on every packet, **plus one instruction**: `cmp r3,#0x1d → cmp r3,#0x19` (the model gate), then the packet is re‑sealed |
| master | packet **model byte** only (payload untouched) |
| slave | packet **model byte** only (payload untouched) |

The model byte goes to `0x19` because the Cobalt bootloader requires it. The single panel
instruction is the firmware's own "does the unit's model match my model?" check; patching it
makes the Carbon panel accept a `0x19` unit.

---

## Requirements: firmware you already possess, lawfully

This project **does not provide, download, link to, or help you obtain firmware**. It only
applies a small edit to files **you already have**.

To use it you must already possess the **official** source-model firmware (the three `.syx`
files) **in a way that is lawful for you** — for example because you own a device of that
model, or the vendor supplied them to you. It is **your** responsibility to ensure you are
entitled to use those files with your hardware, and to comply with any licence/EULA that
governs them.

The project supports exactly the releases named in `patches/` and **refuses everything else**
(the SHA‑256 gate). It does not include any acquisition tooling, firmware URLs, keys, or
bypass of encryption or signatures — see `COMPLIANCE.md` for the full reasoning.

Supported here: **the source firmware revision listed in the patch file** (currently Carbon 8
`1-1`). Other revisions have a different layout and are deliberately refused.


---

## Usage

```bash
git clone <this repo> && cd crossflash-8
python3 -m crossflash8.patcher \
    --patches patches/carbon8_1-1_to_cobalt8.json \
    --from ~/Downloads/carbon8_firmware \
    --out ./out
```

`out/` now holds a flashable set (`Carbon8_panel_1-1.syx`, `Carbon8_master_1-1.syx`,
`Carbon8_slave_1-1.syx`).

Put the synth into update mode (**power on holding SHIFT/INIT** → *"UPDATE / waiting for
MODALapp connection"*), then flash:

```bash
# Linux (ALSA, no extra deps)
python3 -m crossflash8.flash_alsa --dir ./out --pace-ms 20

# Windows / macOS / Linux (mido)
pip install mido python-rtmidi
python3 -m crossflash8.flash_mido --dir ./out --pace-ms 20
```

The unit reboots when all three components are accepted. **Do not unplug during the flash.**

### Windows

* The **patcher is pure standard library** and runs on Windows as‑is, e.g.
  `py -m crossflash8.patcher --patches patches\carbon8_1-1_to_cobalt8.json --from path\to\firmware --out .\out`.
* For **flashing**, use the cross‑platform backend (the ALSA one is Linux‑only):
  `py -m pip install mido python-rtmidi` then `py -m crossflash8.flash_mido --dir .\out`.
* `python-rtmidi` currently ships **prebuilt Windows wheels for Python 3.8–3.12**; use one of
  those (e.g. Python 3.12) so **no compiler is needed**. On 3.13+/3.14 there is no wheel yet.
* The synth shows up as a `CARBON8` / `COBALT8` / `ARGON8` … MIDI port; put it in update mode
  first, and make sure no other MIDI app (or the vendor app) has the port open.


### Troubleshooting

* **"missed firmware start packet" / timeouts** — this is usually pacing/hand‑off, not the
  patch. The flasher replies to the device's component requests immediately and re‑sends a
  component if the loader re‑requests it. If it still fails, re‑enter update mode and retry.
* **`.syx` from a different revision** — the SHA‑256 gate will refuse; that is intentional.

---

## Reverting to stock

The **bootloader is never modified**, so recovery is the same procedure with the official
Cobalt set: put the unit in update mode and serve `Cobalt8_panel/master/slave` (headers
`0x19`, no edits). Nothing in this repo is needed to go back.

Note on identity: while the patched firmware is **running**, the unit presents as the
cross‑flashed model (its USB‑audio card name and its reported model byte both change), which
is what the companion app sees. The **bootloader** (update mode) still presents the stock
model, so the update path and recovery are unaffected.

---

## Repository layout

```
crossflash8/
  syx.py          # .syx packet split/join, 7-bit pack/unpack, integrity re-seal
  patcher.py      # SHA-256-gated patcher (applies patches/*.json)
  flash_alsa.py   # Linux USB-MIDI flasher (ALSA rawmidi)
  flash_mido.py   # cross-platform flasher (mido + python-rtmidi)
patches/
  carbon8_1-1_to_cobalt8.json
DISCLAIMER.md
LICENSE
```

## Adding other models

The same recipe applies to Argon 8 (its panel's gate compares against its own model id).
To add one: build a patch that sets the model byte to the target unit's id and flips that
build's gate instruction to match, verify on hardware, then add a JSON entry with the
source file's SHA‑256. Worked example: `patches/carbon8_1-1_to_cobalt8.json`.

## Technical notes (for contributors)

* The updated image is **not** a flat dump: the on‑wire payload keeps **128 image bytes per
  135‑byte record** (7 framing bytes follow), and the app is linked at base **`0x00410000`**.
  Knowing this is what makes the string/pointer tables resolve.
* The per‑packet integrity value is a **non‑cryptographic** checksum of the payload; any
  payload edit must re‑seal the packet (the patcher does this).
* `20 ms` per message is required; `1 ms` fails with "missed firmware start packet".
