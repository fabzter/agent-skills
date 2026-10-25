---
name: macos-sdl3-app-bundle
description: Package an SDL3 game or tool as a double-clickable macOS .app, or fix a bundle that lost its fonts/art/config. Covers the two asset lookup roots (executable dir vs SDL_GetBasePath), LaunchServices argv/cwd behaviour, TCC identity for HID/Input Monitoring, and what codesign can and cannot seal.
---

# Packaging an SDL3 app as a macOS .app

Use when turning a working bare binary into a double-clickable app, or when a
bundled app misbehaves in ways the bare binary does not (missing fonts, missing
artwork, config not found, controllers not detected, rumble silent).

A working CLI binary is **not** evidence that the bundle is correct: several
lookups change the moment the executable sits inside `Contents/MacOS`.

## The two lookup roots (the single most common bug)

```
Foo.app/Contents/MacOS/        executable + everything it resolves next to itself
                               (game config, disc paths, mods/, bios/, assets/, saves)
Foo.app/Contents/Resources/    what SDL_GetBasePath() returns for a bundle
                               (launcher/ImGui UI fonts, pad art, flags)
```

| Anchor | Used by |
|---|---|
| executable's directory | the app's own "next to the exe" file resolution |
| `SDL_GetBasePath()` | SDL-based UI code — **bundle-aware**, returns `Contents/Resources` for an `.app`, the exe dir for a bare binary |

**Symptom → cause**

| Symptom | Cause |
|---|---|
| UI falls back to a monospace font, controller/box artwork missing, game still runs | assets only in `Contents/MacOS`; SDL looked in `Contents/Resources` |
| game config / disc / settings not found, app starts as if fresh | executable path resolved from a bare `argv[0]` (see below) |
| controllers dead or rumble silent only in the bundle | TCC identity (see below) |

Fix without duplicating a multi-MB payload: keep everything in
`Contents/MacOS/` and symlink the UI root.

```bash
ln -sfn ../MacOS/assets "$APP/Contents/Resources/assets"
```

## LaunchServices gives you a useless argv[0]

Finder, Spotlight and `open` launch with cwd `/` and sometimes a **bare**
`argv[0]`, so `fs::absolute(argv[0])` anchors every lookup at the filesystem
root. Ask the OS instead:

```cpp
#if defined(__APPLE__)
    char raw[PATH_MAX * 4]; uint32_t size = sizeof(raw);
    if (_NSGetExecutablePath(raw, &size) == 0) {
        std::error_code ec;
        fs::path p = fs::weakly_canonical(fs::path(raw), ec);
        if (ec) p = fs::path(raw);
        exe_dir = p.parent_path();
    }
#elif defined(__linux__)   /* same class of launch: desktop entry / PATH */
    char buf[PATH_MAX];
    ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf) - 1);
    if (n > 0) { buf[n] = '\0'; exe_dir = fs::path(buf).parent_path(); }
#endif
```

Never anchor app data on the cwd — it differs between a shell launch, a
shortcut, Spotlight and a debugger.

## TCC identity: why controllers/rumble work outside the bundle and not inside

macOS grants **Input Monitoring** to the *responsible app*. A bare binary
inherits the launching terminal's grant; a bundle gets its own identity
(`CFBundleIdentifier`) and is granted once, for the game.

Both HID input and HID **output** reports (rumble) depend on it: without the
grant, reads can still work while rumble writes are silently dropped — they
return success. Check the process's own view:

```swift
import CoreGraphics; print(CGPreflightListenEventAccess())
```

`TCC.db` is unreadable without Full Disk Access; do not try to read it as a
diagnostic. Grant in System Settings → Privacy & Security → Input Monitoring,
then relaunch (new processes only).

## Signing: what is enough, what is not

- **Executable ad-hoc signature** — `codesign --force --sign - <exe>` — is what
  the Apple Silicon loader needs. clang already linker-signs, so a bundle can
  launch even when the container is unsigned.
- **Sealing the container** can fail for data layouts codesign misreads:
  directories with dotted names (e.g. `br2.enhancement.turbo`) are treated as
  sub-bundles → `bundle format unrecognized`. Not fatal; sign the executable and
  say so rather than shipping a broken script.
- **Distribution** to another Mac needs a Developer ID signature + notarisation.
  Ad-hoc is a local-development answer only.

## Minimal layout that satisfies everything

```
Foo.app/Contents/MacOS/        exe, assets/, mods/, bios/, game*.toml
Foo.app/Contents/Resources/    AppIcon.icns
Foo.app/Contents/Resources/assets -> ../MacOS/assets
Foo.app/Contents/Info.plist
```

```xml
CFBundleExecutable        <exe name inside MacOS/>
CFBundleIdentifier        reverse.dns.unique
CFBundleName              short name
CFBundleDisplayName       what Finder shows
CFBundlePackageType       APPL
CFBundleShortVersionString / CFBundleVersion
LSMinimumSystemVersion    12.0
NSHighResolutionCapable   true
CFBundleIconFile          AppIcon        (omit if no .icns was generated)
```

Icon: `sips -z N N src.png` into an `.iconset` at 16/32/128/256/512 (+`@2x`),
then `iconutil -c icns`. `plutil -lint` the plist before shipping.

**Do not** copy user state (`settings.toml`, `disc.cfg`, saves) into the bundle:
it should start clean and write its own on first run.

## Verification (do it the way a player launches)

```bash
open "dist/Foo.app"        # LaunchServices path — the one that breaks
```

- artwork/fonts present (not a monospace fallback)
- config/disc/saves resolved inside the bundle
- controllers detected; if rumble matters, confirm it in *this* launch

If something works from a terminal but not from `open`, the difference is cwd /
`argv[0]` — not the code.