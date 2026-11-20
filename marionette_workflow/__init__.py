"""Marionette Workflow Helper: an independent companion to Marionette for Blender."""
bl_info = {
    "name": "Marionette Workflow Helper", "author": "Killian Pichon",
    "version": (1, 4, 0), "blender": (5, 2, 0), "category": "Animation",
    "location": "View 3D > Sidebar > Mocap Workflow",
    "description": "Calibrate Mixamo and Tripo capture copies and transfer takes to NLA",
}

import importlib
import json
from pathlib import Path
import bpy
from bpy.props import PointerProperty, BoolProperty, StringProperty, EnumProperty, IntProperty, CollectionProperty, FloatProperty
from bpy_extras.io_utils import ExportHelper
if "workflow" in locals():
    importlib.reload(mapping)
    importlib.reload(calibration)
    importlib.reload(workflow)
    importlib.reload(correction)
    if "preview" in locals():
        importlib.reload(preview)
    else:
        from . import preview
else:
    from . import mapping, calibration, workflow, correction, preview


def armature_poll(self, obj):
    return obj.type == "ARMATURE"


def camera_poll(self, obj):
    return obj.type == "CAMERA"


def profile_changed(self, context):
    if self.rig_profile == "TRIPO":
        self.position_mode = "ALL"


class MW_Visibility(bpy.types.PropertyGroup):
    obj: PointerProperty(type=bpy.types.Object)
    was_hidden: BoolProperty()


