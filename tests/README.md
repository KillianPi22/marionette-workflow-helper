# Portable migration validation

Run from the repository root with Python 3.11 or later and Blender 5.2:

```sh
python scripts/run_tests.py --blender /path/to/blender
```

`BLENDER_BIN` can supply the executable instead. `--suite smoke` or `--suite install` runs one suite. The default runs both and builds the installation ZIP first.

The runner also accepts invocation by absolute script path from another working directory.

The runner starts offline background Blender processes with isolated user resources and extensions beneath ignored `build/test-runs/` folders. It does not install into the normal user profile, connect to Marionette, open production scenes or change the current Blender session. Logs and `summary.json` are kept in each run folder.

| Suite | Coverage |
|---|---|
| `smoke_blender.py` | Registration lifecycle, mapping policies, generated Mixamo-style and Tripo-profile rigs, isolated capture copies, calibrated preset data, current-frame preview changes, source preservation, preview cleanup, independent baking and session visibility |
| `install_blender.py` | Fresh native installation of the built ZIP, metadata, packaged preset, UI icons/reset operators, disable/re-enable |

Synthetic rigs contain 22 body bones with direct limb chains. A separate name-only mapping check covers the 52 supported body/finger joints. The Tripo-profile fixture changes the namespace and bone roll; it is not a Tripo model and cannot establish quality for every exported character. Tests validate data and state transitions, not rendered character appearance.

No official Marionette plugin code, private character models, production scenes or user-specific absolute paths are included. The public suite does not validate the official plugin's live connection or parser, nor an upgrade from every historical release.

Earlier private development recorded 172 checks on production fixtures and official-plugin integration. Those are historical results, not claims that this public suite reruns them. Use the fresh public runner results when assessing this repository migration.

## Migration result: 2026-11-20

Both suites passed with add-on 1.4.0 in Blender 5.2.1 LTS: **47 synthetic smoke checks and 10 native-install checks, 57 total**. They ran as separate isolated processes against this repository source and its freshly built ZIP. No add-on behavior was changed for the migration.
