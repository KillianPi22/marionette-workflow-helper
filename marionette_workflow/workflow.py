"""Capture-copy workflow. Never change the original rig's rest data or rotation modes."""
import json
import math
import sys

import bpy
from mathutils import Matrix, Vector
from .mapping import build_map
from . import calibration


class WorkflowError(ValueError):
    pass


def require_disconnected(scene):
    if getattr(scene, "mb_wants_to_connect", False):
        raise WorkflowError("Disconnect Marionette before preparing, exporting or transferring.")
    # Extension loaders can remove bl_info. Read only loaded client state, never import or configure the plugin.
    for name, module in tuple(sys.modules.items()):
        if not name.endswith(".operators.client_operators"):
            continue
        client = getattr(module, "client", None)
        if client is not None and not getattr(client, "closed", True):
            raise WorkflowError("Wait for Marionette to disconnect, then try again.")
    if getattr(scene, "mb_editing_preset_old_name", ""):
        raise WorkflowError("Save or cancel the preset being edited in Marionette first.")


def curves(action, slot=None):
    if not action:
        return []
    return [fc for layer in action.layers for strip in layer.strips
            for bag in getattr(strip, "channelbags", ())
            if slot is None or bag.slot_handle == slot.handle for fc in bag.fcurves]


def validate_rig(rig, profile="MIXAMO"):
    if rig is None or rig.type != "ARMATURE":
        raise WorkflowError("Choose a supported humanoid armature as Target Rig.")
    if rig.library or rig.data.library or rig.override_library:
        raise WorkflowError("Use a local, editable rig.")
    if rig.parent:
        raise WorkflowError("Use an unparented humanoid armature.")
    if rig.constraints or any(b.constraints for b in rig.pose.bones):
        raise WorkflowError("Use the deformation rig without constraints or IK controllers.")
    ad = rig.animation_data
    if (ad and ad.drivers) or (rig.data.animation_data and rig.data.animation_data.drivers):
        raise WorkflowError("Rigs with drivers are not supported in this version.")
    if ad and ad.use_tweak_mode:
        raise WorkflowError("Exit NLA Tweak Mode first (Tab in the NLA editor).")
    scale = rig.matrix_world.to_scale()
    if rig.matrix_world.determinant() <= 0 or min(scale) < 1e-8 or max(scale) - min(scale) > max(scale) * 1e-4:
        raise WorkflowError("Use a rig with positive, uniform object scale.")
    actions = []
    if ad:
        if ad.action:
            actions.append((ad.action, ad.action_slot))
        for track in ad.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    actions.append((strip.action, strip.action_slot))
    for action, slot in actions:
        if any(not fc.data_path.startswith('pose.bones[') for fc in curves(action, slot)):
            raise WorkflowError("Object-level animation is not supported. Use bone-only Actions.")
    rows, missing, ambiguous = build_map(rig.pose.bones.keys(), profile=profile)
    if missing or ambiguous:
        raise WorkflowError(calibration.profile_label(profile) + " mapping needs attention: " + ", ".join(missing + ambiguous)
                            + ". This version supports Mixamo-named humanoid exports.")
    return rows


def rest_shape_problems(rig, rows):
    return calibration.pose_problems(calibration.reference_entries(rig, use_rest=True), rows)


def bound_meshes(rig, scene):
    return [obj for obj in scene.objects if obj.type == "MESH" and
            any(m.type == "ARMATURE" and m.object == rig for m in obj.modifiers)]


def select_only(context, objects, active):
    if context.object and context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    for obj in context.selected_objects:
        obj.select_set(False)
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    context.view_layer.objects.active = active


