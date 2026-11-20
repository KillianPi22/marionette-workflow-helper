"""Self-contained migration smoke checks; no production rigs or official plugin."""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import marionette_workflow as addon

checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS:', name, flush=True)


def signature(action):
    return [(fc.data_path, fc.array_index, [(tuple(k.co), k.interpolation,
             tuple(k.handle_left), tuple(k.handle_right)) for k in fc.keyframe_points])
            for fc in addon.workflow.curves(action)]


def make_rig(profile):
    """Generate a simple humanoid with direct limb chains and Mixamo-style names."""
    joints = {
        'Hips': (None, (0, 0, 1)), 'Spine': ('Hips', (0, 0, 1.15)),
        'Chest': ('Spine', (0, 0, 1.35)), 'UpperChest': ('Chest', (0, 0, 1.5)),
        'Neck': ('UpperChest', (0, 0, 1.65)), 'Head': ('Neck', (0, 0, 1.75)),
    }
    for side, sign in [('Left', 1), ('Right', -1)]:
        joints.update({
            side+'Shoulder': ('UpperChest', (sign*.12, 0, 1.55)),
            side+'UpperArm': (side+'Shoulder', (sign*.25, 0, 1.55)),
            side+'LowerArm': (side+'UpperArm', (sign*.55, 0, 1.55)),
            side+'Hand': (side+'LowerArm', (sign*.8, 0, 1.55)),
            side+'UpperLeg': ('Hips', (sign*.13, 0, 1)),
            side+'LowerLeg': (side+'UpperLeg', (sign*.13, 0, .55)),
            side+'Foot': (side+'LowerLeg', (sign*.13, 0, .1)),
            side+'Toes': (side+'Foot', (sign*.13, -.15, .05)),
        })
    prefix = 'mixamorig:' if profile == 'MIXAMO' else 'Synthetic:mixamorig1:'
    names = {human: prefix + addon.mapping.BODY[human] for human in joints}
    data = bpy.data.armatures.new(profile+' Synthetic Skeleton')
    rig = bpy.data.objects.new(profile+' Synthetic Rig', data)
    bpy.context.collection.objects.link(rig)
    addon.workflow.select_only(bpy.context, [rig], rig)
    bpy.ops.object.mode_set(mode='EDIT')
    for human, (parent, head) in joints.items():
        bone = data.edit_bones.new(names[human])
        bone.head = head
        children = [point for other, (owner, point) in joints.items() if owner == human]
        bone.tail = children[0] if children else (head[0], head[1], head[2]+.08)
        if parent:
            bone.parent = data.edit_bones[names[parent]]
        # Distinct synthetic roll tests profile-specific reference retention.
        bone.roll = .35 if profile == 'TRIPO' else 0
    bpy.ops.object.mode_set(mode='OBJECT')
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
    return rig, names


addon.register()
check('register exposes scene settings', hasattr(bpy.types.Scene, 'mw_settings'))
check('default interface is Motion Cleanup', bpy.context.scene.mw_settings.workspace_mode == 'CLEANUP')
check('preview is initially inactive', not addon.preview.active())
check('official plugin is not imported', not any(n == 'marionette' or n.startswith('marionette.') for n in sys.modules))

mapping = addon.mapping
full_names = ['mixamorig:' + n for n in (*mapping.BODY.values(), *mapping.FINGERS.values())]
for profile in ('MIXAMO', 'TRIPO'):
    rows, missing, ambiguous = mapping.build_map(full_names, profile=profile)
    check(profile+' full mapping has 52 FK joints', sum(bool(row[1]) for row in rows) == 52 and not missing and not ambiguous)
    check(profile+' hips-only position policy', [row[0] for row in rows if row[3]] == ['Hips'])
    check(profile+' no invented IK pole controls', all(not row[1] for row in rows if row[0] in mapping.GOALS))
    all_rows = mapping.build_map(full_names, positions='ALL', profile=profile)[0]
    check(profile+' all-position policy', all(row[3] for row in all_rows if row[1]))
check('ambiguous aliases are reported', 'Hips' in mapping.build_map(full_names+['Hips'])[2])
check('missing required joints are reported', 'Hips' in mapping.build_map([n for n in full_names if not n.endswith(':Hips')])[1])
check('finger mapping can be disabled', sum(bool(row[1]) for row in mapping.build_map(full_names, fingers=False)[0]) == 22)

