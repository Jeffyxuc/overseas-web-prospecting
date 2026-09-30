#!/usr/bin/env python3
"""Run an actual crawl using the user's saved runtime profile; never print proxy data."""
import argparse
import csv
import io
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid

from check_environment import Runtime, SetupError


def profile_path():
    return Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))) / 'overseas-web-prospecting/runtime.json'


def build_command(runtime, query, output, name, settings, format='csv', extra_reviews=False, depth=1):
    if extra_reviews and format != 'json':
        raise SetupError('Extra reviews require JSON output.')
    args = ['docker','run','-d','--name',name,'--label','overseas-prospecting=1',
            '-v','gmaps-playwright-cache:/opt','-v',runtime.path(query)+':/queries.txt:ro',
            '-v',runtime.path(output)+':/out']
    if settings.get('host_network'):
        if not runtime.distro:
            raise SetupError('Automatic host networking is supported only for the WSL runtime.')
        args += ['--network','host']
    if settings.get('download_env_file'):
        args += ['--env-file',runtime.path(settings['download_env_file'])]
    proxy = settings.get('proxy_file')
    if proxy:
        args += ['-v',runtime.path(proxy)+':/run/secrets/gmaps-proxies:ro']
    args += ['gosom/google-maps-scraper','-input','/queries.txt','-results','/out/results.'+format,
             '-depth',str(depth),'-lang',settings.get('language','en'),'-c','1','-exit-on-inactivity','3m']
    if format == 'json':
        args += ['-json']
    if extra_reviews:
        args += ['-extra-reviews']
    if proxy:
        args += ['-proxies-file','/run/secrets/gmaps-proxies']
    return args


def execute(runtime, output, query_text, settings, format='csv', extra_reviews=False, depth=1, timeout=600, poll_seconds=5):
    if not query_text.strip() or '\n' in query_text or '\r' in query_text:
        raise SetupError('Provide one nonempty query per crawl.')
    if extra_reviews and format != 'json':
        raise SetupError('Extra reviews require JSON output.')
    code, status, _ = runtime.command('docker','inspect','--format','{{.State.Status}}','gmaps-scraper-agent')
    if code == 0 and status in ('running','created','restarting','paused'):
        raise SetupError('An existing scraper container may belong to another task. Finish it first.')
    code, active, _ = runtime.command('docker','ps','-q','--filter','label=overseas-prospecting=1')
    if code or active:
        raise SetupError('Another prospecting crawl is active, or Docker is unavailable. Inspect it before retrying.')
    output = Path(output).resolve()
    result = output / ('results.'+format)
    if result.exists() or (output/'crawl.json').exists():
        raise SetupError('Output already exists. Choose a new directory to preserve previous results.')
    output.mkdir(parents=True, exist_ok=True)
    query = output/'queries.txt'
    query.write_text(query_text+'\n',encoding='utf-8',newline='\n')
    name = 'prospecting-' + uuid.uuid4().hex[:16]
    record = {'status':'starting','query':query_text,'started_at':datetime.now(timezone.utc).isoformat(),
              'container_name':name,'results_path':str(result),'format':format,'extra_reviews':extra_reviews,
              'depth':depth,'concurrency':1,'proxy_configured':bool(settings.get('proxy_file')),
              'host_network':bool(settings.get('host_network')),'wsl_distro':runtime.distro}
    def save():
        (output/'crawl.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    try:
        code, container, _ = runtime.command(*build_command(runtime,query,output,name,settings,format,extra_reviews,depth),timeout=90)
        if code or not container:
            raise SetupError('Container startup failed. Check mounts, runtime profile and image; proxy data is not logged.')
        record.update(status='running',container_id=container)
        save()
        deadline = time.monotonic()+timeout
        while time.monotonic() < deadline:
            code, raw, _ = runtime.command('docker','inspect','--format','{{json .State}}',container)
            if code:
                raise SetupError('The started container can no longer be inspected.')
            state = json.loads(raw)
            if state.get('Status') == 'exited':
                record.update(exit_code=state.get('ExitCode'),finished_at=state.get('FinishedAt'))
                if state.get('ExitCode') != 0:
                    raise SetupError('Crawl exited with an error. Partial results are preserved; inspect sanitized diagnostics.')
                if not result.is_file() or result.stat().st_size == 0:
                    raise SetupError('Crawl exited without data. Check Google access and proxy compatibility.')
                content = result.read_text(encoding='utf-8-sig')
                if format == 'csv':
                    rows = list(csv.DictReader(io.StringIO(content)))
                else:
                    try:
                        rows = json.loads(content)
                        if isinstance(rows, dict):
                            rows = rows.get('results', [rows])
                    except ValueError:
                        rows = [json.loads(line) for line in content.splitlines() if line.strip()]
                if not isinstance(rows,list) or not any(isinstance(r,dict) and (r.get('title') or r.get('name')) for r in rows):
                    raise SetupError('No named business was returned. A header or empty JSON is not a successful crawl.')
                record['business_count'] = len(rows)
                record['status'] = 'completed'
                save()
                return record
            if state.get('Status') in ('dead','removing'):
                raise SetupError('Container stopped unexpectedly.')
            if not record.get('last_progress') or time.monotonic()-record['last_progress'] >= 30:
                print('[WAIT] Crawl running; results are not yet verified.',flush=True)
                record['last_progress'] = time.monotonic()
            time.sleep(poll_seconds)
        raise SetupError('Crawl timed out. Container and partial files are preserved; inspect them before retrying.')
    except (SetupError, OSError, ValueError, KeyboardInterrupt) as exc:
        record['status'] = 'incomplete'
        save()
        if isinstance(exc, SetupError):
            raise
        raise SetupError('Crawl interrupted or returned unreadable data. Partial files are preserved.') from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,default=profile_path())
    p.add_argument('--query',required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--format',choices=['csv','json'],default='csv')
    p.add_argument('--extra-reviews',action='store_true')
    p.add_argument('--depth',type=int,choices=range(1,6),default=1)
    p.add_argument('--timeout',type=int,default=600)
    args = p.parse_args()
    if not args.profile.is_file():
        raise SetupError('No runtime profile. Run the environment installer first.')
    settings = json.loads(args.profile.read_text(encoding='utf-8-sig'))
    runtime = Runtime(settings.get('wsl_distro'))
    with runtime.session():
        runtime.prepare(settings)
        record = execute(runtime,args.output_dir,args.query,settings,args.format,args.extra_reviews,args.depth,args.timeout)
    print('[COMPLETED] '+record['results_path'])


if __name__ == '__main__':
    try:
        main()
    except (SetupError,OSError,ValueError) as exc:
        raise SystemExit('[INCOMPLETE] '+(str(exc) if isinstance(exc,SetupError) else type(exc).__name__))
