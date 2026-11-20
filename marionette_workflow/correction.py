"""Manual post-capture pose adjustments. This is NOT optical lens undistortion."""
import json
import math

import bpy
from mathutils import Matrix, Quaternion, Vector
from . import workflow

Error = workflow.WorkflowError


def basis(settings):
    up = Vector((0, 0, 1))
    if settings.adjust_axis == "CAMERA":
        camera = settings.adjust_camera
        if not camera or camera.type != "CAMERA":
            raise Error("Choose a Blender camera aligned with the recording view, or choose World X/Y.")
        direction = camera.matrix_world.to_quaternion() @ Vector((0, 0, -1))
        direction.z = 0
        if direction.length < 1e-5:
            raise Error("The camera looks vertically down/up. Choose a horizontal depth axis instead.")
        if camera.animation_data and (camera.animation_data.action or camera.animation_data.nla_tracks or camera.animation_data.drivers):
            raise Error("Use a static reference camera for these adjustments.")
        if camera.parent or camera.constraints:
            raise Error("Use an unparented reference camera without constraints.")
        direction.normalize()
    else:
        direction = Vector((1, 0, 0) if settings.adjust_axis == "X" else (0, 1, 0))
    return direction, direction.cross(up).normalized()


def range_weight(frame, start, end, feather):
    if frame < start or frame > end:
        return 0.0
    feather = min(float(feather), (end-start)/2)
    if feather <= 0:
        return 1.0
    t = max(0.0, min(1.0, (frame-start)/feather, (end-frame)/feather))
    return t*t*(3-2*t)


def solve_two_bone(start, middle, end, target, fallback=None):
    """Fixed-length two-bone IK with the source bend plane and a stable singularity fallback."""
    first_length = (middle-start).length
    second_length = (end-middle).length
    span = first_length+second_length
    if min(first_length, second_length) < 1e-8:
        raise Error("A limb has a zero-length segment; it cannot be corrected safely.")
    delta = target-start
    distance = delta.length
    if distance < span*1e-8:
        direction = (end-start).normalized() if (end-start).length > 1e-8 else Vector((0, 0, 1))
    else:
        direction = delta/distance
    eps = span*1e-7
    clamped = min(span-eps, max(abs(first_length-second_length)+eps, distance))
    pole = middle-start
    pole -= direction*pole.dot(direction)
    if pole.length < span*1e-4:
        pole = fallback.copy() if fallback is not None else Vector((0, -1, 0))
        pole -= direction*pole.dot(direction)
    if pole.length < span*1e-4:
        axis = min((Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))), key=lambda v: abs(v.dot(direction)))
        pole = axis-direction*axis.dot(direction)
    pole.normalize()
    along = (first_length**2-second_length**2+clamped**2)/(2*clamped)
    height = math.sqrt(max(0, first_length**2-along**2))
    solved_middle = start+direction*along+pole*height
    solved_end = start+direction*clamped
    return solved_middle, solved_end, pole, (solved_end-target).length


def subtree_names(rig, name):
    bone = rig.pose.bones[name]
    return {bone.name, *(p.name for p in bone.children_recursive)}


def rotate_subtree(world, names, pivot, rotation):
    change = Matrix.Translation(pivot) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for name in names:
        world[name] = change @ world[name]


def apply_chain(world, chain, sets, target, fallback):
    upper, middle, end = chain
    old = {n: world[n].copy() for n in sets[upper]}
    a, b, c = (old[n].translation.copy() for n in chain)
    m, e, pole, error = solve_two_bone(a,b,c,target,fallback)
    q1 = (b-a).normalized().rotation_difference((m-a).normalized())
    q2 = (c-b).normalized().rotation_difference((e-m).normalized())
    new_upper = q1.to_matrix().to_4x4() @ old[upper]
    new_middle = q2.to_matrix().to_4x4() @ old[middle]
    new_end = old[end].copy()  # Keep wrist/ankle world orientation, including its descendants.
    new_upper.translation, new_middle.translation, new_end.translation = a, m, e
    changes = {upper: new_upper @ old[upper].inverted(),
               middle: new_middle @ old[middle].inverted(), end: new_end @ old[end].inverted()}
    for name in sets[upper]:
        owner = end if name in sets[end] else middle if name in sets[middle] else upper
        world[name] = changes[owner] @ old[name]
    return pole, error


