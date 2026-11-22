# Marionette Workflow Helper

An independent Blender companion for preparing Mixamo-style capture rigs, calibrating Tripo characters, adjusting captured motion and transferring takes into the original character's NLA. Maintained by Killian Pichon. GPL-3.0-or-later.

[Repository](https://github.com/KillianPi22/marionette-workflow-helper) | [Releases](https://github.com/KillianPi22/marionette-workflow-helper/releases) | [Detailed English guide](marionette_workflow/README_EN.md)

**Baseline: 1.4.0. Requires Blender 5.2.0 or later. Historical validation used Blender 5.2.1 LTS.** The 10 shipped addon files are unchanged from the original 1.4.0 extension. Repository setup and portable packaging are new; they do not introduce a new addon version.

The official Marionette application and its Blender plugin are separate requirements for live capture and Copy to DCC. This helper does not replace either, discover or configure their connection automatically, or include their code. Obtain them through the [official Marionette site](https://marionettemocap.com/).

## Available in 1.4.0

- Prepare an isolated capture armature and optional preview meshes while preserving the original character's Actions, NLA and rest skeleton.
- Use Mixamo or Tripo (Mixamo Skeleton) profiles, save the capture reference pose and export a character-specific mapping preset.
- Bake a copied take into the original rig's bone spaces and rotation modes, either as a separate Action or a new NLA strip.
- Adjust root travel, torso and whole-body alignment, hand depth, pelvis motion, stance width and per-foot step height.
- Preview manual corrections interactively, compare with the source and build an editable corrected Action without accumulating offsets.
- Tune flat or sloped ground compensation, including a height-based near-ground mode and per-foot controls.

The interface is in English. The unchanged detailed guide records the original development history and private delivery; [public pack notes](docs/PUBLIC_PACK.md) clarify which presets and fixtures are included in the release archives.

## Install and capture

Download the installable `marionette_workflow-1.4.0.zip` from a published release, or build it locally. In Blender use **Edit > Preferences > Add-ons > Install from Disk**, then open **3D Viewport > N > Mocap Workflow**. Install the inner extension ZIP, not the complete delivery pack.

Prepare a capture copy, export its preset, then import and select that preset manually in the official Marionette panel. Connect, capture with Copy to DCC, disconnect, and use the helper to adjust or transfer the take. See the [English guide](marionette_workflow/README_EN.md) for the exact controls and supported setup.

For an update to this version, install the **1.4.0** extension ZIP with Overwrite enabled and restart Blender. An older paragraph in the unchanged historical guide names a previous package version; this repository's manifest and release number are authoritative.

## Retarget presets

The owner-shared JSON presets are available directly from this repository:

| Preset | Download | Scope |
| --- | --- | --- |
| [Mixamo Full FK Portable](marionette_workflow/presets/Mixamo_Full_FK_Portable.json) | [JSON](https://raw.githubusercontent.com/KillianPi22/marionette-workflow-helper/main/marionette_workflow/presets/Mixamo_Full_FK_Portable.json) | Four FK mappings: prefixed or unprefixed names, with hips-only or all mapped position channels. No saved character calibration. |
| [Tripo Full FK](presets/Tripo_Full_FK.json) | [JSON](https://raw.githubusercontent.com/KillianPi22/marionette-workflow-helper/main/presets/Tripo_Full_FK.json) | Mixamo-named FK mapping with a saved reference pose for the character used to create it. |

Import these files with **Import Presets** in the official **Marionette** Blender panel, then select the imported preset and the matching capture rig. They are retarget presets for the Blender plugin, not files to install as an add-on or import as characters in the standalone application. See the [preset guide](presets/README.md) for choosing a mapping and handling character-specific calibration.

These are repository downloads. The published 1.4.0 release archives are unchanged; the Tripo JSON is a separate download.

## Limits

This is for compatible Mixamo-named FK humanoid skeletons, including Tripo exports using that structure. It is not a universal retargeter for custom IK rigs or arbitrary FBX skeletons. Each capture preset must match the current character's rest pose and transforms; do not reuse another character's calibration.

Corrections are manual pose adjustments, not optical lens undistortion or automatic recovery of the actor's true motion. Ground compensation uses an adjustable plane and a height heuristic; it does not perform foot locking, collision detection, arbitrary terrain fitting or automatic gait reconstruction. Live preview evaluates the current frame and does not guarantee full-rate playback; build a corrected Action before rendering or saving the result. Use matching capture and scene frame rates: this version does not resample between frame rates.

## Develop and build

Packaging uses Python 3.11+ and the standard library. Blender's bundled Python also works.

```sh
python scripts/build_release.py
python scripts/run_tests.py --blender /path/to/blender
```

The test runner accepts a local Blender executable and uses isolated background profiles; see [tests/README.md](tests/README.md) for the portable suites and their scope. Generated output belongs under ignored `build/` or `dist/`. Never use a production scene as a writable test fixture.

The builder validates matching `bl_info`/manifest versions, the extension identity, the generic preset and an explicit public file list. It creates the installable ZIP, public delivery pack and `SHA256SUMS.txt` without modifying source. Archives have fixed metadata and sorted entries for reproducibility within the same Python/zlib environment. The public pack differs from the original private delivery: character-specific presets and production scenes are excluded.

| Path | Responsibility |
| --- | --- |
| `marionette_workflow/__init__.py` | Blender properties, operators and UI |
| `marionette_workflow/mapping.py` | Mixamo-style joint mapping and generic presets |
| `marionette_workflow/calibration.py` | Capture reference-pose calibration |
| `marionette_workflow/workflow.py` | Isolated capture preparation, preset export, bake and NLA transfer |
| `marionette_workflow/correction.py` | Manual pose, depth, gait and ground adjustments |
| `marionette_workflow/preview.py` | Live correction preview and recovery lifecycle |
| `scripts/` and `tests/` | Portable packaging and synthetic validation |

The original private development recorded **172 successful checks** plus installation/upgrade checks on Blender 5.2.1. Those figures are **historical**, not results reproduced by this new public repository. Original tests depended on private character scenes and an installed official plugin; neither is redistributed. Read [validation scope](docs/VALIDATION.md) before interpreting test coverage.

The public migration passed **57 fresh checks** on Blender 5.2.1 LTS on 2026-11-20: 47 synthetic smoke checks and 10 native-install checks. These validate the portable scenarios documented in [tests/README.md](tests/README.md), not real capture networking or every production character.

GitHub's build workflow checks Python syntax and package integrity; it does not run Blender. Release publication is requested by changing `release.json` on `main`, pushing a matching version tag, or manually triggering the release workflow. The version must match the source and have notes under `docs/releases/`. Existing release assets are never overwritten.

## Project boundaries

Read [AGENTS.md](AGENTS.md) and [PROJECT_INSTRUCTIONS.txt](PROJECT_INSTRUCTIONS.txt) before making changes. This repository is separate from the Blender Keyframe Reducer and portfolio website. Website download links and deployment are separate integration work.

No official Marionette plugin, production character mesh or mocap footage is included. The standalone Tripo preset linked above is the owner-shared character calibration; other private production calibrations are excluded. This project is not affiliated with Marionette, Mixamo, Tripo or the Blender Foundation.
