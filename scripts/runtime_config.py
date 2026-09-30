#!/usr/bin/env python3
"""Save a local runtime and private proxy files without exposing proxy URLs."""
import argparse
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit, urlunsplit

from check_environment import Runtime, SetupError, run
from install_bundle import codex_home, default_skills_dir


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if os.name != 'nt':
        path.chmod(0o600)


def proxy_urls(value, distro):
    """Return tested-host, container, and download URLs; never return them to stdout."""
    if any(c in value for c in ('\n','\r','"',chr(92))):
        raise SetupError('Unsupported proxy URL characters. Percent-encode credentials.')
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in ('http', 'https') and parsed.hostname and parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise SetupError('Use an HTTP/HTTPS proxy URL with an explicit port in a local file.')
    if bool(parsed.username) != bool(parsed.password):
        raise SetupError('Proxy authentication needs both username and password.')
    test = value
    if not parsed.username:
        # The scraper requires userinfo even for anonymous proxies. Test this adapter first.
        test = urlunsplit(parsed._replace(netloc=secrets.token_hex(8)+':'+secrets.token_hex(16)+'@'+parsed.netloc))
    container = test
    download = value
    loopback = parsed.hostname in ('127.0.0.1', 'localhost', '::1')
    if loopback and not distro:
        def mapped(url):
            p = urlsplit(url)
            auth = p.netloc.rsplit('@',1)[0]+'@' if '@' in p.netloc else ''
            return urlunsplit(p._replace(netloc=auth+'host.docker.internal:'+str(p.port)))
        container, download = mapped(test), mapped(value)
    return test, container, download, loopback and bool(distro)


DAEMON_SCRIPT = '''import json, pathlib, shutil, subprocess, sys, time
source = pathlib.Path(sys.argv[1])
path = pathlib.Path('/etc/docker/daemon.json')
config = json.loads(path.read_text()) if path.exists() else {}
proxies = json.loads(source.read_text())
if config.get('proxies') != proxies:
    active = subprocess.run(['docker','ps','-q'],capture_output=True,text=True)
    if active.returncode or active.stdout.strip():
        sys.exit(21)
    if path.exists():
        backup = path.with_name('daemon.json.before-prospecting-'+str(time.time_ns()))
        shutil.copy2(path,backup)
    path.parent.mkdir(parents=True,exist_ok=True)
    config['proxies'] = proxies
    path.write_text(json.dumps(config,indent=2)+'\\n')
    path.chmod(0o600)
    restarted = subprocess.run(['systemctl','restart','docker'],capture_output=True)
    if restarted.returncode:
        if 'backup' in locals(): shutil.copy2(backup,path)
        else: path.unlink()
        subprocess.run(['systemctl','restart','docker'],capture_output=True)
        sys.exit(22)
'''


def configure(runtime, skills, state, mode='auto', proxy_file=None, engine='desktop', path_prefix=None):
    state = Path(state).resolve()
    profile = state/'runtime.json'
    previous = json.loads(profile.read_text(encoding='utf-8-sig')) if profile.is_file() else {}
    settings = {'schema_version':1,'skills_dir':str(Path(skills).resolve()),'wsl_distro':runtime.distro,
                'engine':engine,'native_path_prefix':path_prefix or [],'language':'en'}
    # Reruns reuse a working local configuration unless the user explicitly changes it.
    if mode == 'auto' and not proxy_file and previous.get('wsl_distro') == runtime.distro and previous.get('engine') == engine:
        for key in ('proxy_file','download_env_file','host_network'):
            if key in previous:
                settings[key] = previous[key]
        if settings.get('proxy_file') and Path(settings['proxy_file']).is_file():
            private_write(profile,json.dumps(settings,indent=2)+'\n')
            print('[CONFIGURED] Reusing saved local network settings.')
            return profile
    runtime.prepare(settings)
    value = ''
    if mode != 'direct':
        if proxy_file:
            values = [v.strip() for v in Path(proxy_file).read_text(encoding='utf-8-sig').splitlines() if v.strip()]
            if len(values) != 1:
                raise SetupError('Supply exactly one proxy URL in the local proxy file.')
            value = values[0]
        else:
            code, out, _ = runtime.command('python3','-c',
                "import os,json; print(json.dumps(next((os.environ[k] for k in ('HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy') if os.environ.get(k)),'')))")
            value = json.loads(out) if code == 0 else ''
            value = value or next((os.environ[k] for k in ('HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy') if os.environ.get(k)), '')
    if value:
        test, container, download, host = proxy_urls(value,runtime.distro)
        curl_config = state/'secrets/proxy-check.conf'
        private_write(curl_config,'proxy = "'+test+'"\nurl = "https://www.google.com/maps"\n')
        try:
            code, status, _ = runtime.command('curl','--config',runtime.path(curl_config),'--silent','--location',
                    '--output','/dev/null','--write-out','%{http_code}','--max-time','40',timeout=50)
        finally:
            curl_config.unlink(missing_ok=True)
        if code or status != '200':
            raise SetupError('Google access through the proxy failed. Check its HTTP port, WSL reachability and anonymous-auth compatibility; rerun with a local proxy file or direct mode.')
        proxy = state/'secrets/proxies.txt'
        env = state/'secrets/download.env'
        private_write(proxy,container+'\n')
        private_write(env,'HTTP_PROXY='+download+'\nHTTPS_PROXY='+download+'\nNO_PROXY=localhost,127.0.0.1\n')
        settings.update(proxy_file=str(proxy),download_env_file=str(env),host_network=host)
        if runtime.distro and engine == 'wsl':
            daemon_file = state/'secrets/daemon-proxy.json'
            private_write(daemon_file,json.dumps({'http-proxy':value,'https-proxy':value,'no-proxy':'localhost,127.0.0.1'}))
            try:
                code, _, _ = run(['wsl.exe','-d',runtime.distro,'-u','root','--exec','python3','-c',DAEMON_SCRIPT,runtime.path(daemon_file)],90)
            finally:
                daemon_file.unlink(missing_ok=True)
            if code:
                raise SetupError('Docker proxy configuration was not applied. Finish existing Docker workloads first; configuration changes never restart active containers. Retry setup afterwards.')
    private_write(profile,json.dumps(settings,indent=2)+'\n')
    print('[CONFIGURED] Local runtime saved; proxy '+('enabled.' if value else 'not configured.'))
    return profile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--skills-dir',type=Path,default=default_skills_dir())
    p.add_argument('--state-dir',type=Path,default=codex_home()/'overseas-web-prospecting')
    p.add_argument('--wsl-distro')
    p.add_argument('--engine',choices=['wsl','desktop'],default='desktop')
    p.add_argument('--network',choices=['auto','direct'],default='auto')
    p.add_argument('--proxy-file',type=Path)
    p.add_argument('--native-path-prefix',action='append',default=[])
    args = p.parse_args()
    if args.network == 'direct' and args.proxy_file:
        raise SetupError('Choose direct mode or a proxy file, not both.')
    runtime = Runtime(args.wsl_distro)
    with runtime.session():
        configure(runtime,args.skills_dir,args.state_dir,args.network,args.proxy_file,args.engine,args.native_path_prefix)


if __name__ == '__main__':
    try:
        main()
    except (SetupError,OSError,ValueError) as exc:
        raise SystemExit('[NEEDS ACTION] '+(str(exc) if isinstance(exc,SetupError) else type(exc).__name__+'. Check local runtime configuration.'))
