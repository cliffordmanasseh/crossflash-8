# Scope — what this project is, and what it deliberately does not do

This file records **why** the project is packaged the way it is, and the rules that keep it that
way. It is engineering notes about how the tool is built and what will and will not be added to
it — nothing more.

## What this project is

Tooling that applies a **small, documented edit** to firmware files that **you** supply, so that
an image can run on the unit you own. It is an **interoperability / personal-use** tool.

## What this project deliberately does NOT do (and must never do)

| Never add | Why |
|---|---|
| Vendor firmware images (`.syx`, `.bin`, hex, zipped images, test fixtures containing them) | Patch-only distribution is the whole point: no vendor file is ever copied into this repository. |
| A downloader, a mirror, or firmware URLs | That would turn the project into a firmware-acquisition pipeline. You bring your own files. |
| Decryption, key extraction, or signature-bypass code | There is nothing encrypted or signed here to get past: the container is plain MIDI SysEx with a simple checksum (see below). Adding such code would create a problem that does not currently exist. |
| Decoded or annotated vendor images, large binary blobs, generated code from vendor images | Same reason as shipping firmware: it would put vendor bytes in the repository. |
| The vendor's name or logo as the project's brand, or any implication of endorsement | A project name shouldn't look like the vendor's own. Describing what the tool interoperates with is just describing what it does. |

## Why this repository can't be mistaken for a firmware distribution channel

* **No vendor code is distributed.** It contains an interpreter for the container format, a
  patcher, two flashers, and a JSON file of *offsets and values*.
* **The edit is tiny and factual.** One header field on every packet, plus **one instruction**
  in one image. Offsets and byte values are facts.
* **The SHA-256 gate makes it useless as a distribution channel.** The patcher refuses any file
  that isn't the exact intended release, and it writes only into a folder on your own machine.

## Nothing cryptographic was bypassed

* The `.syx` container is **plain MIDI SysEx**: 7-bit packing (a transport requirement, not
  encryption) plus a **non-cryptographic** integrity nibble. Disassembly is direct.
* The bootloader checks **no signature**, and the update path uses no key.
* What the patch adjusts is a **compatibility/identity check** (plus the packet checksum that the
  edit invalidates) — not copy protection, and not access control.

## Risks that cannot be engineered away

1. **Vendor intent.** The vendor may not intend its firmware to run on other models, and may say
   so. That is between you and the vendor; `README.md` and `DISCLAIMER.md` say as much.
2. **Framing.** The vendor may object to the tool's purpose regardless of what it actually
   ships, and may ask for a takedown. Packaging cannot prevent a request like that. What
   packaging *can* guarantee is that there is no vendor file to remove.
3. **Support and servicing.** Cross-flashing may affect vendor support and servicing;
   documented in `DISCLAIMER.md`.

## Automated guardrails in this repository

* `.gitignore` excludes `out/`, `*.syx`, `*.bin`, so firmware-derived artifacts cannot be
  committed by accident.
* `tools/check_no_firmware.py` fails if any firmware-like blob is staged or tracked.
* `git config core.hooksPath .githooks` enables a `pre-commit` hook that runs that check
  (see `CONTRIBUTING.md`).

## What the vendor publishes (checked 2026-10-18)

Findings — **no firmware-specific terms are published for firmware or the companion app**:

* The website footer links only its Terms page and a Privacy Policy; the companion-app page has
  no similar link.
* `MODALapp.exe` contains **no terms text** (the only strings of that kind relate to embedded
  fonts).
* No bundled text/PDF terms in the application bundle.

The only public vendor text of this kind is the **Website Terms** page (last updated
10 Jan 2025). What it covers, and why it doesn't reach this project:

| clause | text (abridged) | relevance |
|---|---|---|
| Website material | refers to "material on this website" | firmware isn't website material — and this repo ships none |
| Distribution | "No copying or distribution of material on this website for any **commercial or business use** …" | scoped to website material **and** commercial use; this project is free, non-commercial, and ships no firmware |
| Conduct | rules about how visitors use the site | applies to people using the site |
| Claims | site users cover claims arising from *their use of the site* | not aimed at third-party tools |

Notes:

* We found **no term about the firmware itself** that would prohibit modifying it or running it
  on other hardware, so "you agreed not to do this" doesn't have much to stand on.
* The companion app is distributed through the Apple App Store, whose standard terms cover
  **the app** — not the device firmware. This project ships nothing derived from the app and
  never touches the app itself (a protocol or an interface is not creative content the way code
  is).
* Support and servicing are a separate commercial matter; cross-flashing may affect them — see
  `DISCLAIMER.md`.
* The design stays what it is: no vendor code, patch-only, user-supplied files, SHA-256-gated.

## Where the firmware comes from (checked 2026-10-18)

* Officially, the vendor points users at **its companion app** to update a unit; the product
  pages carry a "Firmware — update via <app>" line and there is **no standalone firmware
  download page**.
* In practice the vendor **hosts the official `.syx` files on its own server and serves them
  without any sign-in** (the files respond `200` with matching sizes; only the server's
  directory listing is blocked). It is the same endpoint the companion app uses.

What that means here:

* Users get the **vendor-served** files rather than a third-party mirror — the cleanest
  provenance available.
* A file being reachable doesn't mean running it on another model is the vendor's intent; that
  stays your call, as above.
* This repository still ships **no** firmware, and deliberately contains **no** endpoint URLs and
  no acquisition tooling, so it is not a distribution channel.

## If someone raises a concern

There is no vendor code in this repository, so there is nothing of that sort to remove. The
reasonable response: explain the interoperability purpose and, if asked, remove a specific patch
entry or the project itself. That costs nothing here, because no vendor content is hosted.
