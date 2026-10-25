---
name: hardware-probe-discipline
description: "Probing unknown hardware behaviour (HID reports, peripherals, protocols) with one variant at a time, guaranteed stops, and human confirmation."
---

# Probing unknown hardware behaviour

For "the device should do X and doesn't" work: rumble, LEDs, vendor-specific HID
reports, firmware modes. The failure mode of this work is not being wrong once —
it is burning hours on stacked assumptions.

## Rules

1. **Return codes are not evidence.** `IOReturn 0`, `SDL_…Rumble() == true`, and
   "write succeeded" only mean the call was accepted. The only evidence is the
   device doing the thing — or a human saying it did.
2. **Never claim a physical effect without human confirmation.** Ask explicitly:
   "did phase 1 vibrate? phase 2?" An assumed success sends you debugging the
   wrong layer for an hour.
3. **One variant per run.** Changing three bytes *and* the report id *and* the
   transport tells you nothing when it finally works. Run A, ask, run B, ask.
4. **Always send a stop, and make it valid.** Any stateful effect (rumble, LED,
   backlight) persists. A malformed stop (e.g. zeroed bytes that include a
   checksum) is silently ignored and leaves the device buzzing — end every run
   with a verified stop in *all* candidate conventions.
5. **Instrument before optimising.** Measure the cost of the call you added
   (per-call ms, calls/second) instead of guessing why the frame rate dropped.
6. **Establish a known-good reference.** If the OS or another app can drive the
   device (System Settings "Identify", vendor tool), that proves the hardware and
   link are fine and the bug is in your path.

## Loop

```
establish reference (OS/other app) → enumerate what the device advertises
  → pick the smallest candidate set → for each: run → ask human → record
  → on success: minimise the winning frame, then verify a full start/stop cycle
```

## Reporting a failure honestly

When nothing works, say what was tried, what the device advertised, and what the
OS could do that you could not. "Accepted but ignored" plus "only the OS can
drive it" is a device/driver limitation — a legitimate conclusion, not a reason
to keep guessing.

## Anti-patterns seen in practice

- Treating a success return as proof the motor spun
- Streaming a report at frame rate without measuring its synchronous cost
- Testing the *next* variant before confirming the current one
- Leaving a stateful effect on while editing code (the device keeps buzzing)
- Assuming a clone pad follows the official vendor's protocol
