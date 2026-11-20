# Marionette Workflow Helper 1.4.0

An independent Blender companion for a **Mixamo or Tripo character → Marionette capture → original character → NLA** workflow. All controls and documentation are in English.

Requires Blender 5.2 or newer. Tested with **Blender 5.2.1 LTS** and the installed **Marionette for Blender 1.0.1 / November 2026** plugin. The official plugin and the Marionette application are separate requirements for live preview and Copy to DCC. This helper does not replace them.

## Install

1. Keep the official **Marionette for Blender** plugin installed and enabled.
2. In Blender, open **Edit → Preferences → Add-ons**, open the menu in the top-right corner, and choose **Install from Disk**.
3. Select **marionette_workflow-1.4.0.zip**. Do not install the outer `Marionette_Workflow_Pack_1.4.0.zip`.
4. Enable **Marionette Workflow Helper** if Blender does not enable it automatically.
5. In the 3D Viewport, press **N** and open the **Mocap Workflow** tab.

If the tab is missing, move the mouse over the 3D Viewport before pressing N, check the enabled add-on, then restart Blender if necessary.

**Updating from 1.0.0 or 1.1.0:** save your work, install 1.3.0 with Overwrite enabled, and restart Blender. Existing sessions remain compatible. For a Tripo character prepared with 1.0.0, finish the old capture session and prepare a new copy using the Tripo profile. The old capture collection and Actions are kept; the helper does not delete them.

## First capture

1. Select your **original character**, either its armature or a mesh bound to it. Click **Use Selected Character**. Choose **Rig Profile → Mixamo** for a Mixamo character or **Tripo (Mixamo Skeleton)** for a Tripo humanoid exported with Mixamo names.
2. Click **1. Prepare Capture Copy**. The helper makes a separate armature and optional preview meshes, clears animation on that copy, restores its rest pose, applies rotation and scale to the copy, and sets its bones to XYZ Euler. Your original character's Actions, NLA tracks, rest skeleton and rotation modes are kept. The Tripo profile can also **Straighten Arms for T-Pose** on the copy; this adjusts the upper/lower arms without borrowing the bone roll from another character. The resulting reference pose is stored with the copy.
3. Leave **Map All Finger Joints** enabled. **All Mapped Bones** reproduces the position-channel settings of the original basic preset and is the Tripo default. **Hips Only (FK)** exports translation only on the hips; see the import note below before using this option.
4. Inspect the capture copy. If you adjust its pose manually in Pose Mode, click **Save Current T-Pose** before capturing animation. Then click **Export Preset JSON**. The exported preset always uses the saved reference, even if you export again while a captured take is displayed.
5. In Blender's official **Marionette** tab, set **Control Rig** to the capture copy named in the helper. Use **Import Presets** to import the exported JSON, and **select that newly imported preset** in the list. Click **Connect**. In the Marionette application, enable **Show Preview in DCC** and inspect the movement. Use matching frame rates in Blender and Marionette. There is no automatic setup button in 1.1.0; the helper does not edit the official plugin's settings or preset files.
6. In the Marionette application, click **Copy to DCC** and wait for it to finish. Then **Disconnect** in Blender and wait for the disconnect to complete.
7. Return to **Mocap Workflow**. The **Capture Action** line should now show the imported take. If the original target has an active Action, click **Push Target Action to NLA** first; an active Action would otherwise override the NLA stack. A static T-pose Action can instead be unlinked manually in the Action Editor.
8. Set **Take Name**, **Place Clip**, and **Blend In (frames)**. Click **3. Bake and Add to Target NLA**.

The helper samples the capture Action, converts it into the original rig's bone spaces and rotation modes, and creates an independent Action. It adds a new NLA track, shows the original character, and hides the capture preview. The capture collection is excluded from renders.

**After Existing Clips** places the new strip after the latest unmuted target clip, with an overlap equal to Blend In. **At Current Frame** uses the current scene frame. The new strip uses Replace blending and Nothing extrapolation. Existing tracks are not renamed, retimed or muted.

