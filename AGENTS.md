# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, Copilot, Hermes, etc.) working in this repo.

## What this repo is

MicroPython code for the ELECFREAKS Cutebot Pro robot car + AI Smart Lens, running on a
BBC micro:bit V2. Everything here is flashed onto the micro:bit's ~20.6KB filesystem;
it is NOT a normal Python project. Constraints below follow from that.

## Hard constraints (do not violate)

1. **Filesystem budget: ~20.6KB total** (161 chunks x 128B, measured). Current usage
   ~10.6KB (AILens.py + cutebot_pro.py + main.py). Before adding or growing any file,
   verify it still packs: `tools/mbpack --no-flash` fails loudly with `StorageFullError`.
2. **No em dashes (U+2014)** in any generated content: code, comments, docstrings,
   commit messages, README. Use a hyphen, colon, parentheses, or separate sentences.
3. **MicroPython, not CPython**: the target is micro:bit MicroPython 2.1.x on the
   nRF52833 (128KB RAM, no f-strings guaranteed safe across ports - use `.format()`
   or `%`). Available APIs: the `microbit` module (display, buttons, i2c, pins,
   accelerometer, radio, sleep), `machine`, `time`, `os`, `neopixel`, `music`,
   `random`, `sys`. No pip, no venv, no filesystem directories (flat fs), no threads,
   no asyncio, no `pathlib`, no dataclasses. `bytes`/`bytearray` yes, `numpy` no.
4. **Do not commit build artifacts**: `*.hex` is generated (1.2MB), already in
   `.gitignore`. Never force-add it.
5. **Drivers are trimmed for a reason**: `cutebot_pro.py` is V2-only by design.
   Do not "restore" the stock 15KB ELECFREAKS driver or add V1 protocol branches;
   the stock driver + AILens.py does not fit the V2 filesystem together. Keep the
   per-file size discipline; if a feature is needed, port it from
   https://github.com/elecfreaks/EF_Produce_MicroPython or the MakeCode source
   https://github.com/elecfreaks/pxt-Cutebot-Pro (v2.ts is protocol ground truth).
6. **Attribution**: driver files derive from ELECFREAKS' MIT-licensed
   EF_Produce_MicroPython. Keep the derivation note in the file headers.

## Build, verify, flash

```bash
# syntax check (CPython AST; microbit module is NOT importable on the host)
python3 -c "import ast, sys; [ast.parse(open(f).read()) for f in sys.argv[1:]]" main.py cutebot_pro.py AILens.py

# pack all .py into one hex and verify contents + filesystem usage
tools/mbpack --no-flash

# flash to a plugged-in micro:bit (writes micropython.hex to the MICROBIT drive)
tools/mbpack

# serial REPL (Ctrl+A then Ctrl+D soft-reboots; Ctrl+C interrupts)
minicom -D /dev/ttyACM0 -b 115200
```

VS Code: Ctrl+Shift+B runs the pack+flash task on the folder of the active file
(`.vscode/tasks.json`).

## Verification standard

There is no emulator and no test runner in this repo; behavior is only provable on
hardware. So:

- Syntax check + `mbpack --no-flash` (which also enforces the filesystem budget) is
  the mandatory pre-commit bar.
- Anything that can be checked statically, check: I2C frame formats against
  `v2.ts`, address constants (car 0x10, camera 0x14), no CJK or em dashes anywhere.
- Claims about on-device behavior ("servo moves", "ball tracking works") must come
  from a human with the hardware, not from an agent. Flag them as unverified otherwise.
- When the servo `clearWheelTurn` ambiguity matters, both protocol variants are
  documented in cutebot_pro.py; do not silently change one to the other.

## Hardware facts (for correct code)

- Cutebot Pro motor board: I2C addr 0x10. V2 command frame: `[0xFF, 0xF9, cmd, len, *params]`.
- AI Smart Lens: I2C addr 0x14. `switch_function()` modes: Card=2, Face=6, Ball=7,
  Tracking=8, Color=9, Learn=10. Data frame is 9 bytes via `i2c.read`.
- Ultrasonic: GPIO pins 8 (trig) / 12 (echo), not I2C.
- Servo ports S1-S4: command 0x40, params `[index_0based, angle_0_180]`.
- Encoder motors: PID closed-loop; `pwmCruiseControl` takes -100..100 per wheel.
- Power: one flat-top 18650 cell. If I2C scan does not find 0x10, the motor board is
  unpowered: `CutebotPro.__init__` raises with that hint.

## Commit / PR style

- Conventional-ish subject line, imperative mood. Body explains WHY, especially for
  protocol changes (cite v2.ts or the wiki).
- No generated-file noise: never commit micropython.hex or settings.json.
- Keep diffs mechanical: one logical change per commit. Driver trims that change
  behavior at runtime deserve their own commit with the measured chunk budget
  before/after in the message.