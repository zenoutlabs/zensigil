"""Build a deterministic source ZIP, portable examples and SHA-256 manifest.

Build the UI first. Wheel building is separate; place the wheel in destination
before packaging to include its hash. ZIP metadata is fixed; reproducibility
assumes identical source bytes and the same compression implementation.
"""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from zensigil import __version__
from zensigil.programs import encode_program


def package(destination):
    destination = Path(destination).resolve()
    if not (ROOT / 'zensigil/web/index.html').is_file():
        raise SystemExit('Build the playground before packaging.')
    if destination == ROOT:
        raise SystemExit('Choose a release directory outside the project root.')
    destination.mkdir(parents=True, exist_ok=True)
    excluded = {'node_modules', '__pycache__', '.git', '.venv', 'build', 'dist', 'work', '.DS_Store'}
    archive = destination / f'zensigil-starter-{__version__}.zip'
    paths = [path for path in ROOT.rglob('*') if path.is_file() and not path.is_symlink()
             and not (destination.is_relative_to(ROOT) and path.is_relative_to(destination))
             and not any(part in excluded or part.endswith('.egg-info') for part in path.relative_to(ROOT).parts)]
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in sorted(paths):
            name = (Path('zensigil') / path.relative_to(ROOT)).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(info, path.read_bytes(), compresslevel=9)
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise SystemExit('Archive integrity check failed.')
    outputs = [archive]
    for key, title in (('reading-list', 'Reading list'), ('event-capacity', 'Event capacity'),
                       ('project-budget', 'Project budget'), ('stock-review', 'Stock review'),
                       ('support', 'Support triage'), ('algorithms', 'Algorithms & typed state'),
                       ('transformations', 'Collection transformations'),
                       ('module-lab', 'Modules & executable tests'), ('decimal-lab', 'Exact decimal text'),
                       ('closure-lab', 'Closures & function factories'), ('typed-data', 'Nested types'),
                       ('collection-lab', 'Collection analysis'),
                       ('namespace-lab', 'Namespaced libraries'), ('sequence-lab', 'Running totals and summaries')):
        example = ROOT / 'examples'
        def optional(suffix):
            path = example / (key + suffix)
            return path.read_text(encoding='utf-8') if path.is_file() else ''
        program = {'format': 'zensigil-program', 'format_version': 1, 'language_version': __version__,
                   'name': title, 'source': optional('.zs'), 'data_text': optional('.json'),
                   'contract_text': optional('.contract.json'), 'proposal_contract_text': optional('.proposal.json'),
                   'modules': json.loads(optional('.modules.json') or '{}')}
        path = destination / f'{key}.sigil.json'
        with path.open('w', encoding='utf-8', newline='') as handle:
            handle.write(encode_program(program))
        outputs.append(path)
    outputs += sorted(destination.glob(f'zensigil-{__version__}-*.whl'))
    outputs += sorted(destination.glob(f'zensigil-language-{__version__}.vsix'))
    manifest = destination / f'zensigil-{__version__}-SHA256SUMS.txt'
    with manifest.open('w', encoding='ascii', newline='') as handle:
        handle.write(''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in outputs))
    print(f'{archive}: {len(paths)} files, {archive.stat().st_size:,} bytes; integrity verified.')
    print(f'{manifest}: {len(outputs)} checksums.')
    return archive


if __name__ == '__main__':
    package(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT.parent)
