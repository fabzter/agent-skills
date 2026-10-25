---
name: psxrecomp-macos-overlay-build
description: "Native macOS arm64 build overlay for psxrecomp game repos (BloodyRoar2Recomp-style): pull-friendly patch overlay, CMake-pinned dependency fetching, Homebrew-upgrade resilience, and the wizard toolchain-pack fix."
---

# psxrecomp macOS overlay build

Applies to game repos built on the `psxrecomp` framework (BloodyRoar2Recomp,
Metal Gear Solid recomp, etc.) whose upstream ships Windows/Linux only.
Goal: a native macOS arm64 build that survives `git pull` and brew upgrades.

## Repo layout (all additive, nothing upstream-owned is edited)

```
scripts/macos/build-macos.sh                     # one-command build
scripts/macos/*.patch                            # fixes for SUBMODULE working trees
scripts/macos/MACOS.md                           # operator docs
branch local/macos  = upstream master + overlay commits
```

Rules that make pulls painless:
- Patches target submodule **working trees** (`git -C psxrecomp apply`), never
  submodule commits. Before pulling: `git -C psxrecomp checkout -- .`.
- Rebase with `git -c rebase.autoStash=true rebase origin/master` so overlay
  edits need no manual stash; `--ff-only` pull breaks once you commit locally.
- Keep local-only artifacts out of `git status` via `.git/info/exclude`
  (`/toolchain` symlink, `/.omp/`). NOTE: upstream `/toolchain/` (trailing
  slash) does NOT match a symlink — exclude the path without the slash.
- `generated/`, `build-*/`, `disc/` are already upstream-gitignored.

## Build pipeline (order matters)

1. `git submodule update --init --recursive`  (emitters + OpenBIOS need it)
2. reset submodule tree, re-apply `scripts/macos/*.patch` (fail loudly if a
   patch no longer applies → regenerate with `git -C psxrecomp diff`)
3. emitters: `psxrecomp/tools/ci/build_emitters.sh` → `build-recompiler/`
   (needs only Apple clang + cmake + ninja; vendored fmt/rabbitizer)
4. OpenBIOS C (bundled, MIT, no dump): from inside `psxrecomp/`,
   `PSXRECOMP_BIOS_BUILD=../build-recompiler tools/regen_bios.sh --config bios/OpenBIOS.toml`
5. `cmake -S . -B build-macos -G Ninja -DCMAKE_BUILD_TYPE=Release` +
   `cmake --build build-macos --target psx-runtime`

No game C ⇒ configure auto-degrades to a **setup host** (launcher + Generate &
rebuild wizard). That is the correct state until the player supplies a disc.

## Dependency model — let CMake fetch, don't borrow brew

`psxrecomp/cmake/psx_dependency_archive.cmake` resolves three tiers, all
SHA256-pinned in `psxrecomp/third_party/deps.manifest`:
pre-extracted `FETCHCONTENT_SOURCE_DIR_*` → vendored `third_party/` archive →
upstream URL. `-DPSX_DEPS_OFFLINE=ON` turns tier 3 into a hard error.

- Force the pinned path with `-DCMAKE_DISABLE_FIND_PACKAGE_SDL3=ON
  -DPSX_SDL3_FETCH=ON` → static `libSDL3.a`, no brew dylib in the binary.
- `-DCMAKE_DISABLE_FIND_PACKAGE_Freetype=ON -DCMAKE_DISABLE_FIND_PACKAGE_PkgConfig=ON`
  drops optional color-emoji deps → `otool -L` shows zero non-Apple dylibs.
- Verify: `otool -L <exe> | grep -vE '/usr/lib|/System'` must be empty for a
  portable binary.
- **Cache-var trap**: `CMAKE_DISABLE_FIND_PACKAGE_*` are CACHED. Every build
  mode must pass them explicitly (ON *and* OFF) or the previous mode silently
  persists — a later default build keeps emoji disabled.

## Homebrew-upgrade resilience (bites every few weeks)

Symptom chain after `brew upgrade`:
`Imported target "PkgConfig::X" includes non-existent path` →
then `fatal error: 'hb.h' file not found`.

Cause: pkg-config results and `SDL3_DIR` are cached in `CMakeCache.txt` and
point at deleted `Cellar/<pkg>/<old-version>` paths.

Fix (bake into the build script, run before every configure):
1. Drop cache lines whose `/opt/homebrew/Cellar/...` paths no longer exist.
2. If anything was dropped, ALSO drop `__pkg_config_checked_*` — a half-purged
   cache is worse: the checked flag survives, `pkg_check_modules()` skips
   re-resolution, and the imported target ends up with NO include dirs.
   Keep `__pkg_config_checked_<PREFIX>` in lockstep: drop it when
   `<PREFIX>_INCLUDE_DIRS` and `<PREFIX>_CFLAGS` are both absent.

Compiled objects survive this (no full rebuild needed).

## Wizard / toolchain-pack fix (macOS packs ship no clang)

`psxrecomp/host/psxrecomp_codegen_host.c` → `toolchain_bin_compiler_works()`
demands `bin/clang` + `bin/ld.lld` in the downloaded `cmake-clang-v1` pack
(Linux layout). The macOS pack is `kind: "cmake-ninja-system-clang"`: only
cmake/ninja/ccache, builds with `/usr/bin/clang` per its own `env.sh`.
Result without a patch: healthy pack quarantined as `.broken` in
`~/.local/share/retcomm/toolchains/cmake-clang-v1/` and re-downloaded in a
loop. Patch: when the pack has no `bin/clang` (and no `bin/ld.lld`), validate
`/usr/bin/clang` instead and drop `-fuse-ld=lld` from the smoke-test command.


