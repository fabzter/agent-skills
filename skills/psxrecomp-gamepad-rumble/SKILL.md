---
name: psxrecomp-gamepad-rumble
description: Controllers or rumble broken in a psxrecomp game port (BloodyRoar2Recomp, MGS recomp family) on macOS or Linux. Traces SIO motor values, the digital-vs-DualShock config gate, forwarder hold/stop policy, per-region setup wizard configs, and the submodule patch workflow.
---

# psxrecomp game ports: input and rumble

Use when a recompiled PSX title does not see a controller, or never rumbles.
Host-side (SDL/macOS/HID) diagnosis lives in `macos-sdl3-gamepad-rumble`; this
skill covers what is specific to the psxrecomp runtime and its titles.

## 1. Trace before theorising

```bash
PSX_RUMBLE_TRACE=1 ./GameName 2>&1 | grep 'psxrecomp rumble'
```

```
psxrecomp rumble: slot=1 small=1 large=255     # motor values the game wrote
psxrecomp rumble-hw: slot=1 low=… high=… dur=250 via=…   # host write (if present)
```

| Observation | Conclusion |
|---|---|
| no `rumble:` lines at all | emulated pad is not config-capable, or the game's Vibration option is off |
| lines, no `rumble-hw:` | runtime forwarder rejected/skipped it |
| `rumble-hw:` lines but no vibration | host side → `macos-sdl3-gamepad-rumble` §5 |

## 2. The emulated-pad gate (the most common cause)

PSX rumble travels only over the DualShock config handshake: `0x43` (enter
config) → `0x4D` (motor map) → `0x42` (motor data bytes). The runtime decides
capability per seat in `runtime/src/main.cpp`:

```c
sio_set_pad_config_capable(s, policy.callback ? policy.config_capable
                                             : mode != PSXRecompV4::PAD_MODE_DIGITAL);
```

So a **digital** seat is an SCPH-1080: no config mode, no rumble — whatever the
in-game option says. Two places set the mode:

1. `game*.toml` `[controller]`: `default_mode` + `lock_mode`. `lock_mode = true`
   with `digital` forces every seat digital (`g_force_digital_pads = 1`) and
   hides the launcher's mode selector.
2. `settings.toml` next to the exe (`p1_mode` / `p2_mode`) — **persisted and
   overriding** the config default. Change both when switching to analog.

Use `default_mode = "analog"` + `lock_mode = false` to enable rumble.

## 3. Forwarder policy: hold, and release exactly once

`update_controller_rumble()` forwards `sio_get_pad_rumble()`. Games pulse the
motors (`small=1,0,1,0` at 60 Hz), so:

- **hold** the effect (~250 ms) and re-arm on every active poll — cancelling on
  the next zero read yields ~16 ms blips that cannot be felt;
- **do not** test the previous frame's values to decide a stop: after the first
  zero frame that test is false forever and a latched effect never releases.
  Keep an explicit `rumble_stop_pending` flag.

Host writes cost milliseconds (Bluetooth), so the forwarder should only publish
the latest values to a writer thread — never call HID from the frame loop.

## 4. Per-region builds and the setup wizard

Multi-region titles have one CMake target and one codegen config per region:

| Region | Config | Marker | Target |
|---|---|---|---|
| EU | `game.toml` | `generated/SLES_017.22_dispatch.c` | `psx-runtime` |
| USA | `game_us.toml` | `generated/SCUS_944.24_dispatch.c` | `psx-runtime-us` |

`codegen_setup.c` pins the region; reusing it for another target makes the
first-run wizard **force itself on every launch** (its sources probe looks for
the EU marker) and then reject a valid dump as *"Disc verification failed
(wrong dump)"*. Give each region its own `codegen_setup_*.c` (own config, own
marker, own `build_dir_name`) wired via `CODEGEN_SETUP_SOURCES`, and add the file
to the packager's `--project-file` list.

Workaround to play without the wizard: `./Game --no-launcher --disc <cue>`.

## 5. Patch workflow (local overlays)

If the build script resets the submodule (`git -C psxrecomp checkout -- .`) and
re-applies `scripts/macos/*.patch`, an **uncommitted submodule edit is silently
discarded** — write the change into a patch file first, then rebuild, then prove
it landed (`strings binary | grep <marker>`).

## 6. Where the code lives

| Concern | File |
|---|---|
| pad mode / config capability, forwarder, hotplug | `runtime/src/main.cpp` |
| motor capture (`0x42`/`0x4D`), `sio_get_pad_rumble` | `runtime/src/sio.c` |
| title setup-wizard config | `<title>/codegen_setup*.c` |
| title host-rumble backend (optional) | `<title>/src/platform/…` via weak symbols |