---
name: unity-free-sdl3-rebuild
description: "Use when removing the Unity engine entirely and running a decompiled Unity Mono game's verbatim C# on a lightweight backend with a much smaller build. Proven on The House On Ash Tree Lane (Unity 2021.1): SDL3 SDL_GPU native Metal + clean-room UnityEngine shim, 855MB→116MB."
---

# Unity-free rebuild on SDL3 (no Unity engine)

Run a decompiled Unity game's C# VERBATIM on a lightweight backend by writing a clean-room
`UnityEngine` compatibility shim. Proven 2026-11-24 (The House On Ash Tree Lane, 2021.1.11f1):
855 MB Unity .app → 116 MB; assets 830 MB → 28 MB.

## Backend decision (research before choosing)
- **SDL3 `SDL_GPU` (native MSL/Metal)** via `ppy.SDL3-CS` — recommended. Compiles native MSL
  (`SDL_GPU_SHADERFORMAT_MSL`), offline-check with `xcrun metal -c -std=macos-metal2.2`.
- FNA: needs Windows `fxc.exe` (FXBC) for Effects; prebuilt `fnalibs` archive 404s; FNA3D moved to SDL_GPU.
- MonoGame / raylib-cs: OpenGL-only on macOS (no native Metal).
- Measure first: the .app bulk is usually **assets** (`.resS` textures/audio/lightmaps), NOT the engine.
  Re-encode assets (UnityPy): UI/sprites→PNG, diffuse→JPEG, lightmaps→small JPEG (drop directional),
  meshes→Deflate binary, audio→OGG (NVorbis). This is where the size win is.

## Architecture
- `extractor/extract_assets.py` (UnityPy): textures/audio/meshes/fonts + scenes/materials/sprites/
  animations JSON. Stripped MonoBehaviour payloads: 32B header + aligned m_Name, then raw fields;
  assert offset==len(payload). UnityPy PRE-FLIPS textures (don't double-flip).
- `src/UnityShim/`: clean-room UnityEngine (Core math/Object/Component/GameObject/Transform, Physics
  triggers+raycast, AudioInput, Rendering Camera/Shader/Material/RenderTexture/Graphics.Blit, Scene,
  UI) over SDL3. `src/GameScripts/` compiles `decomp/csharp/*.cs` with 0 edits. `src/Shaders/*.metal`.
- SDL_GPU MSL binding contract: vertex `[[stage_in]]`, uniforms `[[buffer(n)]]`, `[[texture(n)]]`/
  `[[sampler(n)]]` in sequential slot order per stage.
- Static batching: baked world-space verts → model matrix = identity, draw only
  [firstSubMesh .. +subMeshCount).

## Gotchas
- SIGSEGV after scene load is usually Blit/post-fx or SDL_Quit teardown. **lldb --batch HANGS on
  CoreCLR** — isolate WITHOUT a debugger: --no-postfx/--null-render flags + per-step logging, bisect
  the SDL_GPU call (missing pipeline / unbound texture / released resource / wrong buffer slot).
- Verify: dotnet build 0 errors; per-scene + per-postfx screenshots; codesign --verify --deep --strict.

## Delegation
Heavy RE → Neon (Antigravity) via Herdr; spawn faster Hydrogen/sonnet workers per subsystem. Workers
do long asset-analysis before writing files — don't assume stalled; check pane, nudge gently.

## Visual fidelity (it runs ≠ it matches) — run port-fidelity-gap-audit
- **Lightmap RESOLUTION**: original 1024² keeps low-poly facets crisp; downscaling to 256² blurs
  facets via bilinear bleed. Keep native res for fidelity (costs ~20 MB). Directional lightmaps too.
- **Flat normals**: use hardware `[[flat]]` in MSL for faceted foliage; don't smooth/average normals.
- **Palette/tiny textures** (e.g. 8×8): point/nearest filtering, lossless, no over-blurring mipmaps.
- **Default post-fx**: original may enable the painterly stack by default; match it (F1–F6 toggles).
- **Lighting**: ambient SH probe + Unity PBS indirect specular (SH9 sky bounce) for Standard mats.
- Compare quantitatively: foliage/grass mean/std/percentiles/histograms vs an original capture.

## Size & run
- .NET self-contained runtime ~100 MB+; assets dominate the win (830→28–48 MB). Full lightmaps trade
  ~20 MB for fidelity. Final .app ~116–136 MB vs Unity 855 MB.
- Run: open the .app; WASD/mouse, E interact; F1 none/F2 bloom/F3 kuwahara/F4 pixelart/F5 dog/F6 vignette.
- CLI stills: `--scene 0/1/2 --postfx X --frames N --screenshot out.png [--send-key e:5]`.

## Controller & QoL (SDL3)
- **Init**: `SDL_INIT_VIDEO|AUDIO|JOYSTICK|GAMEPAD` (+EVENTS implied by VIDEO). Set hints BEFORE
  SDL_Init: `SDL_JOYSTICK_HIDAPI=1`, `HIDAPI_PS4=1`, `HIDAPI_PS5=1`, **`HIDAPI_SWITCH=0`** (the Switch
  driver hijacks PS4 pads and fails calibration), `ALLOW_BACKGROUND_EVENTS=1`.
- **Bundle the CURRENT SDL3**: NuGet/publish may ship a stale native libSDL3 lacking HIDAPI PS4;
  build script must copy the homebrew `libSDL3.0.dylib` into the .app.
- **Poll axes, don't trust axis events**: BT PS4 on macOS goes through Apple MFi; SDL3-CS
  `SDL_EVENT_GAMEPAD_AXIS_MOTION` marshaling is unreliable. Poll `SDL_GetGamepadAxis` (and raw
  `SDL_GetJoystickAxis` fallback) each frame; left stick→Horizontal/Vertical, right stick→Mouse X/Y.
- Mapping: left stick move, right stick look, A=jump/space, X=E interact, D-pad=WASD fallback,
  Start=pause menu. Radial deadzone ~0.18.
- **Resolution config**: CLI --width/--height/--fullscreen + UserSettings JSON persist + runtime
  swapchain recreate (retain GPU resources). **Pause menu**: Esc/Start, Time.timeScale=0, overlay via
  the UI quad/FontAtlas pipeline; navigate keyboard/gamepad/mouse.
- Verify with a SDL virtual gamepad (`--test-gamepad`): assert left stick feeds GetAxis, right stick
  rotates yaw, buttons map, Start pauses, raw-joystick fallback works.
