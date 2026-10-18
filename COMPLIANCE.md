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

## EULA / licence review (checked 2026-10-18)

Findings — **there is no published firmware or software EULA from the vendor**:

* The vendor website footer links only **Terms** and Privacy Policy; the MODALapp page has
  **no licence/EULA link**.
* `MODALapp.exe` contains **no EULA text** (the only licence strings are for embedded fonts).
* No bundled text/PDF licence in the application bundle.

The only public vendor legal text is the **Website Terms** (last updated 10 Jan 2025). Relevant
clauses and why they are weak hooks here:

| clause | text (abridged) | relevance |
|---|---|---|
| Copyright | rights in "material on this website" owned by the vendor | firmware isn't website material; and we ship none |
| Distribution | "No copying or distribution of material on this website for any **commercial or business use** …" | scoped to website material **and** commercial use; this project is free/non‑commercial and ships no firmware |
| Conduct | use the site "for lawful purposes only … not … bring [vendor] into disrepute or ridicule" | rhetorical; binds site users |
| Indemnity | user indemnifies vendor for claims from *use of the site* | not aimed at third‑party tools |
| Governing law | English law | — |

Notes:

* There is **no firmware licence term** prohibiting modification or cross‑hardware use that we
  could find, so the "you agreed not to do this" contract argument is weak.
* The app is distributed via the Apple App Store, whose **standard EULA** bars reverse
  engineering of **the app** — not of the device firmware. This project distributes nothing
  derived from the app (a protocol/interfaces are not copyrightable), and this repository
  never touches the app.
* Warranty is a separate, commercial matter (the vendor advertises a multi‑year warranty);
  cross‑flashing may void it — see `DISCLAIMER.md`.
* Absence of an EULA does **not** remove statutory copyright. The mitigation remains: ship
  no vendor code, patch‑only, user‑supplied files, SHA‑256‑gated.


## Official availability of the firmware (checked 2026-10-18)

* Officially, the vendor directs users to update **via its companion app**; the product pages
  have a "Firmware — update via <app>" line and there is **no standalone firmware download
  page**.
* In practice the vendor **hosts the official `.syx` files on its own update server and serves
  them publicly and unauthenticated** (the files respond `200` with matching sizes; only the
  server's directory listing is blocked). This is the same endpoint the companion app uses.

Consequences for this project's posture:

* Provenance is as clean as it gets: users obtain the **genuine, vendor‑served** files, not a
  third‑party mirror, so *acquisition* is not an unauthorised‑copying act.
* Downloading from the vendor is not the same as being licensed to run it on other hardware;
  that remains subject to (absent) licence terms and statutory copyright, as analysed above.
* This repository still ships **no** firmware, and deliberately contains **no** endpoint URLs
  or acquisition tooling, so it does not function as a distribution channel.



## If you receive a complaint

There is nothing infringing to remove (no vendor code). The reasonable response is to
clarify intent, state the interoperability purpose, and — if asked — remove the specific
patch entry or the project, which costs nothing legally because no vendor content is hosted.
