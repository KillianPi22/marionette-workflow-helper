# Retarget presets for Marionette for Blender

These JSON files were selected and validated locally by the repository owner for public sharing. They use Marionette preset format version 3 with `program: blender`. Their supplied mappings and reference data are preserved without modification.

## Downloads

- [Mixamo_Full_FK_Portable.json](../marionette_workflow/presets/Mixamo_Full_FK_Portable.json) — [download JSON](https://raw.githubusercontent.com/KillianPi22/marionette-workflow-helper/main/marionette_workflow/presets/Mixamo_Full_FK_Portable.json).
- [Tripo_Full_FK.json](Tripo_Full_FK.json) — [download JSON](https://raw.githubusercontent.com/KillianPi22/marionette-workflow-helper/main/presets/Tripo_Full_FK.json).

If the download link displays JSON in the browser, save the file with its `.json` extension. On the GitHub file page, **Download raw file** also saves it.

## Mixamo Full FK Portable

The existing extension preset is identical to the file supplied for this addition. It contains four FK variants, each with 52 mapped body and finger joints:

| Bone names | Position channels | Preset name |
| --- | --- | --- |
| `mixamorig:` prefix | Hips only | Mixamo Full FK - Mixamorig - Hips Position |
| `mixamorig:` prefix | All mapped bones | Mixamo Full FK - Mixamorig - All Position |
| No prefix | Hips only | Mixamo Full FK - No Prefix - Hips Position |
| No prefix | All mapped bones | Mixamo Full FK - No Prefix - All Position |

All four disable IK and contain no saved T-pose. Choose the naming variant that matches the capture rig. For a saved reference pose specific to your character, prepare the capture copy, save its reference pose and export a preset with the helper.

## Tripo Full FK

The file contains **Tripo - Full FK - Character Calibrated**, using `mixamorig:` bone names, 52 mapped body and finger joints, rotation and position channels on all mapped joints, and IK disabled. Its saved T-pose contains 65 bone reference entries.

This calibration belongs to the character used to create the preset. It is not a universal calibration for every Tripo export. If your character's proportions, rest pose or object transforms differ, use **Prepare Capture Copy**, adjust and **Save Current T-Pose**, then **Export Preset JSON** for that character. Keep changes on the capture copy.

## Import in Blender

1. Download the JSON matching your capture rig and reference pose.
2. In the official **Marionette** Blender panel, choose the capture copy as **Control Rig**.
3. Use **Import Presets**, select the JSON, then select the newly imported preset in the list.
4. Check the chosen rig, mapped bone names and reference pose before connecting or capturing.

The official Marionette application and Blender plugin are separate requirements. These files are not extension installers or character-import presets for the standalone application. The helper does not install them into the official plugin automatically.

For **Hips Position**, the detailed guide records an import behavior in official plugin 1.0.1 that re-enables limb position channels. See the [official-plugin import note](../marionette_workflow/README_EN.md#tripo-and-a-twisted-character) and the detailed guide before choosing that variant. Recheck the imported channel settings.

## Release scope

These links expose the presets in the repository. Mixamo remains in the existing extension package; Tripo is a separate download. The published 1.4.0 release assets and the add-on's behavior are unchanged by this addition.
