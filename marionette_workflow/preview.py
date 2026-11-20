"""Disposable current-frame preview, refreshed by a main-thread timer."""
import bpy
from bpy.app.handlers import persistent
from . import correction

_state = None

def active():
    return _state is not None

def start(context):
    global _state
    stop()
    s = context.scene.mw_settings
    rig, _, _, _ = correction.resolve_source(context,s)
    _state = dict(scene=context.scene,rig=rig,action=rig.animation_data.action,
                  slot=rig.animation_data.action_slot,result=s.adjust_result,temp=None,key=None)
    try:
        refresh(context)
    except Exception:
        stop()
        raise
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick,first_interval=.12)

def refresh(context):
    state = _state
    s = state['scene'].mw_settings
    if context.scene != state['scene'] or correction.active_rig(context,s) != state['rig']:
        raise correction.Error('Preview stopped: scene or rig changed.')
    old = state['temp']
    report = correction.build(context,s,preview=True)
    state['temp'] = s.adjust_result
    state['temp'].name = 'MW Temporary Preview'
    state['temp']['mw_temporary_preview'] = True
    if old and old.users == 0:
        bpy.data.actions.remove(old)
    s.adjust_status = 'Live preview: current frame' + (' — reach limited' if report['reach_frames'] else '')
    for area in context.screen.areas if context.screen else []:
        area.tag_redraw()

def tick():
    if not _state:
        return None
    try:
        if _state["rig"].animation_data.action != _state["temp"]:
            raise correction.Error("Active Action changed.")
        context = bpy.context
        s = _state['scene'].mw_settings
        props = [p.identifier for p in s.bl_rna.properties if p.identifier.startswith('adjust_')
                 and p.identifier not in {'adjust_status','adjust_result'}] + list(correction.LOWER_SETTINGS)
        key = (context.scene.as_pointer(),context.scene.frame_current,context.scene.frame_subframe,
               context.scene.frame_start,context.scene.frame_end,tuple(str(getattr(s,p)) for p in props),
               str(s.adjust_camera.matrix_world) if s.adjust_camera else '')
        if key != _state['key']:
            refresh(context)
            _state['key'] = key
    except Exception as exc:
        stop()
        if hasattr(bpy.context.scene,'mw_settings'):
            bpy.context.scene.mw_settings.adjust_status = 'Preview stopped: '+str(exc)
        return None
    return .12

def stop():
    global _state
    state,_state = _state,None
    if bpy.app.timers.is_registered(tick):
        bpy.app.timers.unregister(tick)
    if not state:
        recover_preview()
        return
    try:
        s = state['scene'].mw_settings
        rig = state['rig']
        temp = state['temp']
        if rig.animation_data.action == temp:
            rig.animation_data.action = state['action']
            rig.animation_data.action_slot = state['slot']
            correction.restore_baseline(rig,s)
            state['scene'].frame_set(state['scene'].frame_current,subframe=state['scene'].frame_subframe)
        s.adjust_result = state['result']
        s.adjust_status = 'Preview stopped. Build Corrected Copy to apply settings.'
        if temp and temp.users == 0:
            bpy.data.actions.remove(temp)
    except (ReferenceError,RuntimeError):
        pass

@persistent
def cleanup(*args):
    stop()

@persistent
def recover_preview(*args):
    """Undo/load can restore Blender IDs without restoring Python session state."""
    if active() or not hasattr(bpy.data,"scenes"):
        return
    for scene in bpy.data.scenes:
        if not hasattr(scene,'mw_settings'):
            continue
        s = scene.mw_settings
        rig = s.adjust_owner
        source = s.adjust_source
        if not rig or not source or not rig.animation_data:
            continue
        action = rig.animation_data.action
        if not action or action == source:
            continue
        legacy = action.name.startswith('MW Temporary Preview') and action.get('mw_adjustment_source') == source.name
        if not (action.get('mw_temporary_preview') or legacy):
            continue
        slot = next((slot for slot in source.slots if slot.handle == s.adjust_source_slot),None)
        if slot is None:
            continue
        rig.animation_data.action = source
        rig.animation_data.action_slot = slot
        correction.restore_baseline(rig,s)
        if s.adjust_result == action:
            s.adjust_result = None
        scene.frame_set(scene.frame_current,subframe=scene.frame_subframe)
        s.adjust_status = 'Stale preview recovered. Original restored; restart Live Preview.'

def register():
    for handlers in (bpy.app.handlers.save_pre,bpy.app.handlers.load_pre,bpy.app.handlers.undo_pre,bpy.app.handlers.render_pre):
        if cleanup not in handlers:
            handlers.append(cleanup)
    for handlers in (bpy.app.handlers.undo_post,bpy.app.handlers.redo_post,bpy.app.handlers.load_post):
        if recover_preview not in handlers:
            handlers.append(recover_preview)
    if not bpy.app.timers.is_registered(recover_preview):
        bpy.app.timers.register(recover_preview,first_interval=.1)

def unregister():
    if bpy.app.timers.is_registered(recover_preview):
        bpy.app.timers.unregister(recover_preview)
    stop()
    for handlers in (bpy.app.handlers.save_pre,bpy.app.handlers.load_pre,bpy.app.handlers.undo_pre,bpy.app.handlers.render_pre):
        if cleanup in handlers:
            handlers.remove(cleanup)
    for handlers in (bpy.app.handlers.undo_post,bpy.app.handlers.redo_post,bpy.app.handlers.load_post):
        if recover_preview in handlers:
            handlers.remove(recover_preview)
