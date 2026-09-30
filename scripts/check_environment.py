#!/usr/bin/env python3
"""Check one coherent runtime; optionally run a bounded, real upstream crawl."""
from __future__ import annotations
import argparse
from contextlib import contextmanager, nullcontext
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse


class SetupError(Exception):
    pass


def run(args, timeout=30):
    try:
        result = subprocess.run(args, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError(f"Could not complete {args[0]}: {type(exc).__name__}") from exc
    # wsl --list uses UTF-16; ordinary WSL command output is UTF-8.
    def decode(data):
        return data.decode('utf-16-le' if b'\0' in data else 'utf-8', errors='replace').strip()
    return result.returncode, decode(result.stdout), decode(result.stderr)


class Runtime:
    def __init__(self, distro=None):
        if distro == 'docker-desktop':
            raise SetupError('Select a user WSL distribution, not docker-desktop.')
        self.distro = distro
        self.settings = {}

    @contextmanager
    def session(self):
        """An open stdin keeps a WSL client alive, including between Docker polls."""
        holder = None
        if self.distro:
            holder = subprocess.Popen(['wsl.exe','-d',self.distro,'--exec','sh','-c','read -r keepalive'],
                                      stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            yield self
        finally:
            if holder:
                try:
                    holder.stdin.close()
                    holder.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    holder.terminate()
                    holder.wait(timeout=5)

    def prepare(self, settings):
        self.settings = settings
        if not self.distro:
            os.environ['PATH'] = os.pathsep.join(settings.get('native_path_prefix',[])+[os.environ.get('PATH','')])
        if self.distro and settings.get('engine') == 'wsl':
            code, _, _ = run(['wsl.exe','-d',self.distro,'-u','root','--exec','systemctl','start','docker'],60)
            if code:
                raise SetupError('Could not start the WSL Docker service. Rerun environment setup.')

    def command(self, *args, timeout=30):
        prefix = ['wsl.exe', '-d', self.distro, '--exec'] if self.distro else []
        return run(prefix + list(args), timeout)

    def path(self, value):
        value = str(Path(value).resolve())
        if not self.distro:
            return value
        code, out, _ = self.command('wslpath', '-a', '-u', value)
        if code or not out.startswith('/') or '\n' in out:
            raise SetupError('Could not translate the Windows path into the selected WSL distribution.')
        return out


def validate_results(path):
    """An exited container or a CSV header alone is not proof of a usable crawl."""
    try:
        rows = list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8-sig'))))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise SetupError('The crawl did not produce a readable result file.') from exc
    named = [r for r in rows if (r.get('title') or r.get('name') or '').strip()]
    rated = []
    for row in named:
        try:
            rating = float(row.get('review_rating') or row.get('rating') or '')
            count = int(row.get('review_count') or '')
            link = urlparse(row.get('link') or row.get('maps_url') or '')
            if 1 <= rating <= 5 and count > 0 and link.scheme == 'https' and link.hostname in ('google.com', 'www.google.com', 'maps.google.com'):
                rated.append(row)
        except (ValueError, TypeError):
            pass
    if not named or not rated:
        raise SetupError('No business with a map link, rating and review count was returned. Crawl readiness is unverified.')
    return {'business_count': len(named), 'businesses_with_rating_and_count': len(rated)}


def crawl(runtime, skills, report_dir, timeout=600, poll_seconds=5):
    from run_maps import execute
    settings = getattr(runtime, 'settings', {})
    print('[TEST] Checking/downloading the scraper image.', flush=True)
    code, _, _ = runtime.command('docker', 'pull', 'gosom/google-maps-scraper', timeout=600)
    if code:
        raise SetupError('Image download failed. Configure the Docker daemon proxy separately from the crawl proxy; rerun setup.')
    crawl_dir = report_dir / ('smoke-' + uuid.uuid4().hex)
    record = execute(runtime, crawl_dir, 'bakeries in Sydney Australia', settings, timeout=timeout, poll_seconds=poll_seconds)
    return {**record, **validate_results(Path(record['results_path']))}


def check(runtime, skills, report_dir, smoke_test=False):
    with runtime.session() if hasattr(runtime, 'session') else nullcontext():
        return _check(runtime, skills, report_dir, smoke_test)


def _check(runtime, skills, report_dir, smoke_test=False):
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'wsl_distro': runtime.distro,
              'status': 'checking', 'checks': [], 'crawl': {'status': 'not_run'}, 'runtime_profile_configured': bool(getattr(runtime,'settings',{}))}
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / 'environment-report.json'
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    try:
        if hasattr(runtime, 'prepare'):
            runtime.prepare(getattr(runtime, 'settings', {}))
        for name in ('overseas-web-prospecting', 'google-maps-scraper'):
            if not (skills / name / 'SKILL.md').is_file():
                raise SetupError(f'Missing skill: {name}. Run the installer first.')
        helper = skills / 'google-maps-scraper' / 'scripts' / 'run-local.sh'
        if not helper.is_file():
            raise SetupError('The installed scraper has no supported run-local.sh entry point; inspect its current instructions.')
        checks = [('bash', '--version'), ('node', '--version'), ('python3', '--version'),
                  ('docker', 'info', '--format', '{{.OSType}}')]
        for args in checks:
            code, out, _ = runtime.command(*args)
            if code:
                hint = ('Start Docker, finish first-run prompts and enable WSL 2 integration for ' + runtime.distro
                        if runtime.distro else 'Start Docker and finish its first-run prompts.')
                raise SetupError(f'{args[0]} is not usable in the chosen runtime. ' + (hint if args[0] == 'docker' else 'Run environment setup again.'))
            if args[0] == 'docker' and out != 'linux':
                raise SetupError('The scraper needs a Linux Docker engine. Switch Docker to Linux containers.')
            report['checks'].append({'tool': args[0], 'ok': True, 'value': out.splitlines()[0] if out else ''})
            print(f'[OK] {args[0]} in the selected runtime', flush=True)
        # Import core code with the same interpreter that will be used during workflow execution.
        code, _, _ = runtime.command('python3', '-c', 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)')
        if code:
            raise SetupError('The selected runtime needs Python 3.10 or newer.')
        if smoke_test:
            report['crawl'] = {'status': 'running'}
            report['crawl'] = {**crawl(runtime, skills, report_dir), 'status': 'passed'}
            report['status'] = 'ready'
        else:
            report['status'] = 'dependencies_ok_crawl_unverified'
    except (SetupError, OSError, KeyboardInterrupt) as exc:
        report['status'] = 'needs_action'
        report['next_action'] = str(exc) or 'Interrupted. Check the validation container before rerunning.'
        if report['crawl']['status'] == 'running':
            report['crawl']['status'] = 'failed_or_incomplete'
    report_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if report['status'] == 'ready':
        print('[READY] A real business with map rating and review count was obtained. Refresh Codex skills to begin.')
    elif report['status'] == 'needs_action':
        print('[NEEDS ACTION] ' + report['next_action'])
    else:
        print('[CHECKED] Dependencies are available. Google Maps crawling has NOT been tested.')
    print('Report: ' + str(path))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wsl-distro')
    parser.add_argument('--skills-dir', type=Path)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--smoke-test', action='store_true', help='Download the image and perform one real public query.')
    args = parser.parse_args()
    from run_maps import profile_path
    from install_bundle import default_skills_dir
    selected = args.profile or profile_path()
    settings = json.loads(selected.read_text(encoding='utf-8-sig')) if selected.is_file() else {}
    runtime = Runtime(args.wsl_distro or settings.get('wsl_distro'))
    runtime.settings = settings
    skills = args.skills_dir or Path(settings.get('skills_dir', default_skills_dir()))
    report = check(runtime, skills.resolve(), args.report_dir.resolve(), args.smoke_test)
    return 2 if report['status'] == 'needs_action' else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (SetupError, OSError, ValueError, KeyboardInterrupt) as exc:
        print('[INCOMPLETE] ' + (str(exc) if isinstance(exc, SetupError) else type(exc).__name__+'. Check local files; no successful validation recorded.'), file=sys.stderr)
        sys.exit(2)
