# crossflash-8 — complete usage guide

Everything from a clean machine to a flashed unit: environment setup, preparing the patched set,
entering update mode, performing the flash, verifying it, recovering from problems, and the
reference details behind the commands.

**Deliberately not covered: how to obtain firmware.** This project ships none and provides no
acquisition path. You must already have the official source‑model files (see *Read this first*
in the [README](../README.md)).

---

## 0. Ten‑second summary

```bash
git clone <this repo> && cd crossflash-8

# 1. patch your own official files
python3 -m crossflash8.patcher \
    --patches patches/carbon8_1-1_to_cobalt8.json \
    --from /path/to/your/official/syx --out ./out

# 2. power the synth OFF, hold SHIFT/INIT, power ON
#    screen should read:  UPDATE / waiting for MODALapp connection

# 3. flash
python3 -m crossflash8.flash_alsa --dir ./out --pace-ms 20   # Linux
python3 -m crossflash8.flash_mido --dir ./out --pace-ms 20   # macOS / Windows / Linux
```

The rest of this document explains those steps, and how to tell success from failure.

---

## 1. What you need

| | |
|---|---|
| **the synth** | the target unit — e.g. a Cobalt 8 / 8X |
| **USB cable** | a **data** cable (not charge‑only); a direct port is preferred over an unpowered hub |
| **computer** | Linux, macOS or Windows |
| **Python** | **3.8 or newer** — see §3 for the recommended version per OS |
| **firmware** | the **official source‑model** `.syx` files you already have: three files for the same revision, named like `..._panel_...syx`, `..._master_...syx`, `..._slave_...syx` |
| **time** | ~10 minutes. The flash itself is **3–4 minutes** of uninterrupted power and USB |

---

## 2. Which flasher to use

| your OS | backend | extra install |
|---|---|---|
| **Linux** | `crossflash8.flash_alsa` | **none** — standard library only, talks to ALSA raw‑MIDI |
| **macOS** | `crossflash8.flash_mido` | `mido` + `python-rtmidi` |
| **Windows** | `crossflash8.flash_mido` | `mido` + `python-rtmidi` |

The **patcher is standard‑library only** and identical on all three platforms. Only the flasher
differs: Linux can talk to `/dev/snd/midi*` directly, so it needs nothing; macOS and Windows go
through `mido`/`python-rtmidi`.

---

## 3. Environment setup

### 3.1 Get the code (all platforms)

```bash
git clone <this repo> && cd crossflash-8
```

No build step, no `pip install`, nothing to compile for the Linux path. If you don't use git,
downloading the repository as a ZIP and unpacking it works identically (`crossflash-8-main/`).

Optional but recommended if you might contribute — enable the pre‑commit firmware guard:

```bash
git config core.hooksPath .githooks     # blocks accidental firmware commits
python3 tools/check_no_firmware.py      # run manually any time: "OK (no firmware blobs found)"
```

An optional virtual environment keeps any `mido` install out of your system Python:

```bash
python3 -m venv .venv && . .venv/bin/activate     # Windows: py -m venv .venv && .venv\Scripts\activate
```

### 3.2 Linux

Nothing to install for the flasher itself. Two things to check:

**a) Can your user open the MIDI device?** The device nodes are usually `root:audio` with
`crw-rw----`, but on most desktop distributions your logged‑in user is granted access
automatically (a systemd‑logind ACL). Confirm:

```bash
ls -l /dev/snd/midiC*D*
amidi -l                      # from alsa-utils; lists "COBALT8 MIDI 1" etc.
```

If `amidi` lists the port, you have access. If you get **permission denied**, either add yourself
to the `audio` group and log out/in, or add a udev rule:

```bash
sudo usermod -aG audio "$USER"        # then log out and back in
```

**b) Is anything else holding the port?** Close the vendor's companion app, DAWs, `amidi`,
`aconnect`, and any other MIDI software before flashing — a second reader on the port is the
most common cause of flaky transfers.

### 3.3 macOS

macOS has no ALSA, so use the `mido` backend:

```bash
python3 -m pip install --user mido python-rtmidi
python3 -c "import mido; print(mido.get_ioport_names())"     # sanity check
```