def prepare(context, settings):
    require_disconnected(context.scene)
    target = settings.target
    profile = settings.rig_profile
    rows = validate_rig(target, profile)
    if target.name not in context.view_layer.objects:
        raise WorkflowError("Target Rig must be in the current view layer.")
    if settings.capture:
        raise WorkflowError("A capture copy is already selected. Reuse it for the next take.")
    problems = rest_shape_problems(target, rows)
    if profile == "TRIPO" and settings.straighten_arms:
        problems = [p for p in problems if "arm" not in p]
    if problems:
        raise WorkflowError("The rest pose needs a T-pose: " + "; ".join(problems))
    meshes = bound_meshes(target, context.scene) if settings.copy_meshes else []
    if any(m.library or m.constraints or (m.parent and m.parent != target) for m in meshes):
        raise WorkflowError("Preview meshes must be local and parented only to the target rig.")
    old_selection = list(context.selected_objects)
    old_active = context.view_layer.objects.active
    collection = bpy.data.collections.new("MW Capture - " + target.name)
    context.scene.collection.children.link(collection)
    created, created_data = [], []
    try:
        capture = target.copy()
        capture.data = target.data.copy()
        created_data.append(capture.data)
        collection.objects.link(capture)
        created.append(capture)
        capture.name = target.name + "_Marionette"
        capture.animation_data_clear()
        capture.data.animation_data_clear()
        capture.data.pose_position = "POSE"
        capture.hide_viewport = False
        capture.hide_render = True
        for bone in capture.pose.bones:
            bone.rotation_mode = "XYZ"
            bone.matrix_basis = Matrix.Identity(4)
        for original in meshes:
            preview = original.copy()
            preview.data = original.data.copy()
            created_data.append(preview.data)
            collection.objects.link(preview)
            created.append(preview)
            preview.name = original.name + "_Marionette"
            world = original.matrix_world.copy()
            preview.parent = None
            preview.matrix_world = world
            preview.animation_data_clear()
            if preview.data.shape_keys:
                preview.data.shape_keys.animation_data_clear()
            preview.hide_viewport = False
            preview.hide_render = True
            for modifier in preview.modifiers:
                if modifier.type == "ARMATURE" and modifier.object == target:
                    modifier.object = capture
        select_only(context, created, capture)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        for preview in created[1:]:
            world = preview.matrix_world.copy()
            preview.parent = capture
            preview.matrix_parent_inverse = capture.matrix_world.inverted()
            preview.matrix_world = world
        context.view_layer.update()
        if profile == "TRIPO" and settings.straighten_arms:
            calibration.straighten_arms(context, capture, rows)
        problems = calibration.pose_problems(calibration.reference_entries(capture), rows)
        if problems:
            raise WorkflowError("Reference pose needs adjustment: " + "; ".join(problems))
        calibration.store_reference(capture)
        capture["mw_profile"] = profile
        settings.capture = capture
        settings.capture_collection = collection
        settings.prepared_target = target
        capture["mw_rest_signature"] = rest_signature(target)
        capture["mw_source_signature"] = rest_signature(capture)
        capture["mw_target_world"] = json.dumps([list(row) for row in target.matrix_world])
        capture["mw_capture_world"] = json.dumps([list(row) for row in capture.matrix_world])
        settings.visibility.clear()
        for obj in [target] + bound_meshes(target, context.scene):
            if obj.name in context.view_layer.objects:
                item = settings.visibility.add()
                item.obj = obj
                item.was_hidden = obj.hide_get()
        show_capture(context, settings, True)
        select_only(context, [capture], capture)
        return capture
    except Exception:
        settings.capture = None
        settings.capture_collection = None
        for obj in reversed(created):
            bpy.data.objects.remove(obj, do_unlink=True)
        for data in created_data:
            if data.users == 0:
                (bpy.data.armatures if isinstance(data, bpy.types.Armature) else bpy.data.meshes).remove(data)
        bpy.data.collections.remove(collection)
        select_only(context, [o for o in old_selection if o.name in context.view_layer.objects], old_active)
        raise


def rest_signature(rig):
    return json.dumps([(b.name, b.parent.name if b.parent else "", [round(v, 6) for row in b.matrix_local for v in row])
                       for b in rig.data.bones])


def show_capture(context, settings, capture_visible):
    for item in settings.visibility:
        if item.obj and item.obj.name in context.view_layer.objects:
            item.obj.hide_set(True if capture_visible else item.was_hidden)
    if settings.capture_collection:
        for obj in settings.capture_collection.objects:
            if obj.name in context.view_layer.objects:
                obj.hide_set(not capture_visible)
    settings.capture_visible = capture_visible


