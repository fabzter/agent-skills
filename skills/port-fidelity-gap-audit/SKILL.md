---
name: port-fidelity-gap-audit
description: Use when a ported / recompiled / reverse-engineered build "works" (boots, runs, renders) but may not MATCH the original — systematically audit visual, audio, behavioral and platform fidelity gaps (default post-fx, lighting/lightmaps, texture encoding/color-space, palette textures, shaders, static batching, UI scaling, fonts, physics feel, scene flow) by side-by-side comparison against the original before declaring done.
---

# Port fidelity gap audit

**Core principle: "it runs" ≠ "it matches."** A port can be functionally correct yet look/feel
wrong. Before declaring a port/RE project done, run a deliberate gap audit against the ORIGINAL,
category by category. Observed real gaps (The House On Ash Tree Lane, Unity→SDL3/Metal): trees looked
flat vs the original's stylish painterly look (default post-fx + 8×8 palette texture + lightmap
intensity); D3D11-only shaders → Null device; missing MainMenu.nib/PlayerApplication → no window;
texture double-flip; static-batch world-space verts; UI reference-resolution scaling.

## Method
1. Capture the ORIGINAL and the PORT at the SAME state/camera (title, first exterior, interior,
   each post-fx mode, a transition). Use the original build or a reference capture.
2. Compare side-by-side AND quantitatively (foliage/grass mean/std/percentiles/channel histograms vs
   the original capture); delegate pixel/feature comparison to a worker agent if available.
3. Enumerate EVERY delta by category below; fix shim/shaders/asset-encoding (keep game code verbatim).
4. Re-capture and re-compare until they match. Only then declare done.

## Gap checklist
- **Default post-processing**: original may enable effects (Kuwahara/oil-paint, bloom, vignette, DoG)
  BY DEFAULT. A raw port looks flat. Match the default stack + order + parameters.
- **Lighting**: ambient (SH probe), fog, lightmap intensity/color, directional vs color-only lightmaps,
  skybox, Unity PBS indirect specular (SH9). **Lightmap RESOLUTION**: native 1024² keeps low-poly
  facets crisp; downscaling (256²) blurs facets via bilinear bleed — keep native res for fidelity.
- **Textures**: color space (sRGB/linear), compression vibrancy, palette/tiny textures (e.g. 8×8),
  flip (UnityPy PRE-FLIPS — don't double-flip), mipmaps, wrap/filter modes (point/nearest for palette).
- **Shaders**: custom vs standard (e.g. Ciconia double-sided), cutout/transparent, normal mapping.
- **Geometry**: static batching (baked world-space verts → model=identity, draw submesh range),
  normals/tangents, scale, winding. **Low-poly facet clarity**: keep FLAT/per-face normals (hardware
  `[[flat]]` in MSL; don't average/smooth on extraction) so faceted foliage reads as low-poly.
- **UI**: canvas scaler mode + reference resolution + match, font atlas, alignment, text layout.
- **Audio**: clip set, volumes, spatialization, looping, mixing.
- **Input/physics**: trigger/raycast behavior, movement/look feel, cursor lock, gravity/jump.
- **Scene flow**: load order, transitions, fades, timing, lifecycle order
  (Awake/Start/OnEnable/Update/FixedUpdate/LateUpdate).
- **Platform/launch**: Mac MainMenu.nib + NSPrincipalClass=PlayerApplication + NSMainNibFile; mono
  runtime layout per platform; codesign; graphics-API declaration (globalgamemanagers).

## Common mistakes
- Declaring done after "boots + renders one frame" without comparing to the original.
- Comparing only raw renders when the original ships default post-fx.
- Re-encoding assets lossily and losing the original's color/lighting character.
- Fixing visuals by editing game code instead of the shim/shaders/asset pipeline.