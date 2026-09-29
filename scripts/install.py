#!/usr/bin/env python3
"""Install this package into Codex without replacing an existing skill."""
import argparse
import os
from pathlib import Path
import shutil
import sys

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skills-dir', help='Optional destination skills directory; defaults to CODEX_HOME/skills')
    a = p.parse_args()
    src = Path(__file__).resolve().parent.parent
    root = Path(a.skills_dir).expanduser() if a.skills_dir else Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills'
    root = root.resolve()
    dest = root / 'overseas-web-prospecting'
    if dest.exists():
        raise ValueError('Destination already exists; preserved unchanged. Review versions before replacing it: ' + str(dest))
    if not (src / 'SKILL.md').is_file() or src.name != 'overseas-web-prospecting':
        raise ValueError('Installer must stay inside the complete overseas-web-prospecting package')
    if any(p.is_symlink() for p in src.rglob('*')):
        raise ValueError('Package may not contain symlinks')
    if root.is_relative_to(src):
        raise ValueError('Cannot install into the source package')
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store', '.git'))
    print('Installed: ' + str(dest))
    print('Refresh Codex skills or start a new chat. System dependencies were not installed.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as e:
        print('Error: ' + str(e), file=sys.stderr)
        sys.exit(2)