def make_preset(rig, fingers=True, positions="HIPS", name=None):
    profile = rig.get("mw_profile", "MIXAMO")
    rows, missing, ambiguous = build_map(rig.pose.bones.keys(), fingers, positions, profile)
    if missing or ambiguous:
        raise WorkflowError("Missing or ambiguous bones: " + ", ".join(missing + ambiguous))
    if any(b.rotation_mode not in {"XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"} for b in rig.pose.bones):
        raise WorkflowError("Use Prepare Capture Copy first; Marionette requires Euler rotation modes.")
    if not calibration.reference_matches_scene(rig):
        raise WorkflowError("The capture rig moved after calibration. Restore its object transform first.")
    entries = calibration.stored_reference(rig)
    problems = calibration.pose_problems(entries, rows)
    if problems:
        raise WorkflowError("Reference pose needs adjustment: " + "; ".join(problems))
    tpose = [{key: value for key, value in e.items() if key != "local_scale"} for e in entries]
    label = "Tripo" if profile == "TRIPO" else "Mixamo"
    return {"version": 3, "program": "blender", "presets": {
        name or label + " Full FK - " + rig.name: {"enable_ik": [False] * 4, "bone_map": rows, "tpose": tpose}}}


def update_reference(context, settings, restore=False):
    require_disconnected(context.scene)
    rig = settings.capture
    if not rig:
        raise WorkflowError("Prepare Capture Copy first.")
    ad = rig.animation_data
    if ad and (ad.action or ad.use_tweak_mode or any(not t.mute and any(not s.mute for s in t.strips) for t in ad.nla_tracks)):
        raise WorkflowError("Set the reference before Copy to DCC. A capture Action/NLA is active; start a new session to recalibrate.")
    if not calibration.reference_matches_scene(rig):
        raise WorkflowError("Restore the capture rig's object transform before calibrating.")
    if restore:
        calibration.restore_reference(rig)
    else:
        rows = validate_rig(rig, rig.get("mw_profile", "MIXAMO"))
        context.view_layer.update()
        if any(pb.rotation_mode not in calibration.EULER_ORDERS for pb in rig.pose.bones):
            raise WorkflowError("Keep the capture bones in Euler rotation modes.")
        if any(abs(s - 1) > 1e-4 for pb in rig.pose.bones for s in pb.scale):
            raise WorkflowError("Reference poses may rotate bones, but must not scale them.")
        problems = calibration.pose_problems(calibration.reference_entries(rig), rows)
        if problems:
            raise WorkflowError("Reference pose needs adjustment: " + "; ".join(problems))
        calibration.store_reference(rig)
    context.view_layer.update()


def validate_capture(context, settings):
    require_disconnected(context.scene)
    target, source = settings.target, settings.capture
    validate_rig(target, settings.rig_profile)
    if not source or source == target or settings.prepared_target != target:
        raise WorkflowError("Prepare a capture copy for this target first.")
    if source.get("mw_profile", "MIXAMO") != settings.rig_profile:
        raise WorkflowError("The profile changed. Finish this session and prepare a new capture copy.")
    if source.name not in context.view_layer.objects or target.name not in context.view_layer.objects:
        raise WorkflowError("Both rigs must be in the current view layer.")
    if target.data.pose_position != "POSE" or source.data.pose_position != "POSE":
        raise WorkflowError("Both armatures must use Pose Position, not Rest Position.")
    if rest_signature(target) != source.get("mw_rest_signature") or rest_signature(source) != source.get("mw_source_signature"):
        raise WorkflowError("The rest skeleton changed after preparation. Prepare a new capture copy.")
    for rig, key in ((target, "mw_target_world"), (source, "mw_capture_world")):
        old = Matrix(json.loads(source[key]))
        if max(abs(a - b) for ar, br in zip(old, rig.matrix_world) for a, b in zip(ar, br)) > 1e-5:
            raise WorkflowError("An armature was moved after preparation. Restore its object transform first.")
    if source.constraints or any(b.constraints for b in source.pose.bones):
        raise WorkflowError("Remove constraints from the capture copy before transfer.")
    ad = source.animation_data
    if not ad or not ad.action or not ad.action_slot:
        raise WorkflowError("Copy to DCC in Marionette first; the capture copy needs an active Action.")
    if ad.use_tweak_mode or ad.drivers:
        raise WorkflowError("Exit Tweak Mode and remove drivers on the capture copy.")
    fcurves = curves(ad.action, ad.action_slot)
    if not any(fc.keyframe_points or fc.sampled_points for fc in fcurves):
        raise WorkflowError("The capture Action has no keys in the assigned Action slot.")
    if any(not fc.data_path.startswith('pose.bones[') for fc in fcurves):
        raise WorkflowError("The capture Action must contain bone animation only.")
    return target, source


