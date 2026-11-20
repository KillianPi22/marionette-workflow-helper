# Codex working instructions

## Product and compatibility

- Keep the addon UI, tooltips, errors and developer documentation in English. Communicate with Killian in French unless asked otherwise.
- Baseline 1.4.0 contains live correction preview and manual lower-body compensation. Preserve the existing behavior when extracting or packaging; distinguish planned work from available controls.
- Preserve extension ID `marionette_workflow`, `mw.*` operators, saved settings and reference-pose compatibility unless a documented migration is implemented.
- This is an independent companion to the official Marionette plugin. Do not bundle that plugin, overwrite its presets, or infer undocumented connection state.
- Keep this repository separate from Keyframe Reducer and the portfolio website.

## Protect animation and scene data

- Prepare and modify capture copies, not the original character's rest skeleton, Actions, NLA or rotation modes.
- Build corrections from the remembered source Action. Repeated edits must not accumulate corrections.
- Keep live preview temporary and recoverable across stop, save, undo/redo, file load and addon reload. Do not delete a temporary Action that acquired external users.
- Access Blender data only on its main thread. Preserve source Action slots and unrelated animation channels.
- Reject unsupported rigs or conflicting contexts clearly. Do not silently reinterpret unsupported custom IK controllers or constraints.
- Treat ground compensation as a manually tuned plane/height heuristic, not guaranteed contact detection. Pose adjustment cannot be advertised as lens calibration or recovery of true motion.
- Do not stretch limbs to force unreachable targets; retain and test the documented reach-clamping behavior.
- Do not write over a user's production scene in tests. Use generated fixtures and isolated Blender profiles.

## Development and validation

- Run the relevant portable suites with `scripts/run_tests.py`; see `tests/README.md` for what they verify. Run packaging checks before preparing a release.
- Keep historical validation clearly labeled. The original 172 checks required private fixtures and are not equivalent to the portable public tests.
- Keep `scripts/build_release.py` version-driven and independent of private paths, sibling repositories, installed official plugins and production presets.
- The public extension file allowlist is intentional. Update it explicitly when adding legitimate extension files; do not recursively package arbitrary workspace data.
- Keep manifest, `bl_info`, `release.json` and versioned release notes consistent when intentionally preparing a release.
- Generated profiles, logs and builds belong under ignored `build/` or `dist/`. Do not commit credentials, private filesystem paths, footage, character meshes or third-party plugin copies.
- Do not publish a release or deploy website changes without task authorization. A build/test does not itself authorize publication.

## Communication

- Report actual changes, checks run and practical limitations. Avoid claiming optical correction, foot locking, universal rig support or measured performance without evidence.
- Ask concise product questions when the answer changes a meaningful decision; otherwise continue authorized work independently.
