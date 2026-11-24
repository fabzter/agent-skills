---
name: unity-no-editor-metal-shader-port
description: Use when a Unity WINDOWS Mono game must render natively on macOS Metal (or Linux GL) WITHOUT the Unity editor — i.e. the player launches but falls back to NullGfxDevice / crashes because assets carry D3D11-only shaders. Proven on The House On Ash Tree Lane (Unity 2021.1.11f1).
---

# Unity no-editor Metal shader port

A Windows Unity build's shaders are D3D11-only; a Mac player then picks NullGfxDevice and
crashes on first draw. You CAN port to native Metal without the editor (proven 2026-11-24).

## Prereq: windowed launch must already work
Hand-assembled Mac app needs `MainMenu.nib` (from the player module's
`Source/Player/MacPlayer/MacPlayerEntryPoint/Resources/`) in `Contents/Resources/` AND
Info.plist `NSPrincipalClass=PlayerApplication` + `NSMainNibFile=MainMenu`. Without these the
Cocoa delegate never fires (idle NSApplicationMain, no window). See unity-mono-lib-only-recomp.

## Proven reference
`Andreansx/casualties-unknown-apple-silicon` (GitHub) — native Apple-Silicon Metal port of a
Unity Windows game. Clone it; study `docs/port-7.0.md`, `tools/rewrap/` (unity_metal_blob.py,
inject_custom_metal2.py, dxbc2msl.py, patch_ggm_metal.py, transplant_stock.py), `tools/hlslcc/`.

## Pipeline (adapt per Unity version)
1. Inventory shaders (UnityPy): split already-Metal (unity default resources) vs D3D11-only
   (unity_builtin_extra + resources.assets + sharedassets). Count DXBC entries in lz4 compressedBlob.
2. Unity's Metal backend compiles **MSL SOURCE** at load (newLibraryWithSource:), so inject MSL
   in Unity's ABI — NOT precompiled metallib.
3. Extract DXBC; **synthesize the stripped RDEF reflection chunk** from SHDR/SHEX
   dcl_constantbuffer/dcl_resource/dcl_sampler (Unity strips RDEF). Convert DXBC→MSL via Unity HLSLcc.
4. Repack into the target Unity version's Metal sub-program blob: entry =
   wrapper(32B)|0xF00DCAFE payload|trailing input-binding table. The trailing table is
   platform-independent — PRESERVE it. Blob must be LZ4-block-compressed.
5. Patch globalgamemanagers surgically (4-byte writes, never re-serialize) to declare Metal.
6. Verify MSL with `xcrun metal -c -std=macos-metal2.2` (native Mac compiler available).
7. Rebuild app, ad-hoc codesign, launch; gate = Player.log "Initializing Metal device caps: <GPU>"
   (NOT NullGfxDevice) + rendered frame.

## Our implementation (rea_test_2-house-on)
`build/metal_port/`: dxbc2msl_2021.py, unity2021_blob.py, convert_shaders.py, verify_metal_2021.py;
plan in `build/PORT_PLAN.md`. Converted 54 D3D11 shaders / 1580 entries for Unity 2021.1.11f1.

## Delegation
This is heavy RE (blob format differs per Unity version; disassemble UnityPlayer.dylib
LoadGpuProgramFromData / GpuProgramMetal::CreateFromShaderLabSource). Delegate to a strong model
via Herdr (agy = Antigravity "Gemini 4 Neon"); watch quota overlays (esc) but esc mid-turn cancels it.