class MW_Settings(bpy.types.PropertyGroup):
    target: PointerProperty(name="Target Rig", type=bpy.types.Object, poll=armature_poll,
                           description="Original character that will receive the baked Action")
    rig_profile: EnumProperty(name="Rig Profile", items=[
        ("MIXAMO", "Mixamo", "Standard Mixamo humanoid; use its own rest-pose calibration"),
        ("TRIPO", "Tripo (Mixamo Skeleton)", "Tripo humanoid exported with Mixamo names; calibrate for this character")],
        default="MIXAMO", update=profile_changed)
    straighten_arms: BoolProperty(name="Straighten Arms for T-Pose", default=True,
                                 description="On the Tripo capture copy only, align upper and lower arms horizontally while retaining their bone roll")
    capture: PointerProperty(name="Capture Copy", type=bpy.types.Object, poll=armature_poll)
    prepared_target: PointerProperty(type=bpy.types.Object)
    capture_collection: PointerProperty(type=bpy.types.Collection)
    last_action: PointerProperty(type=bpy.types.Action)
    visibility: CollectionProperty(type=MW_Visibility)
    capture_visible: BoolProperty(default=True)
    copy_meshes: BoolProperty(name="Include Preview Meshes", default=True,
                             description="Duplicate bound meshes for a visible capture character")
    include_fingers: BoolProperty(name="Map All Finger Joints", default=True,
                                 description="Map 30 supported finger joints when present; does not create finger motion")
    position_mode: EnumProperty(name="Position Channels", items=[
        ("HIPS", "Hips Only (FK)", "Translate only hips; verify limb Position flags after importing into the official plugin"),
        ("ALL", "All Mapped Bones", "Copy translation on all mapped bones; matches the official plugin's import defaults")], default="HIPS")
    clip_name: StringProperty(name="Take Name", default="Marionette Take")
    placement: EnumProperty(name="Place Clip", items=[
        ("APPEND", "After Existing Clips", "Append after the last unmuted clip, overlapping by Blend In frames"),
        ("CURSOR", "At Current Frame", "Start at the current scene frame")], default="APPEND")
    blend_frames: IntProperty(name="Blend In (frames)", default=10, min=0, max=10000)
    status: StringProperty(default="Choose the original character and its rig profile to begin.")
    workspace_mode: EnumProperty(name="Workflow",items=[("CLEANUP","Motion Cleanup","Adjust an existing copied take"),("CAPTURE","Capture / NLA","Prepare character, connect Marionette and transfer takes")],default="CLEANUP")
    ui_body: BoolProperty(name="Body Alignment",default=True)
    ui_gait: BoolProperty(name="Gait",default=True)
    ui_ground: BoolProperty(name="Ground Contact",default=False)
    ui_range: BoolProperty(name="Range / Strength",default=False)
    ui_torso: BoolProperty(name="Local Torso Offsets",default=False)
    ui_hands: BoolProperty(name="Hand Reach",default=False)
    ui_foot_offsets: BoolProperty(name="Individual Foot Offsets",default=False)
    show_adjustments: BoolProperty(name="Post-Capture Adjustments (Optional)", default=False)
    adjust_rig: PointerProperty(name="Correction Rig", type=bpy.types.Object, poll=armature_poll)
    adjust_owner: PointerProperty(type=bpy.types.Object)
    adjust_source: PointerProperty(type=bpy.types.Action)
    adjust_result: PointerProperty(type=bpy.types.Action)
    adjust_source_slot: IntProperty()
    adjust_signature: StringProperty()
    adjust_baseline: StringProperty()
    adjust_axis: EnumProperty(name="Depth Axis", items=[("Y","World Y","Use world Y for depth and world X for pitch"),
        ("X","World X","Use world X for depth"),("CAMERA","Reference Camera","Use the camera's horizontal viewing direction; no optical calibration is inferred")],default="Y")
    adjust_camera: PointerProperty(name="Reference Camera",type=bpy.types.Object,poll=camera_poll)
    adjust_root_depth: FloatProperty(name="Root Depth Gain",default=1,min=0,max=2,precision=3,
        description="Scale hips depth travel from the first frame; 1 leaves travel unchanged")
    adjust_hand_depth: FloatProperty(name="Hand Depth Gain",default=1,min=0,max=2,precision=3,
        description="Adjust wrist depth relative to the chest using fixed-length arm IK; 1 leaves reach unchanged")
    adjust_hands: EnumProperty(name="Hands",items=[("BOTH","Both","Adjust both hands"),("LEFT","Left","Adjust the left hand"),("RIGHT","Right","Adjust the right hand")],default="BOTH")
    adjust_pitch: FloatProperty(name="Torso Pitch",default=0,subtype="ANGLE",min=-0.785398,max=0.785398,
        description="Rotate the spine subtree around the view-right axis; legs and pelvis are not tilted")
    adjust_roll: FloatProperty(name="Torso Roll",default=0,subtype="ANGLE",min=-0.785398,max=0.785398,
        description="Rotate the spine subtree around the horizontal depth axis")
    adjust_strength: FloatProperty(name="Strength",default=1,min=0,max=1,subtype="FACTOR")
    adjust_keep_feet: BoolProperty(name="Keep Original Foot Positions",default=True,
        description="Use leg IK after root travel edits; unreachable positions are clamped and reported, not stretched")
    adjust_scene_range: BoolProperty(name="Limit to Scene Frame Range",default=False)
    adjust_feather: IntProperty(name="Blend Frames",default=8,min=0,max=10000)
    adjust_status: StringProperty(default="Select the capture copy after Copy to DCC, then Use Active Take.")

    body_pitch: FloatProperty(name="Whole Body Pitch",default=0,subtype="ANGLE",min=-.785398,max=.785398,
        description="Rotate the whole pose around the hips before local and ground adjustments; preserves existing joint angles")
    body_roll: FloatProperty(name="Whole Body Roll",default=0,subtype="ANGLE",min=-.785398,max=.785398)
    pelvis_motion: FloatProperty(name="Pelvis Vertical Motion Gain",default=1,min=0,max=2,
        description="Scale vertical hips travel relative to the first source frame; 1 is unchanged")
    left_step_height: FloatProperty(name="Left Step Height Gain",default=1,min=0,max=3,
        description="Scale positive ankle height above the ground plane and ankle clearance; 1 is unchanged")
    right_step_height: FloatProperty(name="Right Step Height Gain",default=1,min=0,max=3)
    ground_mode: EnumProperty(name="Ground Mode",items=[("CONTACT","Near Ground Only","Smoothly release ground correction as a foot rises"),("ALL","Always Project","Apply ground projection even to lifted feet")],default="CONTACT")
    contact_range: FloatProperty(name="Ground Release Height",default=.08,min=.001,subtype="DISTANCE",
        description="Ankle height above clearance where ground correction releases completely; not automatic contact detection")
    pelvis_height: FloatProperty(name="Pelvis Height",default=0,subtype="DISTANCE")
    foot_depth: FloatProperty(name="Foot Depth Gain",default=1,min=0,max=2)
    foot_width: FloatProperty(name="Stance Width Gain",default=1,min=0,max=2)
    left_lift: FloatProperty(name="Left Foot Height Offset",default=0,subtype="DISTANCE")
    right_lift: FloatProperty(name="Right Foot Height Offset",default=0,subtype="DISTANCE")
    floor_strength: FloatProperty(name="Ground Blend",default=0,min=0,max=1)
    floor_height: FloatProperty(name="Ground Height",default=0,subtype="DISTANCE")
    floor_slope_x: FloatProperty(name="Ground Slope X",default=0,subtype="ANGLE",min=-1.2,max=1.2)
    floor_slope_y: FloatProperty(name="Ground Slope Y",default=0,subtype="ANGLE",min=-1.2,max=1.2)
    left_clearance: FloatProperty(name="Left Ankle Clearance",default=.08,min=0,subtype="DISTANCE")
    right_clearance: FloatProperty(name="Right Ankle Clearance",default=.08,min=0,subtype="DISTANCE")
    floor_left: FloatProperty(name="Left Ground Influence",default=1,min=0,max=1)
    floor_right: FloatProperty(name="Right Ground Influence",default=1,min=0,max=1)