for profile in ('MIXAMO', 'TRIPO'):
    rig, names = make_rig(profile)
    original_rest = addon.workflow.rest_signature(rig)
    settings = bpy.context.scene.mw_settings
    settings.target, settings.rig_profile, settings.copy_meshes = rig, profile, False
    capture = addon.workflow.prepare(bpy.context, settings)
    check(profile+' isolated capture data', capture.data != rig.data and capture.animation_data is None)
    check(profile+' target rest and rotation modes unchanged', addon.workflow.rest_signature(rig) == original_rest and
          all(pb.rotation_mode == 'QUATERNION' for pb in rig.pose.bones))
    check(profile+' capture uses Euler modes', all(pb.rotation_mode == 'XYZ' for pb in capture.pose.bones))
    check(profile+' profile-specific reference stored', capture.get('mw_profile') == profile and bool(capture.get('mw_reference_pose')))
    preset = addon.workflow.make_preset(capture)
    data = next(iter(preset['presets'].values()))
    check(profile+' preset includes complete synthetic reference', len(data['tpose']) == 22 and sum(bool(row[1]) for row in data['bone_map']) == 22)

    hip = capture.pose.bones[names['Hips']]
    for frame, amount in [(1, 0), (6, .1), (12, .2)]:
        hip.location = (0, 0, amount)
        hip.keyframe_insert('location', frame=frame)
    bpy.context.scene.frame_set(6)
    source = capture.animation_data.action
    original = signature(source)
    settings.adjust_rig = capture
    settings.adjust_pitch = 0
    addon.correction.set_source(bpy.context, settings)
    head_before = capture.matrix_world @ capture.pose.bones[names['Head']].head
    addon.preview.start(bpy.context)
    check(profile+' preview becomes active on temporary Action', addon.preview.active() and capture.animation_data.action != source and
          capture.animation_data.action.get('mw_temporary_preview'))
    settings.adjust_pitch = .1
    addon.preview.tick()
    bpy.context.view_layer.update()
    head_after = capture.matrix_world @ capture.pose.bones[names['Head']].head
    check(profile+' current-frame preview reacts to pitch', (head_after-head_before).length > .001)
    check(profile+' preview preserves source keys and handles', signature(source) == original)
    addon.preview.stop()
    check(profile+' stop restores original Action', not addon.preview.active() and capture.animation_data.action == source)
    check(profile+' stop removes temporary Actions', not any(a.get('mw_temporary_preview') for a in bpy.data.actions))
    check(profile+' source remains unchanged after stop', signature(source) == original)

    settings.adjust_pitch = 0
    baked, slot, frames = addon.workflow.bake(bpy.context, settings)
    check(profile+' bake creates independent full take', baked != source and frames == 12 and bool(addon.workflow.curves(baked, slot)))
    check(profile+' bake preserves capture and target rest', signature(source) == original and addon.workflow.rest_signature(rig) == original_rest)
    check(profile+' finish session restores original visibility', bpy.ops.mw.finish_session() == {'FINISHED'} and settings.capture is None and not rig.hide_get())

cleanup = addon.preview.cleanup
recover = addon.preview.recover_preview
addon.unregister()
check('unregister removes settings', not hasattr(bpy.types.Scene, 'mw_settings'))
check('unregister removes preview handlers', all(cleanup not in handlers for handlers in
      (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre, bpy.app.handlers.undo_pre, bpy.app.handlers.render_pre)) and
      all(recover not in handlers for handlers in (bpy.app.handlers.undo_post, bpy.app.handlers.redo_post, bpy.app.handlers.load_post)))
check('unregister removes preview timers', not bpy.app.timers.is_registered(recover) and not bpy.app.timers.is_registered(addon.preview.tick))
addon.register()
check('extension can be registered again', hasattr(bpy.types.Scene, 'mw_settings'))
addon.unregister()
print('SMOKE_TEST_SUMMARY', json.dumps({'passed': True, 'blender': bpy.app.version_string,
      'checks': len(checks), 'tests': checks}), flush=True)
