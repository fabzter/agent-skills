---
name: macos-sdl3-gamepad-rumble
description: Gamepad not detected or rumble silent/collapsing FPS on macOS in an SDL3 app. Layer triage (OS HID, GameController, SDL drivers, TCC Input Monitoring), the DS4 Bluetooth HID report convention SDL cannot express, stop-frame discipline, and moving synchronous HID writes off the frame loop.
---

# macOS SDL3 gamepad: detection and rumble

Use when an SDL3 game/app on macOS does not see a controller, never vibrates,
vibrates but never stops, or drops FPS while vibrating.

**One rule up front:** `SDL_RumbleGamepad()` returning `true`, and
`IOHIDDeviceSetReport` returning `IOReturn 0`, mean *accepted* — never *felt*.
Do not claim a physical effect without the user confirming it. Assuming success
sends you debugging the wrong layer for an hour (and can leave a pad buzzing).

## 1. Which layer loses the device?

```
OS HID  →  GameController framework  →  SDL driver (HIDAPI vs MFI)  →  TCC permission
```

Run these in order; each disagreement is diagnostic.

```bash
hidutil list | awk 'NR==1 || $4==1'                    # usage page 1 = joystick/gamepad
hidutil list --matching '{"VendorID":1356}'            # 0x54C Sony
system_profiler SPBluetoothDataType | sed -n '/Connected:/,/Not Connected:/p'
system_profiler SPUSBDataType | grep -iA5 playstation
```

| OS HID | GCController | SDL | Meaning |
|---|---|---|---|
| no | 0 | 0 | **paired but not connected** — wake it (PS button) or plug USB; not a game bug |
| yes | 0 | 0 | non-MFi/clone pad: needs HIDAPI (and Input Monitoring) |
| yes | yes | 0 | SDL driver disabled or hint mismatch |
| yes | — | yes, app still silent | app-side enumeration (dropdown built once, no hotplug refresh) |

`GCController.controllers()` from a bare CLI is weak; retest from a `.app`
bundle with a foreground window. DS3 has no GameController support at all.

## 2. SDL driver choice (HIDAPI vs MFI)

| Hints | Driver | Notes |
|---|---|---|
| default | HIDAPI | sees clones |
| `SDL_HINT_JOYSTICK_HIDAPI=0` | MFI/GameController | **only** recognised pads; a clone enumerates 0 |
| `SDL_HINT_JOYSTICK_HIDAPI=1` (+`RAWINPUT=0`) | HIDAPI forced | what most ports set; required for clones |

Probe against the **same SDL build the app links** (a static copy in `_deps/`
can differ from brew):

```bash
clang probe.c -o probe -I/opt/homebrew/include -L/opt/homebrew/lib -lSDL3 \
      -Wl,-rpath,/opt/homebrew/lib
```

```c
SDL_SetHint(SDL_HINT_JOYSTICK_HIDAPI, "1");
SDL_Init(SDL_INIT_JOYSTICK | SDL_INIT_GAMEPAD);
int n = 0; SDL_JoystickID *ids = SDL_GetJoysticks(&n);
// per id: SDL_GetJoystickNameForID, SDL_GetJoystickVendorForID/ProductForID,
//         SDL_IsGamepad, SDL_GetGamepadNameForID, GUID string
```

A 60–90 s hotplug watcher (`SDL_EVENT_JOYSTICK_ADDED` + polling) lets the user
reconnect mid-run and shows the exact moment the device appears.

## 3. TCC Input Monitoring (the silent killer)

```swift
import CoreGraphics; print(CGPreflightListenEventAccess())   // swift file.swift
```

