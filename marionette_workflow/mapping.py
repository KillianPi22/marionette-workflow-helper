"""FK naming maps. Tripo's Mixamo export shares names, not the character's reference pose."""
import re

BODY = {
    "Hips": "Hips", "Spine": "Spine", "Chest": "Spine1",
    "UpperChest": "Spine2", "Neck": "Neck", "Head": "Head",
}
for side in ("Left", "Right"):
    for human, mixamo in (("UpperLeg", "UpLeg"), ("LowerLeg", "Leg"),
                          ("Foot", "Foot"), ("Toes", "ToeBase"),
                          ("Shoulder", "Shoulder"), ("UpperArm", "Arm"),
                          ("LowerArm", "ForeArm"), ("Hand", "Hand")):
        BODY[side + human] = side + mixamo
FINGERS = {}
for side in ("Left", "Right"):
    for human, mixamo in (("Thumb", "Thumb"), ("Index", "Index"),
                          ("Middle", "Middle"), ("Ring", "Ring"), ("Little", "Pinky")):
        for number, segment in enumerate(("Proximal", "Intermediate", "Distal"), 1):
            FINGERS[side + human + segment] = f"{side}Hand{mixamo}{number}"
OPTIONAL = {"LeftEye": "LeftEye", "RightEye": "RightEye"}
GOALS = ("LeftArmBendGoal", "RightArmBendGoal", "LeftLegBendGoal", "RightLegBendGoal")
REQUIRED = {"Hips", "Spine", "Head"} | {
    side + part for side in ("Left", "Right")
    for part in ("UpperLeg", "LowerLeg", "Foot", "UpperArm", "LowerArm", "Hand")}


def normalize(name):
    """Handle namespaces, mixamorig1, and separators without guessing arbitrary rigs."""
    name = name.rsplit(":", 1)[-1]
    name = re.sub(r"^mixamorig\d*[_:. -]*", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", name.casefold())


def build_map(names, fingers=True, positions="HIPS", profile="MIXAMO"):
    if profile not in {"MIXAMO", "TRIPO"}:
        raise ValueError("Choose the Mixamo or Tripo (Mixamo Skeleton) profile.")
    index = {}
    for name in names:
        index.setdefault(normalize(name), []).append(name)
    wanted = {**BODY, **FINGERS, **OPTIONAL}
    rows, missing, ambiguous = [], [], []
    for human, conventional in wanted.items():
        candidates = index.get(normalize(conventional), [])
        if human in FINGERS and not fingers:
            candidates = []
        if len(candidates) > 1:
            ambiguous.append(human)
        bone = candidates[0] if len(candidates) == 1 else ""
        if human in REQUIRED and not bone:
            missing.append(human)
        rows.append([human, bone, bool(bone), bool(bone) and (positions == "ALL" or human == "Hips")])
    # A Mixamo deformation skeleton has no IK pole controls. Never use toe/end bones as poles.
    rows.extend([[name, "", False, False] for name in GOALS])
    return rows, missing, ambiguous


def generic_file(prefix="mixamorig:", positions="HIPS"):
    names = [prefix + name for name in (*BODY.values(), *FINGERS.values())]
    rows, _, _ = build_map(names, positions=positions)
    variant = "Mixamorig" if prefix else "No Prefix"
    return {"version": 3, "program": "blender", "presets": {
        f"Mixamo Full FK - {variant} - {positions.title()} Position": {
            "enable_ik": [False] * 4, "bone_map": rows, "tpose": []}}}
