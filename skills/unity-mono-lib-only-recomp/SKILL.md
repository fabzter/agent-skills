---
name: unity-mono-lib-only-recomp
description: "Use when decompiling and recompiling a Unity MONO-backend game (Assembly-CSharp.dll present, MonoBleedingEdge folder) into a functionally identical program without installing the Unity editor; not for IL2CPP builds."
---

# Unity Mono lib-only recomp

Recompile a Unity Mono game's logic from decompiled sources against the shipped managed
libraries — no Unity editor, no AssetRipper project export. Engine (`UnityPlayer.dll`) and
all assets/scenes stay untouched; only `Assembly-CSharp.dll` is rebuilt and swapped.

## When it applies
- Build has `<Game>_Data/Managed/Assembly-CSharp.dll` + a `MonoBleedingEdge/` folder → Mono backend.
- IL2CPP builds (GameAssembly.dll + global-metadata.dat) are NOT covered by this recipe.
- Confirm exact Unity version from `<Game>_Data/globalgamemanagers` (ASCII version string near the head).

## Procedure (verified 2026-11-23, Unity 2021.1.11f1)
1. Decompile the game assembly with ILSpy:
   `dotnet tool install -g ilspycmd` then `~/.dotnet/tools/ilspycmd "<Managed>/Assembly-CSharp.dll" -p -o decomp/csharp`.
   ilspycmd v11.2 has NO `-r` flag; it auto-resolves references from the DLL's own directory,
   so decompile from inside `Managed/` for clean output (otherwise it emits `//IL_xxxx Unknown result type` noise).
2. Recompile with Roslyn against the shipped libs. `csc.dll` is in the dotnet SDK at
   `libexec/sdk/<ver>/Roslyn/bincore/csc.dll`. Reference EVERY `Managed/*.dll` EXCEPT
   `Assembly-CSharp.dll` itself (referencing it causes CS0436 type-conflict warnings):
   ```bash
   dotnet exec "$CSC" -nostdlib -noconfig -target:library -unsafe+ \
     -langversion:latest -checked- -optimize+ -out:rebuilt/Assembly-CSharp.dll \
     "${REFS[@]}" decomp/csharp/*.cs decomp/csharp/Properties/*.cs
   ```
   `-nostdlib` + explicit shipped mscorlib/System/netstandard makes the output's assembly
   references match the Unity Mono runtime exactly.
3. Back up the original DLL, then swap the rebuilt one into `Managed/`.

## Fidelity gates (functional equivalence)
- Byte-identical Unity BUILDS are impossible (new GUIDs, reimport, non-deterministic serialization).
  Target functional equivalence, not byte-identical output.
- Size gate: rebuilt DLL byte-size should match the original (matched exactly: 39424 B in the verified case).
- Logic gate: re-decompile BOTH original and rebuilt from inside `Managed/` (clean refs) and
  `diff -rq` the trees. All game types should be byte-identical; only `.csproj` (ILSpy
  target-framework inference) and `Properties/AssemblyInfo.cs` (compiler security attributes) may differ.

## Alternative paths & tooling facts (when lib-only is not enough)
- **AssetRipper 2.0.0** (native mac-arm64 release) recovers a full Unity project (scenes,
  prefabs, assets, ProjectSettings) but is **web-UI-driven**: `AssetRipper.GUI.Free --headless`
  only hosts a local web server (drive it via CDP/browser); there is **no direct CLI export
  command**. Free tier exports stub shaders (decompile is Premium); prefab structure is inlined;
  GUIDs/import settings and Visual Scripting graphs are not recovered. Use it for full-project
  recovery, not for the lib-only DLL swap.
- **Unity editor install (Apple Silicon):** the Unity Hub 4 prod feed lists ONLY Unity 6-era
  editors — legacy versions (e.g. 2021.1.11f1) do NOT appear in "Install Editor". Use the deep
  link `open "unityhub://<version>/<changeset>"` (e.g. `unityhub://2021.1.11f1/4d8c25f7477e`) or
  the Archive tab. 2021.1 is Intel-only → Rosetta 2 (Play-Mode crash risk); 2021.3.48f1 LTS has a
  native arm64 editor but opening a 2021.1 project upgrades serialization irreversibly. The
  lib-only path above avoids all of this.

## Empirical run verification on macOS (verified 2026-11-23)
A Windows Unity build runs on Apple Silicon via **CrossOver Preview's wineloader** (x86_64 under
Rosetta 2). `brew install --cask wine-stable` is a DISABLED dead end; use CrossOver binaries.
See the `crossover-wine-windows-python-sim` skill for wineserver/prefix gotchas. Recipe:
```bash
CXBIN="/Applications/CrossOver Preview.app/Contents/SharedSupport/CrossOver/bin"
export WINEPREFIX="$PWD/.wineprefix" WINEARCH=win64 WINEDEBUG=-all   # prefix under $HOME, NOT /tmp
# start a detached persistent wineserver (-p86400, fds on /dev/null), then:
"$CXBIN/wineloader" 'Z:\<host-path-to>\<Game>.exe'   # host maps to Z:; use wineloader, NOT the bottle-aware `wine` wrapper
```
- **Success gate = Unity Player.log** (in `.wineprefix/drive_c/users/<u>/AppData/LocalLow/<Company>/<Game>/Player.log`):
  `Initialize engine version: <ver>`, `Direct3D 11.0 ... Renderer: Apple M2 Pro`, and
  `MonoManager ReloadAssembly ... Completed reload, in N seconds` with NO errors → the rebuilt DLL loaded and JIT'd.
- The `wine` wrapper demands a 'default' bottle; `wineloader` respects WINEPREFIX directly (skip bottles).
- Screenshotting a backgrounded CrossOver window often fails (`px_capture_unavailable` / it pauses
  rendering when occluded). Capture right after launch while frontmost, or rely on the Player.log gate.
- Keep all artifacts (prefix, tools) bounded to the project dir; no system-wide Unity install.