`false` → the responsible process never got **System Settings → Privacy &
Security → Input Monitoring**. Consequences: `GCController.controllers()` is 0
and HID **output** reports (rumble) are dropped silently while reads still work
(inputs play fine). Grant it to the launching terminal/app and **relaunch**
(TCC applies to new processes only; `TCC.db` is unreadable without Full Disk
Access — don't try).

Ship the game as a `.app` bundle so the permission attaches to its
`CFBundleIdentifier`, not to whatever shell launched the binary.

## 4. Rumble: is the app even asking?

Some emulators gate rumble on emulated hardware state, not on SDL (e.g. a PS1
pad emulated as a plain digital SCPH-1080 has no config-mode handshake, so the
game cannot send motors at all). Check the app's own trace before blaming the
host — see `psxrecomp-gamepad-rumble` for that class.

## 5. SDL accepted the write and the pad ignored it

Cause: SDL's HIDAPI drivers build the effects frame with the report id **inside**
the buffer; hidapi then passes the report id to `IOHIDDeviceSetReport`
**separately** and strips it from the payload. Clones accept that and do nothing.

Convention that DS4-compatible pads obey (verified variant by variant on
hardware — F rumbles; G, H, missing-CRC and single-shot did not):

```
IOHIDDeviceSetReport(dev, kIOHIDReportTypeOutput, reportID = 0, buf, 78)
  buf[0]=0x11   BT effects report id
  buf[1]=0xC0   HID output + CRC present
  buf[3]=0x03   effect mask (rumble | led)
  buf[6]=small / high-frequency motor (0..255)
  buf[7]=large / low-frequency motor  (0..255)
  buf[74..77]   CRC32 over 0xA2 + buf[0..73]  (poly 0xEDB88320, init/final ~)
```

Before guessing, enumerate what the pad advertises as writable:

```swift
IOHIDDeviceCopyMatchingElements(dev, nil, 0)   // kIOHIDElementTypeOutput →
IOHIDElementGetReportID(e)                     // DS4 clones: 0x11..0x19
```

Variant set worth trying, **one at a time, each followed by a valid stop**:
F (reportID 0, buffer includes `0x11`) · G (reportID `0x11`, buffer also starts
`0x11`) · H (reportID 0, USB-style `0x05`, 32 B). Also worth a try when F is
silent: streaming at ~50 Hz instead of one frame, and
`kIOHIDOptionsTypeSeizeDevice`.

Vendor/product come from SDL (`SDL_GetJoystickVendorForID/ProductForID`), e.g.
DS4 `0x054c/0x05c4` or `0x09cc`. Leave DualSense (different layout) on SDL.

## 6. It starts and never stops

Two independent traps:

- **Invalid stop frame.** Zeroing the whole buffer also zeroes the CRC, so the
  pad ignores the stop and the motor runs forever. Send a *valid* zero-rumble
  frame (rumble bytes 0, CRC recomputed), several times — a single BT frame can
  be dropped.
- **Stop condition that can only be true once.** A "previous frame was active"
  test is false forever after the first zero frame, so a latched effect is never
  released. Keep an explicit `stop_pending` flag: set on every active frame,
  cleared after the stop is sent.

Games pulse motors (`small=1,0,1,0` at 60 Hz). Hold the effect ~250 ms and
re-arm it on every active poll; otherwise each pulse is a ~16 ms blip nobody can
feel.

## 7. FPS collapses while vibrating

`IOHIDDeviceSetReport` is **synchronous**: measured 5–20 ms per call, peaks
78–142 ms over Bluetooth. At frame rate that turns 16.7 ms frames into 30–90 ms
frames.

- dedicated **writer thread** + one-slot mailbox (mutex/condvar, latest value
  wins — never a queue)
- coalesce pulses to ~10 Hz with the latest values; send idle↔active transitions
  immediately so start/stop stay snappy
- keepalive ~100 ms while active (a dropped BT frame must not silence a
  sustained effect)
- **instrument it**: time each write and print `N writes/s, avg X ms, max Y ms`
  behind a trace env var; the before/after numbers are the proof

## 8. Where the fix belongs

Keep the platform convention out of generic frameworks: put it in a
title/project-owned file exposing a tiny backend, and let the framework call it
through **weak symbols** (`attach(vid,pid)` / `update(small,large)` /
`detach()`), so absence costs nothing and SDL's path stays the default. Scope by
vendor/product, and never run HID writes on the render thread.

## Gotchas

- SDL 3.4.x renamed `SDL_HINT_JOYSTICK_HIDAPI_PS4_RUMBLE` / `…PS5_RUMBLE` to
  `SDL_HINT_JOYSTICK_ENHANCED_REPORTS`; old names live in `SDL_oldnames.h` and
  fail to compile under C99+ (`-Wimplicit-function-declaration`).
- `SDL_LogSetAllPriority` is `SDL_SetLogPriorities` in SDL3.
- Bluetooth pads idle-sleep aggressively — never conclude "game bug" from a
  probe that ran while the pad was asleep.
- Verify a fix is actually in the binary (`strings … | grep <marker>`) before
  asking the user to test again.