class MW_OT_reset_torso(bpy.types.Operator):
    bl_idname="mw.reset_torso"
    bl_label="Clear Torso Offsets"
    bl_options={"REGISTER","UNDO"}
    def execute(self,context):
        context.scene.mw_settings.adjust_pitch=0
        context.scene.mw_settings.adjust_roll=0
        return {"FINISHED"}


class MW_OT_reset_gait(bpy.types.Operator):
    bl_idname="mw.reset_gait"
    bl_label="Reset Gait Adjustments"
    bl_description="Reset lower-body gains and offsets; preserve torso settings and ground calibration"
    bl_options={"REGISTER","UNDO"}
    def execute(self,context):
        s=context.scene.mw_settings
        for key,value in {"body_pitch":0,"body_roll":0,"pelvis_motion":1,"pelvis_height":0,
                          "left_step_height":1,"right_step_height":1,"foot_depth":1,"foot_width":1,
                          "left_lift":0,"right_lift":0,"floor_strength":0,"floor_left":1,"floor_right":1,
                          "adjust_keep_feet":True,"ground_mode":"CONTACT"}.items():
            setattr(s,key,value)
        return {"FINISHED"}


class MW_OT_preview(bpy.types.Operator):
    bl_idname = "mw.preview"
    bl_label = "Live Preview"
    def execute(self,context):
        try:
            if preview.active():
                preview.stop()
            else:
                preview.start(context)
            return {"FINISHED"}
        except (workflow.WorkflowError, RuntimeError, ValueError) as exc:
            self.report({"ERROR"},str(exc))
            return {"CANCELLED"}


class MW_OT_adjust_source(bpy.types.Operator):
    bl_idname = "mw.adjust_source"
    bl_label = "Use Active Take"
    bl_description = "Remember the original active Action; every adjustment is rebuilt from this source"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self,context):
        try:
            preview.stop()
            correction.set_source(context,context.scene.mw_settings)
            self.report({"INFO"},"Original take saved for comparison.")
            return {"FINISHED"}
        except (workflow.WorkflowError,RuntimeError,ValueError) as exc:
            self.report({"ERROR"},str(exc))
            return {"CANCELLED"}


class MW_OT_adjust_build(bpy.types.Operator):
    bl_idname = "mw.adjust_build"
    bl_label = "Build Corrected Copy"
    bl_description = "Bake a new Action from the original take with manual pose adjustments; this is not lens undistortion"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self,context):
        try:
            preview.stop()
            report = correction.build(context,context.scene.mw_settings)
            if report["reach_frames"]:
                self.report({"WARNING"},f'Corrected copy created. {report["reach_frames"]} frame(s) reached a limb limit; reduce the adjustment to preserve all foot/hand targets.')
            else:
                self.report({"INFO"},"Corrected copy created. Original Action preserved.")
            return {"FINISHED"}
        except (workflow.WorkflowError,RuntimeError,ValueError,KeyError) as exc:
            self.report({"ERROR"},str(exc))
            return {"CANCELLED"}


