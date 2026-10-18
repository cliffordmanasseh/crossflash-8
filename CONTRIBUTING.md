# Contributing

Thanks for helping. There is **one hard rule**: **never commit firmware.**

## Never commit

* Any `.syx`, `.bin`, `.hex`, or archive containing vendor firmware (not even "test data").
* Anything derived that reproduces substantial vendor bytes (annotated dumps, decoded
  images, generated source from vendor images).
* Downloaders, firmware URLs for other products, keys, or DRM/signature bypasses.

See [`docs/SCOPE.md`](docs/SCOPE.md) for the reasoning. Pull requests that add any of the above
will be closed.

## Setup

```bash
git config core.hooksPath .githooks     # enables the pre-commit firmware guard
python3 tools/check_no_firmware.py      # run manually any time
```

For the full end-user walkthrough (environment setup, patching, flashing, verification,
troubleshooting), see [`docs/USING.md`](docs/USING.md).

## Adding support for another model

1. Obtain your own official source firmware (do not add it here).
2. Determine the byte edits (model/identity field + that build's compatibility-gate
   instruction / table entry). See `patches/carbon8_1-1_to_cobalt8.json` for the shape.
3. Record the source file's **SHA‑256** and the edits as a new JSON in `patches/`.
4. Verify on real hardware that the target unit boots with the patched set, and that
   reverting with the stock set works. Say so in the PR description.
5. Add a short note to `README.md` (supported model + firmware revision).

## Code style

* Standard library only for the base path; keep `mido` optional.
* Run `python3 -m crossflash8.patcher` on your own files and confirm
  `python3 tools/check_no_firmware.py` passes before pushing.