def active_rig(context, settings):
    rig = settings.adjust_rig
    if rig is None:
        obj = context.object
        rig = obj if obj and obj.type == "ARMATURE" else obj.find_armature() if obj else None
    if rig is None:
        rig = settings.capture
    return rig


def validate(context, rig):
    workflow.require_disconnected(context.scene)
    rows = workflow.validate_rig(rig, rig.get("mw_profile", "MIXAMO") if rig else "MIXAMO")
    if rig.name not in context.view_layer.objects:
        raise Error("The correction rig must be in the current view layer.")
    if rig.data.pose_position != "POSE":
        raise Error("Use Pose Position on the correction rig.")
    if any(p.rotation_mode == "AXIS_ANGLE" for p in rig.pose.bones):
        raise Error("Use Euler or Quaternion bone rotations, not Axis Angle.")
    ad = rig.animation_data
    if not ad or not ad.action or not ad.action_slot:
        raise Error("Select the capture copy after Copy to DCC; an active Action is required.")
    if ad.use_nla and any(not t.mute and any(not s.mute for s in t.strips) for t in ad.nla_tracks):
        raise Error("Adjust the active capture Action before adding it to NLA, or disable its NLA evaluation first.")
    if ad.action_blend_type != "REPLACE" or abs(ad.action_influence-1) > 1e-6:
        raise Error("Set the active Action to Replace with influence 1 before adjusting it.")
    if any(not fc.data_path.endswith((".location", ".rotation_euler", ".rotation_quaternion", ".scale"))
           for fc in workflow.curves(ad.action,ad.action_slot)):
        raise Error("Adjust a bone-transform Action only; custom properties and rotation-mode animation are not supported.")
    return {human:name for human,name,*_ in rows if name}


def set_source(context, settings):
    rig = active_rig(context, settings)
    validate(context, rig)
    ad = rig.animation_data
    if ad.action == settings.adjust_result and rig == settings.adjust_owner:
        raise Error("Show Original first, or select a new take. An adjusted result cannot become its own source.")
    curves = workflow.curves(ad.action, ad.action_slot)
    if not any(fc.keyframe_points or fc.sampled_points for fc in curves):
        raise Error("The active Action slot has no keys.")
    settings.adjust_rig = rig
    settings.adjust_owner = rig
    settings.adjust_source = ad.action
    settings.adjust_source_slot = ad.action_slot.handle
    baseline = {}
    for pb in rig.pose.bones:
        matrix = pb.matrix_basis.copy()
        baseline[pb.name] = {"matrix":[list(r) for r in matrix],"mode":pb.rotation_mode}
    settings.adjust_baseline = json.dumps(baseline)
    settings.adjust_result = None
    settings.adjust_signature = workflow.rest_signature(rig)
    settings.adjust_status = "Source saved. Choose adjustments, then build a corrected copy."
    ad.action.use_fake_user = True


def restore_baseline(rig, settings):
    # A source may leave fingers, scales or individual rotation channels unkeyed.
    # Reset these before evaluating it, including when returning from a fully keyed result.
    baseline = json.loads(settings.adjust_baseline)
    for pb in rig.pose.bones:
        pb.rotation_mode = baseline[pb.name]["mode"]
        pb.matrix_basis = Matrix(baseline[pb.name]["matrix"])