class MW_OT_adjust_compare(bpy.types.Operator):
    bl_idname = "mw.adjust_compare"
    bl_label = "Compare Take"
    bl_options = {"REGISTER", "UNDO"}
    corrected: BoolProperty(default=False)
    def execute(self,context):
        try:
            preview.stop()
            correction.compare(context,context.scene.mw_settings,self.corrected)
            return {"FINISHED"}
        except (workflow.WorkflowError,RuntimeError,ValueError) as exc:
            self.report({"ERROR"},str(exc))
            return {"CANCELLED"}


def fold(layout, settings, prop):
    box=layout.box()
    box.prop(settings,prop,icon="TRIA_DOWN" if getattr(settings,prop) else "TRIA_RIGHT",emboss=False)
    return box if getattr(settings,prop) else None


def draw_adjustments(layout, settings, force=False):
    if not force:
        layout.prop(settings,"show_adjustments",icon="TRIA_DOWN" if settings.show_adjustments else "TRIA_RIGHT",emboss=False)
        if not settings.show_adjustments:
            return
    box=layout.box()
    box.prop(settings,"adjust_rig")
    box.operator("mw.adjust_source",text="Use Active Take",icon="ACTION")
    if not settings.adjust_source:
        box.label(text="Copy to DCC, disconnect, then choose a take.",icon="INFO")
        return
    row=box.row()
    row.enabled=False
    row.prop(settings,"adjust_source",text="Source")
    box.operator("mw.preview",text="Stop Preview / Restore" if preview.active() else "Start Live Preview",icon="PAUSE" if preview.active() else "PLAY",depress=preview.active())
    row=box.row(align=True)
    row.operator("mw.adjust_compare",text="Original").corrected=False
    sub=row.row(align=True)
    sub.enabled=settings.adjust_result is not None and not preview.active()
    sub.operator("mw.adjust_compare",text="Corrected").corrected=True
    box=fold(layout,settings,"ui_body")
    if box:
        box.use_property_split=True
        box.use_property_decorate=False
        box.prop(settings,"adjust_axis")
        if settings.adjust_axis=="CAMERA":box.prop(settings,"adjust_camera")
        box.prop(settings,"body_pitch")
        box.prop(settings,"body_roll")
        torso=fold(box,settings,"ui_torso")
        if torso:
            torso.prop(settings,"adjust_pitch")
            torso.prop(settings,"adjust_roll")
            torso.operator("mw.reset_torso",text="Clear Torso Offsets")
        elif abs(settings.adjust_pitch)+abs(settings.adjust_roll)>.0001:
            box.label(text="Local torso offsets are active.",icon="INFO")
    box=fold(layout,settings,"ui_gait")
    if box:
        box.use_property_split=True
        box.use_property_decorate=False
        for key in ("foot_depth","foot_width","left_step_height","right_step_height","pelvis_motion","pelvis_height","adjust_keep_feet"):
            box.prop(settings,key)
        if settings.foot_width<.05:box.label(text="Width near 0 collapses the stance.",icon="ERROR")
        offsets=fold(box,settings,"ui_foot_offsets")
        if offsets:
            offsets.prop(settings,"left_lift")
            offsets.prop(settings,"right_lift")
        elif abs(settings.left_lift)+abs(settings.right_lift)>.0001:
            box.label(text="Individual foot offsets are active.",icon="INFO")
        box.operator("mw.reset_gait",text="Reset Gait / Body Values",icon="LOOP_BACK")
    box=fold(layout,settings,"ui_ground")
    if box:
        box.use_property_split=True
        box.use_property_decorate=False
        box.prop(settings,"floor_strength",slider=True)
        if settings.floor_strength>0:
            box.prop(settings,"ground_mode")
            if settings.ground_mode=="CONTACT":box.prop(settings,"contact_range")
            else:box.label(text="Also projects lifted feet.",icon="INFO")
            for key in ("floor_height","floor_slope_x","floor_slope_y","left_clearance","right_clearance","floor_left","floor_right"):
                box.prop(settings,key)
            box.label(text="Targets ankles, not mesh soles.")
    elif settings.floor_strength>0:
        layout.label(text="Ground correction is active.",icon="INFO")
    box=fold(layout,settings,"ui_hands")
    if box:
        box.prop(settings,"adjust_hand_depth")
        box.prop(settings,"adjust_hands",expand=True)
    elif abs(settings.adjust_hand_depth-1)>.0001:
        layout.label(text="Hand reach adjustment is active.",icon="INFO")
    box=fold(layout,settings,"ui_range")
    if box:
        box.prop(settings,"adjust_strength",slider=True)
        box.prop(settings,"adjust_root_depth")
        box.prop(settings,"adjust_scene_range")
        if settings.adjust_scene_range:
            row=box.row(align=True)
            row.prop(bpy.context.scene,"frame_start",text="Start")
            row.prop(bpy.context.scene,"frame_end",text="End")
            box.prop(settings,"adjust_feather")
    if settings.adjust_scene_range:
        layout.label(text="Limited to scene frame range.",icon="INFO")
    box=layout.box()
    box.operator("mw.adjust_build",text="Build Corrected Copy",icon="CHECKMARK")
    box.label(text="Original keys are preserved.")
    # Wrap status text to the current sidebar width.
    import textwrap
    width=max(22,int((bpy.context.region.width if bpy.context.region else 320)/7)-6)
    for line in textwrap.wrap(settings.adjust_status,width=width):
        box.label(text=line)