Use **Python 3.8–3.12**: `python-rtmidi` publishes prebuilt wheels for those versions, so no
compiler is needed. On 3.13+ there is no wheel yet and the install would build from source
(needs Apple's Xcode command line tools). No special permissions are required for CoreMIDI.

### 3.4 Windows

Use the **python.org** installer for **Python 3.8–3.12** (wheels exist for those; 3.13+ would
need a C++ build toolchain), then:

```bat
py -m pip install --user mido python-rtmidi
py -c "import mido; print(mido.get_ioport_names())"
```

The synth appears as a `CARBON8` / `COBALT8` / `ARGON8` … MIDI port. Close the vendor app and
any DAW first — on Windows a port held by another process typically just won't open.

> If your only Python is 3.13/3.14, the clean workaround is to flash from **Linux** with the
> ALSA backend, which has no dependencies at all.

### 3.5 Confirm you are ready

```bash
python3 -m crossflash8.patcher --help        # patcher CLI
python3 -m crossflash8.flash_alsa --help     # Linux flasher CLI
python3 -m crossflash8.flash_mido --help     # mido flasher CLI (needs mido installed)
```

---

## 4. Step 1 — prepare the patched set

Put your three official `.syx` files for the supported revision in one folder (they can be
anywhere; the patcher is told where to look), then:

```bash
python3 -m crossflash8.patcher \
    --patches patches/carbon8_1-1_to_cobalt8.json \
    --from /path/to/your/official/syx \
    --out ./out
```

A successful run looks like this:

```
panel : packet 1277 payload[102] 0x1d -> 0x19  (cmp r3,#0x1d -> cmp r3,#0x19  (model gate). clean VMA 0x437EDA, padded VMA 0x42A1C5)
panel : wrote ./out/Carbon8_panel_1-1.syx
master: set model byte on 3742 packets -> 0x19
master: wrote ./out/Carbon8_master_1-1.syx
slave : set model byte on 3029 packets -> 0x19
slave : wrote ./out/Carbon8_slave_1-1.syx

done. out/ contains a flashable set (panel, master, slave).
```

`out/` now holds the three files the flasher serves. **`out/` is git‑ignored** — keep it that
way; never commit patched (or original) firmware anywhere.

### The SHA‑256 gate

Each source file's **SHA‑256 must match the patch specification exactly**. If your files are a
different revision, the patcher writes nothing and tells you so:

```
got      1fb7a595fc221cf3457360ffcb7dd79dd45b5328a34b070b2e7dab89e91541b3
This is a different firmware revision; refusing to patch.
```

That is intentional and is the reason a wrong or mixed‑revision set can't produce a broken
image. If you hit it, you have the wrong source revision — the layout differs between releases
and the patch deliberately covers only the revision named in `patches/`.

---

## 5. Step 2 — pre‑flight checklist

Thirty seconds of preparation avoids the only failure modes that matter:

- [ ] **Close everything that touches MIDI** — vendor companion app, DAW, DAW helper services.
- [ ] **Prevent sleep/suspend** for the next ~10 minutes: Linux `systemd-inhibit --what=sleep:idle --why=flashing sleep 600`,
      macOS `caffeinate -i`, Windows: set the power plan to keep the machine awake.
- [ ] **Use a direct USB port** if possible; avoid unpowered hubs and docking‑station chains.
- [ ] **Leave the cable and power alone** once the flash starts. The unit reboots itself at the end.
- [ ] **Know your escape route**: if anything fails, the unit can be put back into update mode and
      re‑flashed (see §9 and §10). Nothing in this process is a one‑way door.

---

## 6. Step 3 — put the synth into update mode

1. Power the synth **off**.
2. Hold **SHIFT/INIT** (the button) and **power on** while holding it.
3. The screen reads **`UPDATE / waiting for MODALapp connection`**. Release the button.

Confirm from the computer that the *bootloader* port is present:

```bash
amidi -l                                   # Linux
python3 -c "import mido; print(mido.get_ioport_names())"   # macOS / Windows
```

You should see the unit's stock model name (e.g. `COBALT8 MIDI 1`) — the bootloader reports the
hardware's real model, not the cross‑flashed one. That's expected and is what makes recovery
straightforward.

> **The flasher will refuse if you skip this step.** It identifies the device first and requires
> the bootloader's update handshake. If the normal application firmware is running instead, it
> stops with `device did not answer the update handshake` rather than sending packets at an app
> that can't receive them. That guard is deliberate — don't work around it.

---

## 7. Step 4 — flash

```bash
# Linux
python3 -m crossflash8.flash_alsa --dir ./out --pace-ms 20

# macOS / Windows / Linux
python3 -m crossflash8.flash_mido --dir ./out --pace-ms 20
```

You should see something like this (annotated):

```
port hw:3,0,0 (/dev/snd/midiC3D0)                             <- port found
[    0.0] dev F0 00 21 07 19 01 7D 00 04 01 01 F7             <- bootloader handshake
device is in update mode
[    0.5] dev F0 00 21 07 19 7C 02 F7                         <- device requests component 2 (slave)
[    0.6] ==> sending slave (3029 msgs @ 20 ms)
[   61.4] <== slave sent
[   61.4] dev CC #127 = 0x78                                  <- device begins programming
[  101.2] dev CC #127 = 0x77                                  <- done
[  101.3] dev F0 00 21 07 19 7C 01 F7                         <- requests component 1 (master)
[  101.3] ==> sending master (3742 msgs @ 20 ms)
[  176.5] <== master sent
[  176.5] dev CC #127 = 0x78
[  179.5] dev CC #127 = 0x77
[  179.5] dev CC #127 = 0x78
[  181.7] dev F0 00 21 07 19 7C 00 F7                         <- requests component 0 (panel)
[  181.8] ==> sending panel (1949 msgs @ 20 ms)
[  220.9] <== panel sent
[  220.9] dev CC #127 = 0x77
finished. served [0, 1, 2] runs={2: 1, 1: 1, 0: 1}
```

What matters:

* **The device drives the sequence.** It asks for each component in turn (slave → master →
  panel); the flasher answers, then waits for the next request. You never choose the order.
* **`CC #127` messages are the device's own progress/status output.** `0x78`/`0x77` pairs
  indicate programming activity and completion. They are normal.
* **`runs=` shows retries.** `{2: 1, 1: 1, 0: 1}` means each component was sent exactly once.
  If the loader re‑requests one, the flasher re‑sends it immediately and the count rises — it
  does not treat that as an error.
* **`served [0, 1, 2]` plus exit code 0 is success.** Anything less exits non‑zero.

Typical timing (measured, at the default 20 ms pacing):

| stage | messages | sending | device‑side programming |
|---|---|---|---|
| slave | 3029 | ~61 s | ~40 s |
| master | 3742 | ~75 s | ~5 s |
| panel | 1949 | ~39 s | to completion |
| **total** | | | **~3 min 40 s** — allow up to ~6 minutes |

When all three components are accepted, **the unit reboots by itself**. Don't unplug it — let it
come up.

---

## 8. Step 5 — verify

* The synth reboots and comes up running the **patched (source‑model) application**: its panel
  behaves as that model, and the USB card/port name changes to the source model, e.g.:

  ```bash
  amidi -l
  #  IO  hw:3,0,0  CARBON8 MIDI 1      <- was COBALT8 before
  ```

* **Optional identity check.** The application answers a broadcast identify request
  (`F0 00 21 07 64 01 01 F7`); the fifth byte of its reply is the model byte it believes it is
  (`0x1D` = Carbon). On Linux, using the repo's own helpers:

  ```bash
  python3 - <<'EOF'
  import os, select, sys, time
  sys.path.insert(0, ".")
  from crossflash8.flash_alsa import IDENTIFY, find_port, node_for, wwrite
  fd = os.open(node_for(find_port()), os.O_RDWR | os.O_NONBLOCK)
  end, b = time.time() + 2.0, b""
  while time.time() < end and not b:
      wwrite(fd, IDENTIFY); time.sleep(0.25)
      while select.select([fd], [], [], 0)[0]:
          b += os.read(fd, 4096)
  os.close(fd)
  print("reply:", b.hex(" ").upper(), "model byte:", hex(b[4]) if b else "no reply")
  EOF
  ```

  On macOS/Windows (with `mido` installed):

  ```bash
  python3 - <<'EOF'
  import mido, time
  n = [x for x in mido.get_ioport_names()
       if any(w in x.upper() for w in ("CARBON", "COBALT", "ARGON", "MODAL"))][0]
  with mido.open_ioport(n) as port:
      port.send(mido.Message("sysex", data=[0x00, 0x21, 0x07, 0x64, 0x01, 0x01]))
      end = time.time() + 2
      while time.time() < end:
          for m in port.iter_pending():
              if m.type == "sysex":
                  print("reply:", " ".join(f"{x:02X}" for x in m.data),
                        "model byte:", hex(m.data[3]))
                  raise SystemExit
          time.sleep(0.05)
      print("no reply")
  EOF
  ```

  The same request sent to the **bootloader** (update mode) answers with the stock model byte
  (`0x19`) and its `7D` handshake — which is exactly how the flasher confirms it is safe to write.

If the unit boots and plays, you're done. If it doesn't, see below — it is recoverable.

---

## 9. Troubleshooting

| symptom | likely cause | what to do |
|---|---|---|
| `no Modal 8-series sound card found` | synth not in update mode, cable is charge‑only, or a hub/USB problem | re‑enter update mode (§6), try a direct port and another cable |
| `device did not answer the update handshake` | the *application* is running, not the bootloader | power‑cycle holding **SHIFT/INIT** — this refusal is the guard working |
| `DEVICE ERROR 9 (state …)` | timed out: pacing too fast, or something else is reading the port | close MIDI apps, keep `--pace-ms 20` or raise to 25–30, retry |
| `DEVICE ERROR 10 …` | "missed firmware start packet" — pacing too fast (1 ms reliably fails) | use ≥ `--pace-ms 20` |
| `DEVICE ERROR 11 …` | second‑stage timeout | retry from update mode; raise pacing if it repeats |
| flasher exits non‑zero, `served` is missing a component | incomplete run (port contention, hub glitch) | re‑enter update mode and run it again; partial writes are simply overwritten |
| `Permission denied` opening `/dev/snd/midi…` (Linux) | user lacks device access | see §3.2 — `audio` group / udev rule |
| port won't open on Windows | another process holds the MIDI port | close the vendor app, DAWs, and any MIDI monitors |
| flash interrupted, unit won't boot | the write didn't finish | the bootloader is untouched: power on holding SHIFT/INIT and flash again (§10) |

Nothing in this list requires a special recovery tool. The worst case is always "put it back into
update mode and flash again".

---

## 10. Reverting to stock

The **bootloader is never written**, so recovery is the ordinary procedure with the stock set:

1. Power on holding **SHIFT/INIT** → `UPDATE / waiting for MODALapp connection`.
2. Serve the **unmodified official files for the unit's own model** (no patching at all) with the
   same flasher:

   ```bash
   python3 -m crossflash8.flash_alsa --dir /path/to/stock/cobalt/syx --pace-ms 20
   ```

Nothing from this repository is required to go back — and no patched file is involved in a
revert, which is why it's the recommended escape route if you ever want to return the unit.

---

## 11. Why a failed flash is recoverable

* **Only three images are ever written** — `panel`, `master`, `slave` — and only when the device
  requests them. The update path never writes the bootloader or any other region.
* **Update mode is entered before any application code runs**, from a key combination at
  power‑on. It does not depend on the (possibly bad) application image, its model check, or the
  USB descriptors it would otherwise publish.
* Therefore an interrupted, refused, or even corrupted application write still leaves a unit that
  can enter update mode and be re‑flashed.

The same mechanism is what makes the cross‑flash possible in the first place: the bootloader is
model‑agnostic apart from the identity byte it insists on — which is exactly what the patch
supplies.

---

## 12. Reference

### 12.1 Patcher

```
python3 -m crossflash8.patcher --patches PATCH.json --from SRC_DIR --out OUT_DIR
```

| option | meaning |
|---|---|
| `--patches` | path to a `patches/*.json` specification (source SHA‑256 + edits) |
| `--from` | folder holding **your** official `.syx` files (any three, matched by role in the filename) |
| `--out` | folder to write the patched set into (created if missing) |

Writes, per component: `Carbon8_panel_1-1.syx`, `Carbon8_master_1-1.syx`, `Carbon8_slave_1-1.syx`.
Refuses (writing nothing, exit non‑zero) if a source file's SHA‑256 doesn't match the spec.

### 12.2 Flasher

```
python3 -m crossflash8.flash_alsa --dir DIR [--pace-ms 20] [--total 600]
python3 -m crossflash8.flash_mido --dir DIR [--pace-ms 20] [--total 600]
```

| option | default | meaning |
|---|---|---|
| `--dir` | *required* | folder holding the patched set (the `out/` from §4) |
| `--pace-ms` | `20` | milliseconds between SysEx messages. **Do not go below 20**; raise to 25–30 if a transfer is flaky |
| `--total` | `600` | overall timeout in seconds before giving up |

Exit codes: **0** = all components served and accepted; **non‑zero** = incomplete (re‑run from
update mode).

### 12.3 What the tools verify before writing anything

* **Patcher:** SHA‑256 of each source file against the patch spec. Mismatch ⇒ refuses, writes nothing.
* **Flasher:** that a Modal 8‑series port exists, and that the device answers the **update‑mode
  handshake**. If the application firmware is running instead, it stops rather than sending.
  Only after that does it answer the device's component requests.

None of this is a cryptographic signature check — the firmware format has no signature and no
encryption (plain SysEx, non‑cryptographic checksum). These are *safety* guards, not DRM: they
exist so that a wrong file, wrong revision, or wrong device state fails loudly instead of
producing a brick.

### 12.4 Protocol notes (why the defaults are what they are)

* The set is plain **MIDI SysEx**, three files, ~1.4 MB total.
* The device requests components one at a time; each is a stream of packets carrying a 7‑bit
  unpacked payload with a per‑packet integrity value (a simple checksum — any payload edit
  requires re‑sealing that packet, which the patcher does).
* **Pacing matters:** the bootloader is a full‑speed USB device with a small buffer. 20 ms per
  message is required in practice; 1 ms fails with "missed firmware start packet".
* The flasher answers the loader's re‑requests immediately within a short retry window, which is
  why a single glitch doesn't abort a run.

---

## 13. Still stuck?

Open an issue with:

* your OS and Python version (`python3 -V`),
* the flasher output **including the `[  time]` lines and any `DEVICE ERROR`**,
* which stage it stopped at and what the synth's screen showed,
* whether you're using `flash_alsa` or `flash_mido`.

**Do not attach firmware files, decoded images, or dumps** — issues are public, and this project
never carries vendor firmware.