def resolve_source(context, settings):
    rig = active_rig(context, settings)
    names = validate(context, rig)
    if rig != settings.adjust_owner or not settings.adjust_source:
        raise Error("Click Use Active Take first.")
    if rig.animation_data.action not in {settings.adjust_source, settings.adjust_result}:
        raise Error("A different take is active. Click Use Active Take to start a new adjustment.")
    if workflow.rest_signature(rig) != settings.adjust_signature:
        raise Error("The rig's rest skeleton changed. Click Use Active Take to start a new adjustment.")
    source = settings.adjust_source
    slot = next((s for s in source.slots if s.handle == settings.adjust_source_slot), None)
    if slot is None:
        raise Error("The source Action slot no longer exists. Select the source again.")
    return rig, names, source, slot


def compare(context, settings, corrected):
    rig, _, source, slot = resolve_source(context, settings)
    if corrected:
        if not settings.adjust_result:
            raise Error("Build a corrected copy first.")
        action = settings.adjust_result
        slot = action.slots[0]
    else:
        action = source
    rig.animation_data.action = action
    rig.animation_data.action_slot = slot
    restore_baseline(rig, settings)
    context.scene.frame_set(context.scene.frame_current, subframe=context.scene.frame_subframe)
    context.view_layer.update()


def build(context, settings, preview=False):
    rig, names, source, source_slot = resolve_source(context, settings)
    depth, right = basis(settings)
    source_curves = workflow.curves(source, source_slot)
    times = [p.co.x for fc in source_curves for p in (*fc.keyframe_points,*fc.sampled_points)]
    if not times:
        raise Error("The source Action slot has no keys.")
    frames = workflow.sample_frames(min(times),max(times))
    if settings.adjust_scene_range:
        start = max(frames[0], float(context.scene.frame_start))
        end = min(frames[-1], float(context.scene.frame_end))
        if end <= start:
            raise Error("The scene range must overlap at least two source frames.")
        feather = settings.adjust_feather
    else:
        start, end, feather = frames[0], frames[-1], 0
    if not preview and max(abs(settings.body_pitch),abs(settings.body_roll),abs(settings.pelvis_motion-1),abs(settings.left_step_height-1),abs(settings.right_step_height-1),abs(settings.pelvis_height), abs(settings.foot_depth-1), abs(settings.foot_width-1), settings.floor_strength, abs(settings.left_lift), abs(settings.right_lift), abs(settings.adjust_pitch),abs(settings.adjust_roll),abs(settings.adjust_hand_depth-1),abs(settings.adjust_root_depth-1)) < 1e-8:
        raise Error("Change at least one adjustment. Neutral values already match the original.")
    if preview:
        frames = [context.scene.frame_current + context.scene.frame_subframe]
    chains = {}
    for side in ("Left", "Right"):
        for label, parts in (("Arm",("UpperArm","LowerArm","Hand")), ("Leg",("UpperLeg","LowerLeg","Foot"))):
            chain = tuple(names[side+part] for part in parts)
            if rig.pose.bones[chain[1]].parent != rig.pose.bones[chain[0]] or rig.pose.bones[chain[2]].parent != rig.pose.bones[chain[1]]:
                raise Error("This adjustment requires direct upper/lower/hand or upper/lower/foot chains.")
            chains[side+label] = chain
    all_chain_names = {n for chain in chains.values() for n in chain}
    sets = {n:subtree_names(rig,n) for n in all_chain_names}
    hip_set = subtree_names(rig,names["Hips"])
    torso_set = subtree_names(rig,names["Spine"])
    anchor_name = names.get("UpperChest",names.get("Chest",names["Spine"]))
    ad, scene = rig.animation_data, context.scene
    old_action, old_slot = ad.action, ad.action_slot
    old_frame, old_subframe = scene.frame_current, scene.frame_subframe
    old_hidden, old_nla = rig.hide_get(), ad.use_nla
    old_pose = {p.name:(p.rotation_mode,p.matrix_basis.copy()) for p in rig.pose.bones}
    action = None
    success = False
    previous, poles, buffers = {}, {}, {}
    reach_events, reach_frames, max_reach_error = 0, set(), 0.0
    try:
        rig.hide_set(False)
        ad.action, ad.action_slot, ad.use_nla = source, source_slot, False
        restore_baseline(rig, settings)
        context.view_layer.update()
        scene.frame_set(math.floor(min(times)),subframe=min(times)-math.floor(min(times)))
        evaluated = rig.evaluated_get(context.evaluated_depsgraph_get())
        root_anchor = (evaluated.matrix_world @ evaluated.pose.bones[names["Hips"]].matrix).translation.copy()
        inverse = rig.matrix_world.inverted()
        for frame in frames:
            scene.frame_set(math.floor(frame),subframe=frame-math.floor(frame))
            context.view_layer.update()
            evaluated = rig.evaluated_get(context.evaluated_depsgraph_get())
            world = {p.name:evaluated.matrix_world @ p.matrix for p in evaluated.pose.bones}
            if abs(settings.body_pitch)+abs(settings.body_roll)>1e-9:
                weight=range_weight(frame,start,end,feather)*settings.adjust_strength
                rotation=Quaternion(depth,settings.body_roll*weight) @ Quaternion(right,settings.body_pitch*weight)
                rotate_subtree(world,set(world),world[names["Hips"]].translation.copy(),rotation)
            original_hip = world[names["Hips"]].translation.copy()
            original_feet = {side:world[names[side+"Foot"]].translation.copy() for side in ("Left","Right")}
            weight = range_weight(frame,start,end,feather)*settings.adjust_strength
            if weight > 0:
                shift = depth*((world[names["Hips"]].translation-root_anchor).dot(depth)*(settings.adjust_root_depth-1)*weight)
                shift.z += (settings.pelvis_height+(original_hip.z-root_anchor.z)*(settings.pelvis_motion-1))*weight
                if shift.length > 1e-9:
                    for name in hip_set:
                        world[name].translation += shift
                if abs(settings.adjust_pitch)+abs(settings.adjust_roll) > 1e-9:
                    rotation = Quaternion(depth,settings.adjust_roll*weight) @ Quaternion(right,settings.adjust_pitch*weight)
                    rotate_subtree(world,torso_set,world[names["Spine"]].translation.copy(),rotation)
                if abs(settings.adjust_hand_depth-1) > 1e-9:
                    anchor = world[anchor_name].translation.copy()
                    for side in ("Left","Right"):
                        if settings.adjust_hands not in {"BOTH",side.upper()}:
                            continue
                        label = side+"Arm"
                        wrist = world[names[side+"Hand"]].translation.copy()
                        target = wrist+depth*((wrist-anchor).dot(depth)*(settings.adjust_hand_depth-1)*weight)
                        poles[label], error = apply_chain(world,chains[label],sets,target,None)
                        if error > 1e-5:
                            reach_events += 1
                            reach_frames.add(frame)
                            max_reach_error = max(max_reach_error,error)
                for side in ("Left","Right"):
                    label = side+"Leg"
                    foot = names[side+"Foot"]
                    target = original_feet[side].copy() if settings.adjust_keep_feet else world[foot].translation.copy()
                    relative = original_feet[side]-original_hip
                    target += depth*relative.dot(depth)*(settings.foot_depth-1)*weight
                    target += right*relative.dot(right)*(settings.foot_width-1)*weight
                    target.z += (settings.left_lift if side=="Left" else settings.right_lift)*weight
                    normal = Vector((-math.tan(settings.floor_slope_x),-math.tan(settings.floor_slope_y),1)).normalized()
                    clearance = settings.left_clearance if side=="Left" else settings.right_clearance
                    influence = settings.floor_left if side=="Left" else settings.floor_right
                    distance = (target-Vector((0,0,settings.floor_height))).dot(normal)-clearance
                    gain=settings.left_step_height if side=="Left" else settings.right_step_height
                    # Scale positive swing height; do not amplify penetration below the plane.
                    target += normal*max(0,distance)*(gain-1)*weight
                    distance=(target-Vector((0,0,settings.floor_height))).dot(normal)-clearance
                    contact=1.0
                    if settings.ground_mode=="CONTACT":
                        t=max(0.0,min(1.0,distance/max(settings.contact_range,1e-5)))
                        contact=1-t*t*(3-2*t)
                    target -= normal*distance*settings.floor_strength*influence*weight*contact
                    if (target-world[foot].translation).length > 1e-9:
                        _, error = apply_chain(world,chains[label],sets,target,None)
                        if error > 1e-5:
                            reach_events += 1
                            reach_frames.add(frame)
                            max_reach_error = max(max_reach_error,error)
            wanted = {name:inverse @ matrix for name,matrix in world.items()}
            for pb in rig.pose.bones:
                kwargs = {"parent_matrix":wanted[pb.parent.name],"parent_matrix_local":pb.parent.bone.matrix_local} if pb.parent else {}
                local = pb.bone.convert_local_to_pose(wanted[pb.name],pb.bone.matrix_local,invert=True,**kwargs)
                loc,rot,scale = local.decompose()
                if pb.rotation_mode == "QUATERNION":
                    if pb.name in previous and rot.dot(previous[pb.name]) < 0:
                        rot.negate()
                    values,prop = rot,"rotation_quaternion"
                else:
                    values = rot.to_euler(pb.rotation_mode,previous[pb.name]) if pb.name in previous else rot.to_euler(pb.rotation_mode)
                    prop = "rotation_euler"
                previous[pb.name] = values.copy()
                for path,data in (("location",loc),(prop,values),("scale",scale)):
                    for index,value in enumerate(data):
                        buffers.setdefault((pb.name,path,index),[]).extend((frame,value))
        action = bpy.data.actions.new(source.name+"_Adjusted")
        action.use_fake_user = not preview
        slot = action.slots.new(id_type="OBJECT",name=rig.name)
        bag = action.layers.new("Post-Capture Adjustments").strips.new(type="KEYFRAME").channelbags.new(slot)
        for (name,path,index),values in buffers.items():
            fc = bag.fcurves.new(rig.pose.bones[name].path_from_id(path),index=index)
            fc.keyframe_points.add(len(frames))
            fc.keyframe_points.foreach_set("co",values)
            for key in fc.keyframe_points:
                key.interpolation = "LINEAR"
            fc.update()
        action["mw_adjustment_source"] = source.name
        action["mw_adjustment_settings"] = json.dumps({
            "depth_axis":settings.adjust_axis,"root_depth":settings.adjust_root_depth,
            "hand_depth":settings.adjust_hand_depth,"pitch":settings.adjust_pitch,"roll":settings.adjust_roll,
            "strength":settings.adjust_strength,"keep_feet":settings.adjust_keep_feet,
            "lower_body":{k:getattr(settings,k) for k in LOWER_SETTINGS},"range":[start,end],"feather":feather,"reach_limited_frames":len(reach_frames)})
        ad.action,ad.action_slot = action,slot
        settings.adjust_result = action
        settings.adjust_status = f"{len(frames)} samples; {len(reach_frames)} frames with reach limits."
        success = True
        return {"samples":len(frames),"reach_events":reach_events,"reach_frames":len(reach_frames),"max_reach_error":max_reach_error}
    except Exception:
        ad.action,ad.action_slot = old_action,old_slot
        if action:
            bpy.data.actions.remove(action)
        raise
    finally:
        if not success:
            ad.action,ad.action_slot = old_action,old_slot
        ad.use_nla = old_nla
        for pb in rig.pose.bones:
            pb.rotation_mode,pb.matrix_basis = old_pose[pb.name]
        scene.frame_set(old_frame,subframe=old_subframe)
        rig.hide_set(old_hidden)
        context.view_layer.update()


LOWER_SETTINGS = ("body_pitch", "body_roll", "pelvis_motion", "left_step_height", "right_step_height", "ground_mode", "contact_range", "pelvis_height", "foot_depth", "foot_width", "left_lift", "right_lift", "floor_strength", "floor_height", "floor_slope_x", "floor_slope_y", "left_clearance", "right_clearance", "floor_left", "floor_right")