class MW_OT_use_selected(bpy.types.Operator):
    bl_idname = "mw.use_selected"
    bl_label = "Use Selected Character"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        settings = context.scene.mw_settings
        obj = context.object
        rig = obj if obj and obj.type == "ARMATURE" else obj.find_armature() if obj else None
        if not rig:
            self.report({"ERROR"}, "Select a supported armature or a mesh bound to it.")
            return {"CANCELLED"}
        if settings.capture:
            self.report({"ERROR"}, "Finish this capture session before choosing another target.")
            return {"CANCELLED"}
        settings.target = rig
        return {"FINISHED"}


class MW_OT_prepare(bpy.types.Operator):
    bl_idname = "mw.prepare"
    bl_label = "1. Prepare Capture Copy"
    bl_description = "Create an isolated XYZ Euler copy with normalized transforms and a clean rest pose"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        try:
            rig = workflow.prepare(context, context.scene.mw_settings)
            context.scene.mw_settings.status = "Capture copy ready: " + rig.name
            self.report({"INFO"}, "Capture copy prepared. Original animation and rotations preserved.")
            return {"FINISHED"}
        except (workflow.WorkflowError, RuntimeError, OSError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_OT_reference(bpy.types.Operator):
    bl_idname = "mw.reference_pose"
    bl_label = "Save Current Reference Pose"
    bl_description = "Save the capture copy's current T-pose; export the preset again after changing the reference"
    bl_options = {"REGISTER", "UNDO"}
    restore: BoolProperty(default=False)
    def execute(self, context):
        try:
            workflow.update_reference(context, context.scene.mw_settings, restore=self.restore)
            self.report({"INFO"}, "Reference pose restored." if self.restore else "Reference saved. Export and import a new preset in Marionette.")
            return {"FINISHED"}
        except (workflow.WorkflowError, RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = "mw.export_preset"
    bl_label = "Export Marionette Preset"
    bl_description = "Export a Marionette v3 JSON preset using this character's saved reference pose"
    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    def invoke(self, context, event):
        rig = context.scene.mw_settings.capture
        if rig and not self.filepath:
            self.filepath = bpy.path.clean_name(rig.get("mw_profile", "MIXAMO").title() + "_" + rig.name + "_Preset") + ".json"
        return ExportHelper.invoke(self, context, event)
    def execute(self, context):
        settings = context.scene.mw_settings
        try:
            workflow.require_disconnected(context.scene)
            if not settings.capture:
                raise workflow.WorkflowError("Prepare Capture Copy first.")
            document = workflow.make_preset(settings.capture, settings.include_fingers, settings.position_mode)
            Path(self.filepath).write_text(json.dumps(document, indent=2), encoding="utf-8")
            self.report({"INFO"}, "Preset exported for the official Marionette Blender plugin.")
            return {"FINISHED"}
        except (workflow.WorkflowError, OSError, RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_OT_show(bpy.types.Operator):
    bl_idname = "mw.show_character"
    bl_label = "Switch Character Preview"
    bl_options = {"REGISTER", "UNDO"}
    capture: BoolProperty(default=True)
    def execute(self, context):
        settings = context.scene.mw_settings
        if not settings.capture:
            return {"CANCELLED"}
        workflow.show_capture(context, settings, self.capture)
        rig = settings.capture if self.capture else settings.target
        if rig and rig.name in context.view_layer.objects:
            workflow.select_only(context, [rig], rig)
        return {"FINISHED"}


class MW_OT_push(bpy.types.Operator):
    bl_idname = "mw.push_target_action"
    bl_label = "Push Target Action to NLA"
    bl_description = "Move the target's active Action to its own NLA track so it cannot override the new clip"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        try:
            workflow.push_target_action(context, context.scene.mw_settings)
            self.report({"INFO"}, "Target Action moved to NLA.")
            return {"FINISHED"}
        except (workflow.WorkflowError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_OT_bake(bpy.types.Operator):
    bl_idname = "mw.bake"
    bl_label = "3. Bake and Add to Target NLA"
    bl_description = "Sample the capture Action, convert to the target's bone rotations and create a new Action"
    bl_options = {"REGISTER", "UNDO"}
    add_nla: BoolProperty(default=True)
    def execute(self, context):
        settings = context.scene.mw_settings
        try:
            preview.stop()
            workflow.validate_capture(context, settings)
            if self.add_nla:
                workflow.check_nla_target(settings.target)
            action, slot, count = workflow.bake(context, settings)
            if self.add_nla:
                try:
                    strip = workflow.add_to_nla(context, settings, action, slot)
                except Exception:
                    # Keep the finished bake if NLA placement fails; it remains available in the Action list.
                    settings.status = "Bake kept in Action list: " + action.name
                    raise
                settings.status = f"{action.name}: {count} samples, NLA starts at {strip.frame_start:g}."
            else:
                settings.status = f"{action.name}: {count} samples; choose it in the target Action Editor."
            self.report({"INFO"}, settings.status)
            return {"FINISHED"}
        except (workflow.WorkflowError, RuntimeError, KeyError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_OT_finish(bpy.types.Operator):
    bl_idname = "mw.finish_session"
    bl_label = "Finish Capture Session"
    bl_description = "Restore original visibility and release this session; keep the capture copy and its Actions"
    bl_options = {"REGISTER", "UNDO"}
    def execute(self, context):
        try:
            workflow.require_disconnected(context.scene)
            settings = context.scene.mw_settings
            workflow.show_capture(context, settings, False)
            settings.capture = None
            settings.prepared_target = None
            settings.capture_collection = None
            settings.visibility.clear()
            settings.status = "Session finished. Capture objects and Actions are kept in their collection."
            return {"FINISHED"}
        except workflow.WorkflowError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class MW_PT_main(bpy.types.Panel):
    bl_label = "Marionette Workflow Helper"
    bl_idname = "MW_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mocap Workflow"
    def draw(self, context):
        layout = self.layout
        s = context.scene.mw_settings
        layout.prop(s,"workspace_mode",expand=True)
        if s.workspace_mode=="CLEANUP":
            draw_adjustments(layout,s,force=True)
            layout.label(text="Independent companion | v1.4.0")
            return
        box = layout.box()
        box.label(text="1. Prepare Character", icon="ARMATURE_DATA")
        row = box.row()
        row.enabled = s.capture is None
        row.prop(s, "rig_profile")
        row = box.row()
        row.enabled = s.capture is None
        row.prop(s, "target")
        if not s.capture:
            box.operator("mw.use_selected", icon="EYEDROPPER")
            box.prop(s, "copy_meshes")
            if s.rig_profile == "TRIPO":
                box.prop(s, "straighten_arms")
            box.operator("mw.prepare", icon="DUPLICATE")
        else:
            box.label(text="Capture: " + s.capture.name)
            row = box.row(align=True)
            row.operator("mw.show_character", text="Show Capture", depress=s.capture_visible).capture = True
            row.operator("mw.show_character", text="Show Target", depress=not s.capture_visible).capture = False
        box = layout.box()
        box.label(text="2. Export Character Preset", icon="PRESET")
        box.prop(s, "include_fingers")
        box.prop(s, "position_mode")
        if s.capture:
            rows, missing, ambiguous = mapping.build_map(s.capture.pose.bones.keys(), s.include_fingers, s.position_mode, s.rig_profile)
            box.label(text=f"{sum(bool(r[1]) for r in rows)} mapped joints | FK, no IK poles")
            box.label(text="Reference saved for this character.", icon="CHECKMARK")
            row = box.row(align=True)
            row.operator("mw.reference_pose", text="Save Current T-Pose").restore = False
            row.operator("mw.reference_pose", text="Restore").restore = True
        row = box.row()
        row.enabled = s.capture is not None
        row.operator("mw.export_preset", text="Export Preset JSON", icon="EXPORT")
        box.label(text="In the official Marionette tab:", icon="INFO")
        box.label(text="1. Set Control Rig to the capture copy.")
        if s.capture:
            box.label(text=s.capture.name, icon="ARMATURE_DATA")
        box.label(text="2. Import the JSON and select its preset.")
        if s.position_mode == "HIPS":
            box.label(text="Hips Only: check limb Position flags.", icon="INFO")
            box.label(text="Marionette may enable them on import.")
        box.label(text="3. Connect; Preview / Copy to DCC.")
        if s.rig_profile == "TRIPO":
            box.label(text="Use a Tripo-calibrated preset.", icon="INFO")
            box.label(text="The X Bot preset has different axes.")
        box.label(text="Disconnect before transferring.")
        draw_adjustments(layout,s)
        box = layout.box()
        box.label(text="3. Transfer to Original Character", icon="NLA")
        source_ad = s.capture.animation_data if s.capture else None
        box.label(text="Capture Action: " + (source_ad.action.name if source_ad and source_ad.action else "None"))
        target_ad = s.target.animation_data if s.target else None
        if target_ad and target_ad.action:
            box.label(text="Target has an active Action.", icon="INFO")
            box.operator("mw.push_target_action", icon="NLA_PUSHDOWN")
        box.prop(s, "clip_name")
        box.prop(s, "placement")
        box.prop(s, "blend_frames")
        row = box.row()
        row.enabled = bool(source_ad and source_ad.action)
        row.operator("mw.bake", icon="ACTION").add_nla = True
        row = box.row()
        row.enabled = bool(source_ad and source_ad.action)
        row.operator("mw.bake", text="Bake Only (New Action)").add_nla = False
        if s.last_action:
            box.label(text="Last bake: " + s.last_action.name, icon="CHECKMARK")
        if s.capture:
            layout.operator("mw.finish_session", icon="CHECKMARK")
        layout.label(text="Independent companion | v1.4.0")


classes = (MW_Visibility, MW_Settings, MW_OT_reset_torso, MW_OT_reset_gait, MW_OT_preview, MW_OT_adjust_source, MW_OT_adjust_build, MW_OT_adjust_compare, MW_OT_use_selected, MW_OT_prepare,
           MW_OT_reference, MW_OT_export, MW_OT_show, MW_OT_push,
           MW_OT_bake, MW_OT_finish, MW_PT_main)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mw_settings = PointerProperty(type=MW_Settings)
    preview.register()


def unregister():
    preview.unregister()
    # Visibility is only changed in the current view layer, matching hide_set's scope.
    if hasattr(bpy.types.Scene, "mw_settings"):
        settings = bpy.context.scene.mw_settings
        workflow.show_capture(bpy.context, settings, False)
        del bpy.types.Scene.mw_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
