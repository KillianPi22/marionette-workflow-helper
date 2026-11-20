"""Install the locally built public ZIP in an isolated Blender profile."""
import ast
import importlib
import json
import os
from pathlib import Path
import tomllib

import bpy

checks = []


def check(name, condition):
    assert condition, name
    checks.append(name)
    print('PASS:', name, flush=True)


root = Path(__file__).resolve().parents[1]
profile = Path(os.environ['MW_TEST_PROFILE']).resolve()
assert profile.is_relative_to(root / 'build'), 'Use scripts/run_tests.py'
archive = Path(os.environ['MW_TEST_PACKAGE']).resolve()
manifest = tomllib.loads((root/'marionette_workflow/blender_manifest.toml').read_text(encoding='utf-8'))
repo = next(r for r in bpy.context.preferences.extensions.repos if r.module == 'user_default')
assert Path(repo.directory).resolve().is_relative_to(profile)
check('native installation succeeds', bpy.ops.extensions.package_install_files(filepath=str(archive),
      repo='user_default', enable_on_install=True, overwrite=True) == {'FINISHED'})
name = 'bl_ext.user_default.marionette_workflow'
addon = importlib.import_module(name)
installed_manifest = tomllib.loads(Path(addon.__file__).with_name('blender_manifest.toml').read_text(encoding='utf-8'))
check('installed metadata matches working manifest', installed_manifest['version'] == manifest['version'])
check('installed source is isolated from user profile', Path(addon.__file__).resolve().is_relative_to(profile))
check('native enable exposes settings', hasattr(bpy.types.Scene, 'mw_settings') and name in bpy.context.preferences.addons)
check('portable preset is included', Path(addon.__file__).with_name('presets').joinpath('Mixamo_Full_FK_Portable.json').is_file())
icons = bpy.types.UILayout.bl_rna.functions['label'].parameters['icon'].enum_items.keys()
tree = ast.parse(Path(addon.__file__).read_text(encoding='utf-8'))
check('all literal UI icons exist', all(node.value.value in icons for node in ast.walk(tree)
      if isinstance(node, ast.keyword) and node.arg == 'icon' and isinstance(node.value, ast.Constant)))
settings = bpy.context.scene.mw_settings
settings.adjust_pitch = .2
check('installed torso reset operator works', bpy.ops.mw.reset_torso() == {'FINISHED'} and settings.adjust_pitch == 0)
settings.right_lift = .2
settings.foot_width = .8
check('installed gait reset operator works', bpy.ops.mw.reset_gait() == {'FINISHED'} and settings.right_lift == 0 and settings.foot_width == 1)
check('native disable succeeds', bpy.ops.preferences.addon_disable(module=name) == {'FINISHED'} and not hasattr(bpy.types.Scene, 'mw_settings'))
check('native re-enable succeeds', bpy.ops.preferences.addon_enable(module=name) == {'FINISHED'} and hasattr(bpy.types.Scene, 'mw_settings'))
bpy.ops.preferences.addon_disable(module=name)
print('INSTALL_TEST_SUMMARY', json.dumps({'passed': True, 'blender': bpy.app.version_string,
      'checks': len(checks), 'tests': checks}), flush=True)
