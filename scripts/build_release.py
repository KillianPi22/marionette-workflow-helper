"""Build deterministic, public Blender extension archives using only stdlib."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'marionette_workflow'
REQUIRED = {
    '__init__.py', 'blender_manifest.toml', 'calibration.py', 'correction.py',
    'LICENSE', 'mapping.py', 'presets/Mixamo_Full_FK_Portable.json',
    'preview.py', 'README_EN.md', 'workflow.py',
}


def package_version():
    manifest = tomllib.loads((PACKAGE / 'blender_manifest.toml').read_text(encoding='utf-8'))
    for node in ast.parse((PACKAGE / '__init__.py').read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'bl_info' for t in node.targets):
            info = ast.literal_eval(node.value)
            break
    else:
        raise ValueError('Missing bl_info')
    version = manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected numeric major.minor.patch version')
    if version != '.'.join(map(str, info['version'])):
        raise ValueError('Manifest and bl_info versions disagree')
    if manifest['id'] != 'marionette_workflow':
        raise ValueError('Unexpected extension identity')
    return version


def write_zip(path, entries):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(entries.items()):
            item = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data, compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None or set(archive.namelist()) != set(entries):
            raise ValueError(f'Archive integrity check failed: {path.name}')
        if any(archive.read(name) != data for name, data in entries.items()):
            raise ValueError(f'Archive payload differs from source: {path.name}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--check-release-request', action='store_true')
    args = parser.parse_args()
    version = package_version()
    if args.check_release_request:
        requested = json.loads((ROOT / 'release.json').read_text(encoding='utf-8'))['version']
        if requested != version:
            raise ValueError(f'Release request {requested} differs from source version {version}')
        if not (ROOT / 'docs' / 'releases' / f'{version}.md').is_file():
            raise ValueError(f'Missing release notes for {version}')

    entries = {p.relative_to(PACKAGE).as_posix(): p.read_bytes() for p in PACKAGE.rglob('*')
               if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    if set(entries) != REQUIRED:
        raise ValueError(f'Unexpected package contents; missing={REQUIRED - entries.keys()}, extra={entries.keys() - REQUIRED}')
    preset = json.loads(entries['presets/Mixamo_Full_FK_Portable.json'])
    if preset.get('version') != 3 or preset.get('program') != 'blender' or not preset.get('presets'):
        raise ValueError('Invalid portable Marionette preset')
    if (ROOT / 'LICENSE').read_bytes() != entries['LICENSE']:
        raise ValueError('Root and extension licenses disagree')

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    extension = output / f'marionette_workflow-{version}.zip'
    write_zip(extension, entries)
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in entries.items()}
    pack_entries = {
        extension.name: extension.read_bytes(),
        'START_HERE_EN.md': entries['README_EN.md'],
        'READ_FIRST.md': (ROOT / 'docs' / 'PUBLIC_PACK.md').read_bytes(),
        'LICENSE': entries['LICENSE'],
        'presets/Mixamo_Full_FK_Portable.json': entries['presets/Mixamo_Full_FK_Portable.json'],
        'SOURCE_SHA256.json': (json.dumps(hashes, indent=2, sort_keys=True) + '\n').encode(),
    }
    pack = output / f'Marionette_Workflow_Pack_{version}.zip'
    write_zip(pack, pack_entries)
    artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (extension, pack)}
    checksums = output / 'SHA256SUMS.txt'
    checksums.write_text(''.join(f'{digest}  {name}\n' for name, digest in artifacts.items()), encoding='utf-8')
    print(json.dumps({'version': version, 'source_files': len(entries), 'output': str(output),
                      'artifacts': artifacts, 'checksums': checksums.name}, indent=2))


if __name__ == '__main__':
    main()
