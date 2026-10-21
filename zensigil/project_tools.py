"""Explicit project source enumeration and format preflight; no directory scanning."""
from pathlib import Path
from .projects import load_project
from .jsonio import loads
from .programs import read_text
from .modules import file_modules
from .formatter import format_source, write_formatted


def project_sources(directory):
    project = load_project(directory)
    paths = {}
    def add(path):
        logical = Path(path)
        if logical.is_symlink() or any(parent.is_symlink() for parent in logical.parents if parent != project['root'] and parent.is_relative_to(project['root'])):
            raise ValueError('Project formatting does not follow source file symlinks.')
        resolved = logical.resolve()
        if not resolved.is_relative_to(project['root']):
            raise ValueError('Project source must stay inside its root.')
        if resolved not in paths:
            if len(paths) >= 256:
                raise ValueError('Project tools allow at most 256 explicit source files.')
            paths[resolved] = read_text(resolved, 65536)
    manifest = loads(read_text(project['root'] / 'zensigil.json', 16384))
    entries = [project['root'] / name for name in [manifest['entry']] + manifest.get('tests', [])]
    for path in entries:
        add(path)
        for name in file_modules(paths[path.resolve()], path, root=project['root']):
            add(project['root'] / name)
    return project['root'], paths


def format_project(directory, write=False):
    root, sources = project_sources(directory)
    # Parse and format every source before any writes. Writes are atomic per file;
    # a disk failure can still leave a partially formatted project.
    formatted = {path: format_source(source) for path, source in sources.items()}
    changed = [path for path in sources if sources[path] != formatted[path]]
    if write:
        for path in changed:
            if path.is_symlink() or read_text(path, 65536) != sources[path]:
                raise ValueError('A source changed during formatting; rerun after saving your edits.')
        for path in changed:
            write_formatted(path, formatted[path])
    return {'files': len(sources), 'changed': [path.relative_to(root).as_posix() for path in changed]}