If you only need editable keyframes, choose **Bake Only (New Action)**. The resulting Action is kept with a fake user and can be selected on the target in the Action Editor. This does not replace the target's current Action or add a strip.

## More takes

Use **Show Capture**, reconnect, and repeat Preview → Copy to DCC → Disconnect → Bake. Reuse the capture copy and preset. Each bake creates a separate Action, even when Marionette updates the same source take. **Show Target** returns to the original character for playback.

Use **Finish Capture Session** when done. It restores original visibility and releases the helper's session references. Capture objects, source Actions and baked Actions remain available. Save your `.blend` file to keep the session and its objects. No scene file is saved automatically.

## New in 1.3.0: post-capture pose adjustments

Use this optional stage **after Copy to DCC and Disconnect, before Bake and Add to Target NLA**. It creates an editable Action with manual corrections to root travel, wrist depth and torso lean. It works on the same Mixamo-named FK skeletons supported by the helper, including the supplied Tripo minotaur.

This is **pose adjustment, not optical lens undistortion**. There is no universal iPhone 0.5x preset. Wide-angle perspective, lens distortion, camera height, occlusion and motion-estimation mistakes can produce different errors. A 3D take alone does not contain the original camera calibration or enough information to recover the true pose automatically. Optical correction belongs before tracking and needs a suitable lens model/calibration; see the [OpenCV calibration guide](https://docs.opencv.org/3.4.19/dc/dbb/tutorial_py_calibration.html).

### First correction

1. After Copy to DCC, **Disconnect** the official plugin. Click **Show Capture** to see the capture copy.
2. Expand **Post-Capture Adjustments (Optional)**. Set **Correction Rig** to the capture copy if it is not already selected. Its copied take must be the active Action. Click **Use Active Take** once to remember the source.
3. Choose **Depth Axis** to match the filming direction: World Y, World X, or a static **Reference Camera** aligned with the recording view. The camera option only supplies its horizontal direction; focal length and lens distortion are not inferred. A parented, constrained, animated or vertically aimed reference camera is rejected.
4. Change one control slightly, then click **Build Corrected Copy**. For interactive adjustments, click **Start Live Preview**, then change sliders or scrub the timeline. Click **Build Corrected Copy** to commit the full take, or **Stop Preview / Restore** to return to the previous Action.
5. Use **Show Original** and **Show Corrected**, scrubbing the same frames from the same Blender viewpoint. Compare with the same source-video frame. Every build starts from the remembered original, so repeated builds do not compound the correction.
6. Leave the preferred Action displayed, then use **3. Bake and Add to Target NLA**. The normal transfer uses whichever Action is active on the capture copy. You can also edit the corrected Action directly, or reduce its keys after validation.

| Control | Effect |
| --- | --- |
| Root Depth Gain | Scales hips travel along the chosen depth axis, relative to the first source frame. 1 is unchanged, below 1 compresses travel, above 1 increases it. It does not relocate the first frame or change body proportions. |
| Hand Depth Gain | Changes wrist depth relative to the upper chest. 1 is unchanged. Arm IK preserves each frame's captured upper/lower segment lengths and wrist world orientation. Choose Both, Left or Right. |
| Torso Pitch / Roll | Tilts the spine subtree around the horizontal view-right/depth axes. The pelvis and legs are not tilted. Adjust by a few degrees initially, then compare. |
| Strength | Blends the chosen correction amount. 0 reproduces the sampled original; 1 applies the full settings. |
| Keep Original Foot Positions | After root travel edits, solves the legs toward the original animated ankle positions and retains ankle world orientation. These are moving source targets, not detected floor contacts. |
| Limit to Scene Frame Range | Applies the correction only inside the scene playback range, with Blend Frames easing it in and out. The entire source take is still sampled into the new Action. |

Start with neutral values (gains 1, angles 0). There is deliberately no baked-in correction percentage for the iPhone lens. For an arm reaching too far toward the camera, try a small reduction in Hand Depth Gain; for a consistently leaning torso, try Torso Pitch. These are starting experiments, not estimates of the correct motion.

**Reach limits:** an ankle or wrist target may become unreachable. The tool clamps the reach and reports how many frames are affected; it does not stretch the limb to force the target. Reduce the adjustment, narrow its frame range, or accept that a foot cannot stay at its original position with that root trajectory. It preserves the segment lengths already present in each source frame, so it does not remove stretching that exists in the input. Nearly straight limbs have an ambiguous bend plane; inspect elbow and knee direction when making large corrections. This stage does not detect contact, remove foot sliding, prevent intersections, recover occluded motion, or align a hand to a held prop.

**Source and timing:** each result is a separate Action with a fake user, and the remembered source is also kept. Existing source keys, handles and interpolation are untouched. Unkeyed bone components are frozen when Use Active Take is clicked, so returning to the original cannot inherit changes from the fully keyed result. The output has Linear keys at every integer frame plus fractional endpoints; equality outside the correction range is guaranteed at the sampled frames, not for every subframe of an originally curved interpolation. Old results remain in the Action list until you remove them.

**Next capture:** before reconnecting, show the original take and confirm the official Control Rig. After another Copy to DCC and Disconnect, click **Use Active Take** again. Marionette may update an existing Action; this helper cannot protect a take from being overwritten by another application's Copy to DCC. Save important takes separately before recapturing.

The correction stage requires a bone-transform Action, Replace blending with influence 1, Euler or Quaternion bones, direct upper/lower/hand and upper/lower/foot chains, and no active NLA blending, constraints or drivers. It also works on a compatible standalone FK rig, but the normal target/NLA transfer still requires a capture copy prepared for that target.

For future footage, try the rear **1x** camera from farther away, keeping the full body visible and the phone steady, then compare the solve. Correcting a calibrated video before tracking may help lens distortion; it cannot remove perspective foreshortening or restore occluded joints. The official [Marionette tutorials](https://marionettemocap.com/tutorials) also cover cleanup and rig adjustments.

## Tripo and a twisted character

The inspected Tripo minotaur uses `mixamorig:` bone names, just like the X Bot. Its bone axes, proportions and relaxed arm pose are different. Matching names do **not** make a saved X Bot T-pose valid for this character. Some of their reference-bone rotations differ by nearly 180 degrees.

For this Tripo model, use **Tripo (Mixamo Skeleton)**, keep **All Mapped Bones** initially, prepare a new capture copy, and export/import its character-specific preset. Do not select `Simple_Mixamo` or the X Bot calibrated preset for this model. Recheck Control Rig as well as the selected preset before connecting. Mute any previously incorrect take when testing the new result.

**Official plugin 1.0.1 import note:** importing a preset re-enables Position on both upper/lower arms and upper/lower legs when its IK flags are read. All Mapped Bones round-trips unchanged. If you choose Hips Only to keep a rotation-only limb chain, open the official preset editor after importing and turn off **Copy Position** on Left/Right UpperArm, LowerArm, UpperLeg and LowerLeg. Keep it enabled for Hips. Recheck after loading presets again. The helper displays a reminder for this mode; it does not modify the official importer or silently edit its settings.

**Straighten Arms for T-Pose** only makes the upper and lower arms horizontal. It keeps anatomical wrist roll and does not repair skin weights, force finger poses, or reshape the creature. If the hands need a different reference orientation, rotate them on the capture copy, click **Save Current T-Pose**, export again, and import/select the new preset. **Restore** returns to the stored reference. Saving or restoring the reference is blocked while a capture Action or unmuted capture NLA is active, to avoid treating an animation frame as calibration.

This Tripo profile is for humanoid **Mixamo-named** exports, including the supplied minotaur. It does not claim support for Tripo native, UE5, VRM, ActorCore or non-humanoid skeleton conventions. Those need separate naming maps and validation.

## Included presets

- **Mixamo_Full_FK_Portable.json**: four presets combining `mixamorig:` or unprefixed bone names with Hips Only or All Mapped Bones position channels. They contain complete mappings but no character-specific T-pose. Marionette 1.0.1 can use the rig's rest pose when no T-pose is saved. Older plugin versions need Edit → T-pose → Save. Use an Euler capture rig, not an animated quaternion target.
- **Mixamo_Full_FK_From_Basic.json**: extends your supplied `Simple_Mixamo` preset with all available finger joints and correct FK assignments, while retaining its saved T-pose. Two variants cover Hips Only and All Mapped Bones. Use this only with the same character, bone names and object transforms as your original basic preset. For another character, generate a calibrated preset with the helper.
- **Tripo_Minotaur_Full_FK_1.1.0.json**: a separate 52-joint preset generated from the supplied Tripo minotaur FBX, with a saved arm T-pose and All Mapped Bones position channels. Its complete mapping, flags and calibration are checked against the official importer. Use it with a freshly prepared capture copy of that exact model. If the rig's proportions, rest bones or object transforms differ, export a new preset from your current copy instead.
- **Export Preset JSON**: creates a complete preset calibrated for the current capture copy. Import it through the **Import Presets** control in the official Blender plugin when needed.

The official import format is JSON **version 3**, `program: blender`. These files are for **Marionette for Blender**, not a character-import preset for the standalone application.

The full standard mapping contains **52 joints**: 22 body joints and 30 finger joints. Mixamo `Spine`, `Spine1`, and `Spine2` map to Spine, Chest, and UpperChest. `HandPinky1/2/3` map to Little Proximal/Intermediate/Distal. ToeBase maps to Toes. Toe-end and finger-end bones are not IK controls. All four BendGoal slots are empty and IK is disabled. Eye slots are mapped only when matching eye bones exist; a standard X Bot has none.

Mapping finger joints does not generate finger movement if the source capture contains none.

## Supported setup and limits

- This version supports local, unparented **Mixamo-named FK humanoid rigs** with positive uniform object scale. Common `mixamorig`, numbered namespace, and unprefixed names are recognized. Ambiguous or missing required bones are reported. Mixamo uses its T-pose rest skeleton; Tripo can calibrate relaxed arms into a T-pose on the copy.
- It is not a universal retargeter for Rigify, custom IK controllers, constraints, drivers, or arbitrary imported FBX skeletons. It transfers motion from the copy it prepared back to its matching target.
- Do not move either rig, edit their rest bones, or change their parenting after preparation. Object-level animation is rejected. Bone rotations, translations and scales in the capture Action are sampled; only that Action's assigned slot is used. Capture NLA tracks are temporarily excluded from evaluation during baking.
- Use matching Blender/Marionette frame rates. The helper preserves the scene frame rate and copies frame timing; it does not resample between frame rates. The official plugin may change Blender's frame rate during Copy to DCC, so check it before evaluating existing Mixamo clips.
- Tweak Mode, connected live preview, and target NLA Solo tracks must be turned off before transfer. An active target Action must be pushed down before automatic NLA placement.
- A transfer samples every integer frame and includes fractional start/end keys. Keys use Linear interpolation. Use the Action Editor or your Keyframe Reducer afterward if you want fewer keys. For editing a strip in place, select it in the NLA editor and enter Tweak Mode; exit Tweak Mode before another transfer.
- Blend In creates an NLA crossfade. It does not align different root trajectories, fix foot sliding, or solve contact. Inspect transitions and adjust hips/root curves if necessary. The helper does not extend the scene playback range automatically.
- Scene operations support Blender Undo. Exported JSON files are persistent files and are not undone by Blender Undo. Importing and managing official Marionette presets is done in the official plugin.

## Validation

The included test reports cover a real Mixamo scene and the supplied Tripo FBX, preservation of original meshes/rigs/Actions/NLA tracks, preset parsing and setup-message creation through the installed official plugin, pose application, bone/mesh motion comparisons, quaternion and Euler target rotations, saved reference restoration, and NLA placement. The helper does not modify the installed official plugin.

`CORRECTION_VALIDATION_REPORT.json` covers synthetic takes on those actual rigs: source preservation, comparison with unkeyed joints, fixed limb lengths, reachable ankle/wrist targets, clamped IK, range blending, repeated builds, Action-slot isolation, reference-camera guards and transfer back to the target. The current iPhone video and its copied take were not available for artistic or optical validation.

A live round trip with the standalone Marionette application has not been tested automatically. Use a short take for the first live check.

## License and independence

Copyright 2026 Killian Pichon. GPL-3.0-or-later; see LICENSE. This is an independent companion, not an official Marionette product. The official plugin and standalone app retain their own licenses.

Official plugin and tutorials: <https://marionettemocap.com/tutorials>


## Interactive preview and ground compensation (1.3.0)

After **Use Active Take**, click **Start Live Preview**. The current frame refreshes roughly every 0.12 seconds plus evaluation time. It does not rebuild the whole take while dragging a slider. Scrubbing works; playback is a lightweight inspection preview and is not guaranteed to run at the scene frame rate. The source keys remain untouched. **Build Corrected Copy** ends the preview and calculates the full take from the original. **Stop Preview / Restore** restores the Action displayed before preview started. Show Original / Show Corrected also end preview. Save, Undo, loading a file and rendering stop it automatically. Save a committed corrected Action if you want the correction in a render or a reopened scene. Do not reconnect Marionette or edit keys during preview.

The original upper-body controls still work. New lower-body controls are:

| Setting | Effect |
| --- | --- |
| Pelvis Height | Moves the hips and their descendants vertically; with Keep Original Foot Positions, the legs solve back toward the original ankles. |
| Foot Depth Gain | Adjusts ankle depth relative to the source hips; 1 is neutral. |
| Stance Width Gain | Adjusts ankle separation along the view-right axis; 1 is neutral. |
| Left / Right Foot Height Offset | Raises or lowers the individual ankle target. |
| Ground Blend | Blends ankle targets toward the ground plane. 0 disables ground projection; 1 projects fully, subject to leg reach. |
| Ground Height | World Z height of the plane at world X=Y=0. |
| Ground Slope X / Y | Inclines the plane along world X or Y. Both 0 means a horizontal floor. |
| Left / Right Ankle Clearance | Distance from the plane to the ankle joint, measured along the plane normal. Adjust for the character's anatomy; the default 0.08 is in Blender units, not an inferred sole thickness. |
| Left / Right Ground Influence | Per-foot weight. Set 0 for a lifted foot; 1 allows the Ground Blend amount. |

For a flat floor, leave slopes at zero, set Ground Height to your floor, then increase Ground Blend gradually. Adjust ankle clearances while viewing the mesh from the side. Ground projection targets the ankle joints: it does not fit mesh soles, rotate feet onto a slope or detect contact. The existing ankle orientations are retained. It can pull an intentionally lifted foot downward, so reduce that foot's influence or use Limit to Scene Frame Range / Blend Frames for the contact interval. If the legs cannot reach, the status reports a reach limit. Lower Pelvis Height or reduce the correction; limbs are not stretched.

An inclined plane is supported. Arbitrary uneven terrain, stairs and mesh collision are not supported by this version; use the individual offsets and frame ranges for manual adjustments. These controls compensate the resulting pose, without assuming a universal lens correction.

The preview and final bake use the same frame-local leg/arm solve, so scrubbing backward does not accumulate corrections. Near perfectly straight limbs, the bend direction remains ambiguous; inspect knees and elbows. The tests validate current-frame preview versus committed Actions, scrubbing, temporary-data cleanup, selected-foot ground influence and sloped-plane targets on the supplied Mixamo and Tripo rigs. Visual tuning of the user's current take is still required.


## 1.3.1: stale preview recovery

Undo/Redo or reopening can restore a temporary one-frame Action without its Python preview session. The helper now recognizes these orphaned previews, restores the remembered original Action and retains your slider values. Restart Live Preview to evaluate them again. Recovery runs after Undo/Redo/load, at registration and before saving if no preview session is active. Previous 1.3.0 temporary Actions are recognized too. The source keys are unchanged.

Stance Width Gain of 0 collapses the ankle targets onto the hips along the selected view-right axis. Use 1 as the neutral starting point. Ground Blend of 1 projects the ankle target onto the plane and overrides its height offset: use per-foot Ground Influence or a frame range for lifted feet. The UI displays reminders for these cases.


## 1.4.0: gait and whole-body alignment

These are manual correction parameters for an existing walk. They do not generate a walk cycle, infer true motion from a lens, synchronize gait phases or automatically remove a limp. Compare the same frames with the source video, especially before making both feet symmetrical: a normal step includes unequal foot heights.

Start with **Reset Gait Adjustments**. This resets lower-body gains/offsets and disables ground projection, while preserving torso settings and ground calibration. For a rigid whole-body alignment test, also set **Torso Pitch / Roll** to zero yourself so an older waist correction is not stacked with it.

- **Whole Body Pitch / Roll** rotates the entire sampled pose around the hips before other adjustments. With other corrections neutral, it preserves joint angles and distances: it adds no bend at the waist. It preserves any curve already present in the source; it does not straighten an already bent spine. Ground correction may subsequently bend the legs to reach their targets.
- **Left / Right Step Height Gain** scales positive ankle height above the calibrated plane and ankle clearance. 1 is unchanged. Use small differences to reduce an exaggerated swing or restore a step that is too low. Existing below-ground penetration is not amplified. This is a height multiplier, not a constant height offset, and does not change step timing. Unreachable targets are clamped and reported.
- **Pelvis Vertical Motion Gain** scales vertical hips travel relative to the first source frame. Below 1 reduces vertical bobbing; above 1 increases it. With Keep Original Foot Positions, legs solve toward the reference ankle targets. Whole-body alignment is included in those reference targets.
- **Foot Depth Gain** adjusts the feet relative to the hips along the selected world/camera depth axis. Use it to tune reach, not playback speed. **Stance Width Gain** adjusts separation; 1 is neutral.
- **Ground Mode: Near Ground Only** is the new default. Ground Blend gradually releases as the ankle rises above its clearance. At **Ground Release Height**, its projection is fully released, retaining the lifted step. This is a height-based heuristic, not contact detection or foot locking. Set the release height to fit the scale of your character.
- **Ground Mode: Always Project** retains the old projection behavior, including lifted feet. Select this explicitly if you want the pre-1.4 behavior. With Ground Blend=1 it overrides vertical foot offsets.

Suggested tuning order: neutral lower body; torso offsets neutral if testing whole-body alignment; small Whole Body Pitch/Roll; Foot Depth and Stance Width; separate step-height gains; pelvis vertical gain; finally Near Ground Only with modest Ground Blend. Scrub a complete left/right step cycle, including lifts and contacts. Keep corrections local with the scene frame range when the take also contains a crouch, pickup or deliberate weight shift. A sloped plane remains supported, not arbitrary terrain.

Live Preview and Build Corrected Copy use the same controls. Whole-body alignment does not change the rig's object transform or rest pose. All controls and the guide remain in English.


### Interface in 1.4.0

The top switch selects **Motion Cleanup** (default) or **Capture / NLA**. Motion Cleanup shows only the active-take workflow: source, preview, collapsible Body Alignment / Gait / Ground Contact / Hand Reach / Range sections, and Build Corrected Copy. Capture / NLA retains character preparation, preset export and transfer controls.

Local torso offsets and individual constant foot offsets are collapsed by default. A reminder remains visible when hidden offsets are nonzero. **Clear Torso Offsets** removes the old local bend while preserving whole-body alignment. **Reset Gait / Body Values** resets gait and whole-body controls while retaining torso settings and ground calibration. Ground calibration fields appear when Ground Blend is above zero. The Corrected comparison button is disabled during temporary live preview; commit or stop preview first. Slider edits still update the preview even when their section is later collapsed. Source keys are preserved.
