# Compliance posture

This file records **why** the project is packaged the way it is, and the rules that keep it
that way. It is engineering diligence, **not legal advice**.

## What this project is

Tooling that applies a **small, documented edit** to firmware files the user already lawfully
possesses, so that firmware can run on hardware the user owns. It is an **interoperability /
personal-use** tool.

## What this project deliberately does NOT do (and must never do)

| Never add | Why |
|---|---|
| Vendor firmware images (`.syx`, `.bin`, hex, zipped images, test fixtures containing them) | The whole point of patch-only distribution: no vendor code is copied. Keep it that way. |
| A downloader / mirroring tool / firmware URLs for other products | Would turn the project into an acquisition + cross-flash pipeline, the most exposed possible framing. Users must obtain firmware themselves. |
| Decryption keys, DRM/key-extraction, signature-bypass code | Creates anti-circumvention (§1201 / EU InfoSoc) exposure where there is currently almost none. The firmware here is unencrypted SysEx with a non-cryptographic checksum. |
| Decoded/annotated vendor source, large binary blobs, or generated code from vendor images | Same copyright concern as shipping firmware. |
| The vendor's name/logo as the project's brand, or any implication of endorsement | Trademark. Descriptive references ("runs <product> firmware on <product>") are nominative use; branding is not. |

## Why the residual copyright exposure is minimal

* **No vendor code is distributed.** The repository contains only an interpreter for the
  container format, a patcher, flashers, and a JSON file of *offsets and values*.
* **The patch is non-expressive.** It changes a single header field on each packet, plus
  **one instruction** in one image. Offsets and byte values are facts, not creative content.
* **Users bring their own copy** and the patch refuses any file whose SHA‑256 doesn't match
  the exact intended release, so it cannot be repurposed as a distribution channel.

## Why the anti-circumvention exposure is minimal

* The `.syx` container is **plain MIDI SysEx**: 7‑bit packing (a transport requirement, not
  encryption) plus a **non-cryptographic** integrity nibble. Disassembly is direct.
* The bootloader verified **no signature**; the update path needs no key. **Nothing
  cryptographic was broken** to produce this work.
* What the patch adjusts is a **compatibility/identity check** (and a checksum), not copy
  protection or access control.

## The residual risks the maintainer cannot engineer away

1. **Contract/EULA.** A vendor EULA may restrict using firmware on non-corresponding
   hardware or forbid modification. That is between the user and the vendor; the README and
   DISCLAIMER say so plainly.
2. **Purpose framing.** A vendor may still object that the tool's purpose is to run their
   software on hardware it wasn't licensed for, and may send a takedown/C&D regardless of
   the merits.
3. **Warranty / support.** Cross‑flashing may void warranties; documented in `DISCLAIMER.md`.

## Automated guardrails in this repo

* `.gitignore` excludes `out/`, `*.syx`, `*.bin` so firmware-derived artifacts cannot be
  committed by accident.
* `tools/check_no_firmware.py` fails if any firmware-like blob is staged/tracked.
* `git config core.hooksPath .githooks` enables a `pre-commit` hook that runs that check
  (see `CONTRIBUTING.md`).

## If you receive a complaint

There is nothing infringing to remove (no vendor code). The reasonable response is to
clarify intent, state the interoperability purpose, and — if asked — remove the specific
patch entry or the project, which costs nothing legally because no vendor content is hosted.
