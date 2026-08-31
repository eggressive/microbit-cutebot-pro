# microbit-cutebot-pro

MicroPython code for the ELECFREAKS Smart Cutebot Pro robot car with the AI Smart Lens
camera, driven by a BBC micro:bit V2. Programmed and flashed from Linux (Fedora).

## What is in this repo

| File | Purpose |
|---|---|
| `main.py` | Ball chaser demo: drives at the red/blue ball using the AI Lens |
| `cutebot_pro.py` | Trimmed V2-only driver for the Cutebot Pro motor board (details below) |
| `AILens.py` | AI Smart Lens driver, English docstrings (upstream is Chinese) |
| `.vscode/tasks.json` | VS Code build task: Ctrl+Shift+B packs and flashes all .py files |

## Why trimmed drivers exist (the interesting part)

The stock ELECFREAKS MicroPython drivers do not fit the micro:bit V2 filesystem
when used together:

- The micro:bit V2 MicroPython filesystem holds **161 chunks of 128 bytes (~20.6KB)**
  (measured with `micropython-microbit-fs`, not the ~30KB sometimes quoted in docs)
- Stock `cutebot_pro.py` alone is 15.3KB and needs 122 chunks; together with
  `AILens.py` and a `main.py` packing fails with `Not enough space`

The drivers in this repo are therefore:

- **V2 hardware only** (V1 boards talk the older 0x99 frame protocol; current
  production Cutebot Pro units are V2.0.2 / V2.1.0)
- 5.1KB (`cutebot_pro.py`) + 4.7KB (`AILens.py`), whole project ~10.6KB, half the budget
- Servo control **added** (`setServo(index, angle)`, ports S1-S4): missing from the
  official Python driver, protocol taken from ELECFREAKS' own MakeCode extension (`v2.ts`)
- `clearWheelTurn` **fixed**: the official Python driver sends `motor+2` to command
  0x50, but `v2.ts` sends the 0-based motor index. This repo follows `v2.ts`.
  If clearing misbehaves on your unit, try `motor+2`.
- Debug prints removed, `AILens.py` demo block removed, docstrings translated to English

Derived from [elecfreaks/EF_Produce_MicroPython](https://github.com/elecfreaks/EF_Produce_MicroPython) (MIT).

## Flashing

### Option A: mbpack (multi-file, recommended)

`tools/mbpack` packs every `.py` in a folder into a single
universal hex (via `micropython-microbit-fs`, the same library the official micro:bit
Python Editor uses) and copies it to the MICROBIT drive:

```bash
pip install micropython-microbit-fs   # into the venv of your choice
# copy tools/mbpack to a directory on PATH (or use it in place), then:
cd /path/to/this/repo
mbpack            # packs all .py -> micropython.hex, flashes to the micro:bit
mbpack --no-flash # build only
```

Each file keeps its own name in the on-device filesystem, so
`from cutebot_pro import *` works like a normal Python import.

In VS Code: open this folder, press Ctrl+Shift+B (the default build task runs
`mbpack` on the folder of the active file).

### Option B: uflash (single file)

```bash
pip install uflash
uflash main.py    # embeds ONE script as main.py in the hex
```

Note: `uflash` always embeds exactly one file (named `main.py`) and every hex
copy **wipes the on-device filesystem**, including files placed with `ufs put`.

## Hardware

- ELECFREAKS Smart Cutebot Pro (EF-08292), V2 hardware
- ELECFREAKS AI Smart Lens (EF-05045), I2C address 0x14, no conflict with the car at 0x10
- BBC micro:bit V2.2
- One 18650 flat-top cell powers the car (charging: any compatible Li-Ion charger)

## License

MIT. See [LICENSE](LICENSE). Contains code derived from ELECFREAKS' MIT-licensed
EF_Produce_MicroPython.