## Region targets (multi-config titles)

A title with `game.toml` / `game_us.toml` / `game_japan.toml` has one CMake
target per region (`psx-runtime`, `psx-runtime-us`, …) and each needs its **own**
codegen setup file: `codegen_setup.c` pins `.game_toml_relpath` and
`.gen_marker_relpath` (`generated/SLES_017.22_dispatch.c`). Reusing the EU file
for the USA target forces first-run setup on every launch (the EU marker never
exists) and then rejects a valid US dump as "wrong dump". Copy it to
`codegen_setup_us.c` with `game_us.toml` + `generated/SCUS_944.24_dispatch.c`
+ `build_dir_name = "build-release-usa"`, pass it via `CODEGEN_SETUP_SOURCES`
for that target, and add the file to the packager's `--project-file` list.

Build per region: generate game C with that region's config, then build the
target (`--usa` flag in the macOS script). Universal needs all regions' C.

## Controller / rumble prerequisites

`[controller] default_mode = "analog"` + `lock_mode = false` — a digital seat is
emulated as an SCPH-1080 with no config handshake, so rumble can never reach it.
The persisted mode in `settings.toml` (`p1_mode`/`p2_mode`) overrides the config.
DS4-compatible BT pads also need a title HID writer (see
`macos-sdl3-rumble-triage` §7).


## Branch switching silently changes the runtime config

The game reads `game_us.toml` / `game.toml` from the **repo root** (it walks up
from the exe), not from the staged copy next to the binary. Switching to an
upstream PR branch therefore swaps in upstream's config: `[controller]
default_mode = "digital"` + `lock_mode = true` disables rumble instantly, even
though the binary is unchanged.

Worse, a run in that state persists `p1_mode = "digital"` into
`build-macos/settings.toml`, which **overrides the config** on later launches.
After any branch switch, check both:

```bash
sed -n '/\[controller\]/,+3p' game_us.toml
sed -n '/p1_mode/p' build-macos/settings.toml     # must match
```

Fix: checkout the overlay branch (`local/macos`), set `p1_mode`/`p2_mode` back to
`analog` in `settings.toml`, rebuild, relaunch.

## Packaging a double-clickable .app (and the two traps in it)

A bare Mach-O works, but a bundle is what makes the build feel like an app and —
more importantly — gives the game its own TCC identity. Two independent lookups
decide whether it renders correctly:

| Component | Anchor |
|---|---|
| runtime (game config, disc, bios/, mods/, assets/, settings, saves) | the **executable's directory** → `Contents/MacOS/` |
| launcher UI (pad art, fonts, flags) | `SDL_GetBasePath()`, which is **bundle-aware** and returns `Contents/Resources/` |

**Trap 1 — missing art/fonts.** Assets only in `Contents/MacOS` make the launcher
fall back to a monospace font and draw **no controller artwork**, while the game
itself still runs fine: it reads as a broken build, not a path problem. Fix: keep
one payload and add `Contents/Resources/assets` → symlink to `../MacOS/assets`.

**Trap 2 — LaunchServices path.** Finder/Spotlight/`open` can pass a **bare
`argv[0]` with cwd `/`**, so `fs::absolute(argv[0])` anchors at the filesystem
root and every sidecar lookup misses. Resolve via the OS instead:
`_NSGetExecutablePath` + `weakly_canonical` on macOS, `readlink(/proc/self/exe)`
on Linux (Windows already uses `GetModuleFileNameW`).

**TCC identity.** A bare binary inherits Input Monitoring from the launching
terminal (HID input *and* rumble output reports depend on it, per terminal,
forever). A bundle is granted once for the game's `CFBundleIdentifier`.

**Signing.** Sign the executable ad-hoc (`codesign --force --sign - <exe>`); the
loader on Apple Silicon is satisfied. Sealing the *container* fails: codesign
refuses the mod catalog's dotted package directories (`br2.enhancement.turbo`)
as "bundle format unrecognized" sub-bundles. Report that in the packaging script
instead of failing; distribution to another Mac needs Developer ID +
notarisation, not a workaround.

Minimal layout that satisfies everything:

```
Foo.app/Contents/MacOS/        exe + bios/ mods/ assets/ game*.toml
Foo.app/Contents/Resources/    AppIcon.icns
Foo.app/Contents/Resources/assets -> ../MacOS/assets
Foo.app/Contents/Info.plist    CFBundleExecutable/Identifier/Name/Version,
                               LSMinimumSystemVersion, NSHighResolutionCapable
```

Do **not** copy `settings.toml`, `disc.cfg` or saves into the bundle — it should
start clean and write its own on first run.

## Verification checklist

- `--headless` run loads `game.toml`, prints "disc needed", exit 0.
- GUI: window appears (`cua-driver call list_windows` → on-screen 1100x912);
  wizard shows OpenBIOS **OK** and NO toolchain page (accepted silently).
- `otool -L` clean for portable builds.
- Re-run the build with a clean submodule to prove patch auto-reapply.