def sample_frames(start, end):
    if not math.isfinite(start + end) or end <= start:
        raise WorkflowError("The capture Action must span more than one frame.")
    if end - start > 50000:
        raise WorkflowError("Limit each transfer to 50,000 frames or fewer.")
    return [start] + [float(f) for f in range(math.floor(start) + 1, math.ceil(end)) if start < f < end] + [end]


def bake(context, settings):
    target, source = validate_capture(context, settings)
    source_ad = source.animation_data
    source_curves = curves(source_ad.action, source_ad.action_slot)
    times = [p.co.x for fc in source_curves for p in (*fc.keyframe_points, *fc.sampled_points)]
    frames = sample_frames(min(times), max(times))
    scene = context.scene
    old_frame, old_subframe = scene.frame_current, scene.frame_subframe
    old_nla = source_ad.use_nla
    old_influence, old_blend = source_ad.action_influence, source_ad.action_blend_type
    old_pose = {p.name: p.matrix_basis.copy() for p in source.pose.bones}
    old_hidden = source.hide_get()
    action = bpy.data.actions.new(settings.clip_name.strip() or "Marionette Take")
    action.use_fake_user = True
    slot = action.slots.new(id_type="OBJECT", name=target.name)
    layer = action.layers.new("Captured Motion")
    bag = layer.strips.new(type="KEYFRAME").channelbags.new(slot)
    tracks, previous = {}, {}
    for bone in target.pose.bones:
        if bone.rotation_mode == "AXIS_ANGLE":
            bpy.data.actions.remove(action)
            raise WorkflowError("Axis-angle target bones are not supported. Use Euler or Quaternion.")
        rotation = "rotation_quaternion" if bone.rotation_mode == "QUATERNION" else "rotation_euler"
        for prop, count in (("location", 3), (rotation, 4 if rotation == "rotation_quaternion" else 3), ("scale", 3)):
            for index in range(count):
                tracks[(bone.name, prop, index)] = []
    try:
        source.hide_set(False)
        source_ad.use_nla = False
        source_ad.action_influence = 1
        source_ad.action_blend_type = "REPLACE"
        # Reset unkeyed channels so streamed leftovers cannot leak into a new take.
        calibration.restore_reference(source)
        context.view_layer.update()
        inverse_target = target.matrix_world.inverted()
        # Applying object scale changes bone lengths but keeps orthonormal bone axes.
        # Match corresponding rest frames to preserve the target's original unit scale.
        rest_offsets = {
            b.name: (source.matrix_world @ source.data.bones[b.name].matrix_local).inverted()
                    @ target.matrix_world @ b.matrix_local for b in target.data.bones}
        for frame in frames:
            scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
            context.view_layer.update()
            evaluated = source.evaluated_get(context.evaluated_depsgraph_get())
            wanted = {b.name: inverse_target @ evaluated.matrix_world @ b.matrix @ rest_offsets[b.name]
                      for b in evaluated.pose.bones}
            for bone in target.pose.bones:
                kwargs = {}
                if bone.parent:
                    kwargs = {"parent_matrix": wanted[bone.parent.name],
                              "parent_matrix_local": bone.parent.bone.matrix_local}
                basis = bone.bone.convert_local_to_pose(wanted[bone.name], bone.bone.matrix_local,
                                                         invert=True, **kwargs)
                loc, rot, scale = basis.decompose()
                if bone.rotation_mode == "QUATERNION":
                    if bone.name in previous and rot.dot(previous[bone.name]) < 0:
                        rot.negate()
                    values = rot
                    prop = "rotation_quaternion"
                else:
                    values = rot.to_euler(bone.rotation_mode, previous[bone.name]) if bone.name in previous else rot.to_euler(bone.rotation_mode)
                    prop = "rotation_euler"
                previous[bone.name] = values.copy()
                for path, data in (("location", loc), (prop, values), ("scale", scale)):
                    for index, value in enumerate(data):
                        tracks[(bone.name, path, index)].extend((frame, value))
        for (name, prop, index), values in tracks.items():
            fc = bag.fcurves.new(target.pose.bones[name].path_from_id(prop), index=index)
            fc.keyframe_points.add(len(frames))
            fc.keyframe_points.foreach_set("co", values)
            for key in fc.keyframe_points:
                key.interpolation = "LINEAR"
            fc.update()
        action["mw_target"] = target.name
        action["mw_source"] = source_ad.action.name
        settings.last_action = action
        return action, slot, len(frames)
    except Exception:
        bpy.data.actions.remove(action)
        raise
    finally:
        source_ad.use_nla = old_nla
        source_ad.action_influence, source_ad.action_blend_type = old_influence, old_blend
        for pb in source.pose.bones:
            pb.matrix_basis = old_pose[pb.name]
        scene.frame_set(old_frame, subframe=old_subframe)
        source.hide_set(old_hidden)
        context.view_layer.update()


