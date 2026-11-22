# Public delivery pack

Install `marionette_workflow-1.4.0.zip` with Blender's **Install from Disk** command. Do not install the outer `Marionette_Workflow_Pack_1.4.0.zip`.

The public pack contains the unchanged 1.4.0 extension, English guide, GPL license, generic Mixamo mapping preset and source checksums. The official Marionette application/plugin are separate requirements and are not included.

The original guide describes a private development delivery with calibrated Mixamo and Tripo presets. Those character-specific presets, production scenes, meshes and test profiles are **not included here**. Use **Prepare Capture Copy**, save the correct reference pose, and **Export Preset JSON** for your own character. The included generic preset contains mappings, not a calibration for arbitrary character proportions.

For updating this release, install the **1.4.0** ZIP and restart Blender. The unchanged historical guide has an older update paragraph mentioning 1.3.0; it is not the package version in this public release.

Source code and portable test instructions:

https://github.com/KillianPi22/marionette-workflow-helper

The original private validation recorded 172 checks plus installation/upgrade verification. Those are historical results, not a claim that the public synthetic suite reproduces all private scene or official-plugin tests.

Public archives are rebuilt with normalized ZIP metadata; their archive hashes differ from the original private delivery even though the extension files are unchanged. `SOURCE_SHA256.json` identifies the shipped source payload, and the release's `SHA256SUMS.txt` identifies the downloadable archives.

## Additional repository preset downloads

The repository now also provides the owner-shared [Tripo Full FK preset](../presets/Tripo_Full_FK.json), alongside the existing [Mixamo Full FK Portable preset](../marionette_workflow/presets/Mixamo_Full_FK_Portable.json). See the [preset guide](../presets/README.md) for import instructions and calibration scope.

The Tripo file is a standalone repository download. It is not added to, or claimed to be part of, the already published 1.4.0 extension or delivery pack described above. Those release assets remain unchanged. Other private presets and production fixtures remain excluded.
