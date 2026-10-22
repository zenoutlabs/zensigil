"""Verify the release inventory, hashes, archives, and expected example results.

These checks stay active with ``python -O``. A matching checksum proves bytes,
not the publisher's identity. Use --require-distributables for a public release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from zensigil import __version__, run
from zensigil.programs import decode_program

EXAMPLES = ('reading-list', 'event-capacity', 'project-budget', 'stock-review',
            'support', 'algorithms', 'transformations', 'module-lab', 'decimal-lab',
            'closure-lab', 'typed-data', 'collection-lab', 'namespace-lab', 'sequence-lab')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_manifest(directory):
    path = directory / f'zensigil-{__version__}-SHA256SUMS.txt'
    require(path.is_file() and not path.is_symlink(), 'Missing regular checksum manifest.')
    require(path.stat().st_size <= 65536, 'Checksum manifest exceeds 64 KiB.')
    lines = path.read_text(encoding='ascii').splitlines()
    require(bool(lines), 'Checksum manifest is empty.')
    entries = {}
    folded = set()
    for line in lines:
        match = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)', line)
        require(match is not None, 'Invalid checksum entry or unsafe filename.')
        digest, name = match.groups()
        require(name.lower() not in folded, f'Duplicate checksum filename: {name}')
        folded.add(name.lower())
        entries[name] = digest
    return entries


def same_value(actual, expected):
    """Compare JSON values without treating booleans as numeric values."""
    if type(actual) in (int, float) and type(expected) in (int, float):
        return actual == expected
    if type(actual) is not type(expected):
        return False
    if type(actual) is list:
        return len(actual) == len(expected) and all(same_value(a, b) for a, b in zip(actual, expected))
    if type(actual) is dict:
        return actual.keys() == expected.keys() and all(same_value(actual[key], value) for key, value in expected.items())
    return actual == expected


def example_matches(key, result, expected):
    require(result.get('ok') is True, f'{key}: example execution failed: {result.get("diagnostics")}')
    require(same_value(result.get('values'), expected.get('values', [])), f'{key}: structured values differ.')
    wanted = expected.get('proposals', [])
    proposals = result.get('proposals', [])
    require(len(proposals) == len(wanted), f'{key}: proposal count differs.')
    for actual, (action, fields) in zip(proposals, wanted):
        require(actual.get('action') == action, f'{key}: proposal action differs.')
        require(actual.get('requires_review') is True, f'{key}: proposal lacks review requirement.')
        require(all(same_value(actual.get('fields', {}).get(k), v) and k in actual.get('fields', {})
                    for k, v in fields.items()), f'{key}: proposal fields differ.')
    if 'notes' in expected:
        require([n.get('message') for n in result.get('notes', [])] == expected['notes'],
                f'{key}: notes differ.')
    else:
        require(len(result.get('notes', [])) == expected['note_count'], f'{key}: note count differs.')
    duplicates = result.get('stats', {}).get('duplicates_collapsed')
    require(type(duplicates) is int and duplicates == expected.get('duplicates', 0),
            f'{key}: duplicate count differs.')


def check_archive(path, kind):
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, f'{path.name}: damaged archive.')
        names = archive.namelist()
        require(len(names) == len({name.casefold().rstrip('/') for name in names}),
                f'{path.name}: duplicate archive paths, including letter-case aliases.')
        require(all(not name.startswith(('/', '\\')) and '\\' not in name
                    and ':' not in name
                    and all(part not in ('', '.', '..') and not part.endswith((' ', '.'))
                            and not re.search(r'[\x00-\x1f]', part)
                            and not re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part)
                            for part in name.rstrip('/').split('/'))
                    for name in names), f'{path.name}: unsafe archive path.')
        for member in archive.infolist():
            kind_bits = stat.S_IFMT(member.external_attr >> 16)
            expected_kind = stat.S_IFDIR if member.is_dir() else stat.S_IFREG
            require(kind_bits in (0, expected_kind), f'{path.name}: unsupported archive member type.')
        files = {name.casefold() for name in names if not name.endswith('/')}
        require(not any('/'.join(name.casefold().split('/')[:index]) in files
                        for name in names for index in range(1, len(name.split('/')))),
                f'{path.name}: a file is also an archive directory.')
        if kind == 'source':
            require(all(name.startswith('zensigil/') for name in names), 'Source ZIP has a file outside its project folder.')
            required = {'zensigil/LICENSE', 'zensigil/README.md', 'zensigil/pyproject.toml',
                        'zensigil/zensigil/__init__.py', 'zensigil/zensigil/web/index.html'}
            require(required.issubset(names), 'Source ZIP is missing required files.')
            require(not any('/node_modules/' in n or '/.git/' in n or '/__pycache__/' in n for n in names),
                    'Source ZIP includes local build or repository files.')
            require(f'version = "{__version__}"' in archive.read('zensigil/pyproject.toml').decode(),
                    'Source ZIP version does not match the release.')
        elif kind == 'vsix':
            required = {'extension/package.json', 'extension/extension.js', 'extension/client.js'}
            require(required.issubset(names), 'VSIX is missing extension files.')
            metadata = json.loads(archive.read('extension/package.json'))
            require(metadata.get('publisher') == 'zenoutlabs' and metadata.get('version') == __version__,
                    'VSIX publisher or version does not match.')
        elif kind == 'wheel':
            prefix = f'zensigil-{__version__}.dist-info/'
            require(all(name.startswith(('zensigil/', prefix)) for name in names),
                    'Wheel contains a file outside its runtime or package metadata.')
            required = {'zensigil/__init__.py', 'zensigil/web/index.html', prefix + 'METADATA',
                        prefix + 'WHEEL', prefix + 'entry_points.txt'}
            require(required.issubset(names), 'Wheel is missing runtime, browser, or package metadata.')
            metadata = archive.read(prefix + 'METADATA').decode()
            require(f'\nVersion: {__version__}\n' in metadata, 'Wheel version does not match.')
            require('Requires-Dist:' not in metadata, 'Wheel has unexpected runtime dependencies.')
            require('zensigil = zensigil.__main__:main' in archive.read(prefix + 'entry_points.txt').decode(),
                    'Wheel is missing the command entry point.')


def check_wheel_source(source_path, wheel_path):
    """The distributable runtime must match the source release, including assets."""
    with zipfile.ZipFile(source_path) as source, zipfile.ZipFile(wheel_path) as wheel:
        prefix = 'zensigil/zensigil/'
        expected = {name.removeprefix('zensigil/'): name for name in source.namelist()
                    if name.startswith(prefix) and not name.endswith('/')}
        actual = {name for name in wheel.namelist()
                  if name.startswith('zensigil/') and not name.endswith('/')}
        require(set(expected) == actual,
                'Wheel runtime inventory differs from source ZIP; missing: '
                + ', '.join(sorted(set(expected) - actual)) + '; unexpected: '
                + ', '.join(sorted(actual - set(expected))))
        for name, source_name in expected.items():
            require(wheel.read(name) == source.read(source_name),
                    f'Wheel runtime bytes differ from source ZIP: {name}')


def verify(directory, require_distributables=False):
    directory = Path(directory)
    entries = read_manifest(directory)
    source_name = f'zensigil-starter-{__version__}.zip'
    wheel_name = f'zensigil-{__version__}-py3-none-any.whl'
    vsix_name = f'zensigil-language-{__version__}.vsix'
    required = {source_name, *(key + '.sigil.json' for key in EXAMPLES)}
    allowed = required | {wheel_name, vsix_name}
    if require_distributables:
        required |= {wheel_name, vsix_name}
    require(required.issubset(entries), 'Release is missing required artifacts: ' + ', '.join(sorted(required - entries.keys())))
    require(set(entries).issubset(allowed), 'Manifest contains an unexpected artifact.')
    for name in allowed:
        require(not (directory / name).exists() or name in entries,
                f'Release artifact is not covered by checksums: {name}')
    expected = json.loads((ROOT / 'tests/fixtures/examples-expected.json').read_text(encoding='utf-8'))
    for name, digest in entries.items():
        path = directory / name
        require(path.is_file() and not path.is_symlink(), f'Missing regular release file: {name}')
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, f'Checksum mismatch: {name}')
        if name == source_name:
            check_archive(path, 'source')
        elif name == wheel_name:
            check_archive(path, 'wheel')
        elif name == vsix_name:
            check_archive(path, 'vsix')
        else:
            program = decode_program(path.read_text(encoding='utf-8'))
            result = run(program['source'], json.loads(program['data_text']),
                         contract=json.loads(program['contract_text']) if program['contract_text'] else None,
                         proposal_contract=json.loads(program['proposal_contract_text']) if program['proposal_contract_text'] else None,
                         modules=program['modules'])
            key = name.removesuffix('.sigil.json')
            example_matches(key, result, expected[key])
    if wheel_name in entries:
        check_wheel_source(directory / source_name, directory / wheel_name)
    report = {'ok': True, 'version': __version__, 'checksums': len(entries),
              'portable_examples': len(EXAMPLES), 'distributables_required': require_distributables,
              'wheel_matches_source': wheel_name in entries}
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', default=str(ROOT.parent))
    parser.add_argument('--require-distributables', action='store_true')
    args = parser.parse_args()
    try:
        verify(args.directory, args.require_distributables)
    except (ValueError, OSError, UnicodeError, zipfile.BadZipFile) as error:
        parser.exit(1, f'Release verification failed: {error}\n')