def check_nla_target(target):
    ad = target.animation_data
    if ad and ad.action:
        raise WorkflowError("Push Target Action to NLA first, or use Bake Only.")
    if ad and (ad.use_tweak_mode or any(t.is_solo for t in ad.nla_tracks)):
        raise WorkflowError("Exit Tweak Mode and turn off Solo on target NLA tracks first.")
    if ad and not ad.use_nla:
        raise WorkflowError("Enable NLA evaluation on the target first.")


def add_to_nla(context, settings, action, slot):
    target = settings.target
    check_nla_target(target)
    ad = target.animation_data_create()
    start = float(context.scene.frame_current)
    if settings.placement == "APPEND":
        ends = [s.frame_end for t in ad.nla_tracks if not t.mute for s in t.strips if not s.mute]
        if ends:
            start = max(ends) - min(settings.blend_frames, float(action.frame_range[1] - action.frame_range[0]))
    track = ad.nla_tracks.new()
    track.name = "Marionette - " + action.name
    try:
        strip = track.strips.new(action.name, int(math.floor(start)), action)
        strip.action_slot = slot
        strip.frame_start = start
        strip.blend_type = "REPLACE"
        strip.extrapolation = "NOTHING"
        strip.use_auto_blend = False
        strip.blend_in = min(float(settings.blend_frames), strip.frame_end - strip.frame_start)
        show_capture(context, settings, False)
        select_only(context, [target], target)
        return strip
    except Exception:
        ad.nla_tracks.remove(track)
        raise


def push_target_action(context, settings):
    require_disconnected(context.scene)
    target = settings.target
    validate_rig(target, settings.rig_profile)
    ad = target.animation_data
    if not ad or not ad.action or not ad.action_slot:
        raise WorkflowError("Target Rig has no active Action to push down.")
    action, slot = ad.action, ad.action_slot
    blend, influence = ad.action_blend_type, ad.action_influence
    track = ad.nla_tracks.new()
    track.name = action.name
    try:
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        strip.action_slot = slot
        strip.frame_start = action.frame_range[0]
        strip.blend_type, strip.influence = blend, influence
        strip.extrapolation = ad.action_extrapolation
        ad.action = None
        return strip
    except Exception:
        ad.nla_tracks.remove(track)
        raise
