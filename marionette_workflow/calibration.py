"""Character-specific reference poses; bone names alone never define calibration."""
import json
import math

from mathutils import Matrix, Quaternion, Vector

EULER_ORDERS = {"XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"}
REFERENCE_KEY = "mw_reference_pose"


def profile_label(profile):
    return "Tripo (Mixamo Skeleton)" if profile == "TRIPO" else "Mixamo"


def reference_entries(rig, use_rest=False):
    entries = []
    for pb in rig.pose.bones:
        matrix = pb.bone.matrix_local if use_rest else pb.matrix
        pos, rot, _ = (rig.matrix_world @ matrix).decompose()
        local_pos, local_rot, local_scale = (Matrix.Identity(4) if use_rest else pb.matrix_basis).decompose()
        entries.append({
            "bone_name": pb.name, "local_position": list(local_pos), "local_rotation": list(local_rot),
            "local_scale": list(local_scale), "world_position": list(pos), "world_rotation": list(rot),
            "rotation_mode": pb.rotation_mode,
        })
    return entries


def store_reference(rig):
    rig[REFERENCE_KEY] = json.dumps(reference_entries(rig))


def stored_reference(rig):
    # Backward compatibility for a capture copy made with 1.0.0.
    raw = rig.get(REFERENCE_KEY)
    entries = json.loads(raw) if raw else reference_entries(rig, use_rest=True)
    if {e["bone_name"] for e in entries} != set(rig.pose.bones.keys()):
        raise ValueError("The saved reference no longer matches this skeleton. Prepare a new capture copy.")
    if any(e["rotation_mode"] not in EULER_ORDERS for e in entries):
        raise ValueError("The saved reference must use Euler rotation modes. Prepare a new capture copy.")
    return entries


def restore_reference(rig):
    for entry in stored_reference(rig):
        pb = rig.pose.bones[entry["bone_name"]]
        pb.rotation_mode = entry["rotation_mode"]
        pb.matrix_basis = Matrix.LocRotScale(Vector(entry["local_position"]), Quaternion(entry["local_rotation"]),
                                            Vector(entry.get("local_scale", (1, 1, 1))))


def pose_problems(entries, rows):
    world = {e["bone_name"]: Vector(e["world_position"]) for e in entries}
    points = {human: world[name] for human, name, *_ in rows if name and name in world}
    problems = []
    def angle(a, b):
        return math.degrees(a.angle(b)) if a.length > 1e-8 else 180.0
    if angle(points["Head"] - points["Hips"], Vector((0, 0, 1))) > 30:
        problems.append("body is not upright")
    for side in ("Left", "Right"):
        arm = points[side + "LowerArm"] - points[side + "UpperArm"]
        forearm = points[side + "Hand"] - points[side + "LowerArm"]
        if abs(90 - angle(arm, Vector((0, 0, 1)))) > 30 or angle(arm, forearm) > 30:
            problems.append(side.lower() + " arm is not in a T-pose")
        thigh = points[side + "LowerLeg"] - points[side + "UpperLeg"]
        shin = points[side + "Foot"] - points[side + "LowerLeg"]
        if angle(thigh, Vector((0, 0, -1))) > 30 or angle(thigh, shin) > 30:
            problems.append(side.lower() + " leg is not straight and upright")
    return problems


def straighten_arms(context, rig, rows):
    """Swing arms into a horizontal T-pose; preserve roll rather than borrowing another rig's axes."""
    names = {human: bone for human, bone, *_ in rows if bone}
    inv_world = rig.matrix_world.inverted()
    hips = rig.matrix_world @ rig.pose.bones[names["Hips"]].head
    for side in ("Left", "Right"):
        upper = rig.matrix_world @ rig.pose.bones[names[side + "UpperArm"]].head
        sign = 1 if upper.x >= hips.x else -1
        direction = Vector((sign, 0, 0))
        for first, second in (("UpperArm", "LowerArm"), ("LowerArm", "Hand")):
            pb = rig.pose.bones[names[side + first]]
            child = rig.pose.bones[names[side + second]]
            world = rig.matrix_world @ pb.matrix
            start = world.translation.copy()
            end = rig.matrix_world @ child.head
            delta = end - start
            if delta.length < 1e-7:
                raise ValueError("Cannot calibrate a zero-length arm segment.")
            correction = delta.normalized().rotation_difference(direction).to_matrix().to_4x4()
            rotated = correction @ world
            rotated.translation = start
            pb.matrix = inv_world @ rotated
            context.view_layer.update()


def reference_matches_scene(rig, tolerance=1e-5):
    """Detect a moved rig before exporting a calibration made in another world frame."""
    saved = rig.get("mw_capture_world")
    if not saved:
        return True
    matrix = Matrix(json.loads(saved))
    return max(abs(a-b) for ar, br in zip(matrix, rig.matrix_world) for a, b in zip(ar, br)) < tolerance
