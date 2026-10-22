"""A truncated or misleading release must fail verification, including under -O."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from tools.verify_release import check_archive, check_wheel_source, example_matches, read_manifest, verify
from zensigil import __version__

ROOT = Path(__file__).resolve().parents[1]


class ReleaseIntegrityTests(unittest.TestCase):
    def manifest(self, directory, text):
        path = Path(directory) / f'zensigil-{__version__}-SHA256SUMS.txt'
        path.write_text(text, encoding='ascii')
        return path

    def test_empty_manifest_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as directory:
            self.manifest(directory, '')
            with self.assertRaisesRegex(ValueError, 'empty'):
                verify(directory)

    def test_malformed_duplicate_and_unsafe_entries(self):
        digest = 'a' * 64
        for line in ('bad  file.zip', digest + '  ../outside', digest + '  a\\b',
                     digest + '  C:outside', digest + '  .hidden', digest + '  a b.zip',
                     digest + '  a.zip\n' + digest + '  A.zip', digest + '  a.zip\n\n'):
            with self.subTest(line=line), tempfile.TemporaryDirectory() as directory:
                self.manifest(directory, line)
                with self.assertRaises(ValueError):
                    read_manifest(Path(directory))

    def test_missing_required_inventory_and_packages_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            self.manifest(directory, 'a' * 64 + '  harmless.txt\n')
            with self.assertRaisesRegex(ValueError, 'missing required'):
                verify(directory, require_distributables=True)

    def test_checks_run_under_optimized_python(self):
        with tempfile.TemporaryDirectory() as directory:
            self.manifest(directory, '')
            result = subprocess.run([sys.executable, '-O', str(ROOT / 'tools/verify_release.py'), directory],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1)
            self.assertIn('empty', result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_examples_check_proposals_notes_and_duplicates_not_only_values(self):
        good = {'ok': True, 'values': [], 'proposals': [{'action': 'review', 'fields': {'count': 2},
                'requires_review': True}], 'notes': [{'message': 'Checked'}],
                'stats': {'duplicates_collapsed': 1}}
        expected = {'proposals': [['review', {'count': 2}]], 'notes': ['Checked'], 'duplicates': 1}
        example_matches('case', good, expected)
        for edit in (lambda d: d['proposals'][0]['fields'].update(count=3),
                     lambda d: d['proposals'][0].update(action='send'),
                     lambda d: d['proposals'][0].update(requires_review=False),
                     lambda d: d.update(notes=[]),
                     lambda d: d['stats'].update(duplicates_collapsed=0)):
            changed = json.loads(json.dumps(good))
            edit(changed)
            with self.assertRaises(ValueError):
                example_matches('case', changed, expected)
        numeric = {'ok': True, 'values': [1, {'count': 0}], 'proposals': [], 'notes': [],
                   'stats': {'duplicates_collapsed': 0}}
        wanted = {'values': [1.0, {'count': 0}], 'note_count': 0}
        example_matches('numeric compatibility', numeric, wanted)
        for edit in (lambda d: d.update(values=[True, {'count': 0}]),
                     lambda d: d.update(values=[1, {'count': False}]),
                     lambda d: d['stats'].update(duplicates_collapsed=False)):
            changed = json.loads(json.dumps(numeric))
            edit(changed)
            with self.assertRaises(ValueError):
                example_matches('strict boolean', changed, wanted)

    def test_source_archive_rejects_cross_platform_paths_and_special_files(self):
        normal = {'zensigil/LICENSE': 'license', 'zensigil/README.md': 'readme',
                  'zensigil/pyproject.toml': f'version = "{__version__}"',
                  'zensigil/zensigil/__init__.py': '', 'zensigil/zensigil/web/index.html': ''}
        for unsafe, mode in [('C:/escape.py', 0o100644), ('zensigil/readme.md', 0o100644),
                             ('zensigil/link', 0o120777), ('zensigil/pipe', 0o010600),
                             ('zensigil/CON.txt', 0o100644), ('zensigil/trailing.', 0o100644),
                             ('zensigil/README.md/child', 0o100644)]:
            with self.subTest(path=unsafe), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'source.zip'
                with zipfile.ZipFile(path, 'w') as archive:
                    for name, body in normal.items():
                        archive.writestr(name, body)
                    info = zipfile.ZipInfo(unsafe)
                    info.create_system = 3
                    info.external_attr = mode << 16
                    archive.writestr(info, '../../outside.md')
                with self.assertRaises(ValueError):
                    check_archive(path, 'source')

    def test_wheel_runtime_matches_source_including_browser_assets(self):
        files = {'zensigil/__init__.py': '__version__ = "0.8.0"\n',
                 'zensigil/web/index.html': '<script src="assets/current.js"></script>',
                 'zensigil/web/assets/current.js': '/* current */'}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.zip'
            with zipfile.ZipFile(source, 'w') as archive:
                for name, body in files.items():
                    archive.writestr('zensigil/' + name, body)
            for change in ('same', 'stale', 'missing', 'changed'):
                with self.subTest(change=change):
                    wheel = root / (change + '.whl')
                    current = dict(files)
                    if change == 'stale':
                        current['zensigil/web/assets/old.js'] = '/* stale build output */'
                    elif change == 'missing':
                        del current['zensigil/web/assets/current.js']
                    elif change == 'changed':
                        current['zensigil/web/assets/current.js'] = '/* different bytes */'
                    with zipfile.ZipFile(wheel, 'w') as archive:
                        for name, body in current.items():
                            archive.writestr(name, body)
                        archive.writestr(f'zensigil-{__version__}.dist-info/RECORD', '')
                    if change == 'same':
                        check_wheel_source(source, wheel)
                    else:
                        with self.assertRaisesRegex(ValueError, 'Wheel runtime'):
                            check_wheel_source(source, wheel)

    def test_wheel_rejects_unexpected_top_level_payload(self):
        prefix = f'zensigil-{__version__}.dist-info/'
        files = {'zensigil/__init__.py': '', 'zensigil/web/index.html': '',
                 prefix + 'METADATA': f'Name: zensigil\nVersion: {__version__}\n',
                 prefix + 'WHEEL': '', prefix + 'entry_points.txt': 'zensigil = zensigil.__main__:main',
                 'unexpected.pth': 'import unexpected'}
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / 'package.whl'
            with zipfile.ZipFile(wheel, 'w') as archive:
                for name, body in files.items():
                    archive.writestr(name, body)
            with self.assertRaisesRegex(ValueError, 'outside its runtime'):
                check_archive(wheel, 'wheel')


if __name__ == '__main__':
    unittest.main()
