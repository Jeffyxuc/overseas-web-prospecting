#!/usr/bin/env python3
"""Install both skills from ZIP archives, preserving LF and backing up old copies."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import urllib.request
import uuid
import zipfile

NAMES = ('overseas-web-prospecting', 'google-maps-scraper')


def codex_home():
    return Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser()


def default_skills_dir():
    if os.environ.get('CODEX_HOME'):
        return codex_home() / 'skills'
    agents = Path.home() / '.agents/skills'
    return agents if (agents / NAMES[0] / 'SKILL.md').is_file() else codex_home() / 'skills'


def unpack_skill(data, subdir, target):
    """Extract only one skill subtree; ZIP paths and symlinks cannot escape it."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        roots = {PurePosixPath(m.filename).parts[0] for m in members if m.filename}
        if len(roots) != 1:
            raise ValueError('Unexpected repository archive layout')
        prefix = next(iter(roots)) + '/' + (subdir.strip('/') + '/' if subdir else '')
        for member in members:
            if chr(92) in member.orig_filename:
                raise ValueError('Unsafe archive path separator')
            if not member.filename.startswith(prefix) or member.is_dir():
                continue
            relative = PurePosixPath(member.filename[len(prefix):])
            if relative.is_absolute() or '..' in relative.parts or chr(92) in str(relative) or ':' in str(relative):
                raise ValueError('Unsafe archive path')
            if ((member.external_attr >> 16) & 0o170000) == 0o120000:
                raise ValueError('Archive symlinks are not supported')
            if '.git' in relative.parts or '__pycache__' in relative.parts:
                continue
            dest = target.joinpath(*relative.parts)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(member))
    if not (target / 'SKILL.md').is_file():
        raise ValueError('Archive does not contain the requested skill')


def download(repo, subdir, target):
    # Never use git checkout: global core.autocrlf must not alter Bash files.
    url = f'https://codeload.github.com/{repo}/zip/refs/heads/main'
    with urllib.request.urlopen(url, timeout=90) as response:
        unpack_skill(response.read(), subdir, target)


def verify_source(source):
    manifest = json.loads((source / 'package-manifest.json').read_text(encoding='utf-8-sig'))
    for name, digest in manifest['files'].items():
        path = source / name
        if not path.resolve().is_relative_to(source.resolve()) or not path.is_file():
            raise ValueError('Invalid release manifest path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('Release file digest mismatch: ' + name)
    return manifest['version']


def install_prepared(prepared, roots, target, state):
    """Move exact skill directories to backups, rolling back if copying fails."""
    target = target.resolve()
    roots = list(dict.fromkeys([Path(r).resolve() for r in roots] + [target]))
    if any(state.resolve().is_relative_to(r / n) for r in roots for n in NAMES):
        raise ValueError('State directory cannot be inside a skill being replaced')
    backup = state / ('backup-' + uuid.uuid4().hex)
    moved, installed = [], []
    try:
        for index, root in enumerate(roots):
            for name in NAMES:
                old = root / name
                if old.is_symlink():
                    raise ValueError('Existing skill is a symlink; preserve it and choose a separate --skills-dir')
                if old.exists():
                    if old.resolve().parent != root or not (old / 'SKILL.md').is_file():
                        raise ValueError('Refusing to move an unexpected installation directory')
                    dest = backup / str(index) / name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    old.rename(dest)
                    moved.append((dest, old))
        target.mkdir(parents=True, exist_ok=True)
        for name in NAMES:
            dest = target / name
            installed.append(dest)
            shutil.copytree(prepared / name, dest, ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
    except Exception:
        # Only remove newly created directories whose exact parent we just verified.
        for dest in installed:
            if dest.exists() and dest.parent == target and not dest.is_symlink():
                shutil.rmtree(dest)
        for saved, old in reversed(moved):
            saved.rename(old)
        raise
    return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Optional complete local release folder')
    parser.add_argument('--skills-dir', type=Path)
    parser.add_argument('--state-dir', type=Path, default=codex_home() / 'overseas-web-prospecting')
    args = parser.parse_args()
    target = (args.skills_dir or default_skills_dir()).resolve()
    state = args.state_dir.expanduser().resolve()
    state.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prospecting-install-') as temp:
        prepared = Path(temp)
        if args.source:
            shutil.copytree(args.source.resolve(), prepared / NAMES[0], ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc'))
        else:
            print('[DOWNLOAD] Overseas prospecting skill', flush=True)
            download('Jeffyxuc/overseas-web-prospecting', '', prepared / NAMES[0])
        version = verify_source(prepared / NAMES[0])
        print('[DOWNLOAD] Google Maps Scraper skill', flush=True)
        download('gosom/google-maps-scraper','skills/google-maps-scraper',prepared / NAMES[1])
        roots = [target]
        if not args.skills_dir and not os.environ.get('CODEX_HOME'):
            roots += [Path.home()/'.codex/skills', Path.home()/'.agents/skills']
        backup = install_prepared(prepared, roots, target, state)
    receipt = {'version':version,'skills_dir':str(target),'backup_dir':str(backup),'state_dir':str(state)}
    (state / 'installation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print('[INSTALLED] '+str(target))
    print('Previous copies, if any: '+str(backup))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Download/proxy exceptions can embed credentials; do not echo exception strings.
        raise SystemExit('[INSTALL FAILED] '+type(exc).__name__+'. Existing copies are preserved or restored; check connectivity and installation paths.')
