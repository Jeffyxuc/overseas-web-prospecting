"""Offline regression tests for portable installs, saved settings and crawl failures."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import zipfile

import check_environment as env
import install_bundle as bundle
import run_maps as maps
import runtime_config as config


class InstallRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, entries):
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w') as z:
            for name, content in entries.items():
                z.writestr('repo-main/'+name, content)
        return out.getvalue()

    def test_zip_install_preserves_bash_lf(self):
        bundle.unpack_skill(self.archive({'SKILL.md':'x','scripts/run.sh':b'#!/bin/bash\necho ok\n'}),'',self.root)
        self.assertEqual((self.root/'scripts/run.sh').read_bytes(),b'#!/bin/bash\necho ok\n')

    def test_zip_traversal_and_symlinks_rejected(self):
        for name in ('../escape','C:/escape','scripts/../../escape'):
            with self.assertRaises(ValueError):
                bundle.unpack_skill(self.archive({'SKILL.md':'x',name:'bad'}),'',self.root)
        # ZipFile normalizes backslashes on Windows while writing; emulate an external ZIP.
        malformed = self.archive({'SKILL.md':'x','scripts/escape':'bad'}).replace(b'scripts/escape',b'scripts\\escape')
        with self.assertRaises(ValueError):
            bundle.unpack_skill(malformed,'',self.root)
        out = io.BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            member = zipfile.ZipInfo('repo-main/link')
            member.external_attr = 0o120777 << 16
            z.writestr(member, '../outside')
        with self.assertRaises(ValueError):
            bundle.unpack_skill(out.getvalue(),'',self.root)

    def prepared(self):
        prepared = self.root/'prepared'
        for name in bundle.NAMES:
            (prepared/name).mkdir(parents=True)
            (prepared/name/'SKILL.md').write_text('new')
        return prepared

    def test_duplicate_copies_backed_up_and_one_active_install(self):
        prepared = self.prepared()
        roots = [self.root/'codex', self.root/'agents']
        for root in roots:
            for name in bundle.NAMES:
                (root/name).mkdir(parents=True)
                (root/name/'SKILL.md').write_text('old')
        backup = bundle.install_prepared(prepared,roots,roots[1],self.root/'state')
        self.assertEqual(len(list(backup.rglob('SKILL.md'))),4)
        self.assertFalse((roots[0]/bundle.NAMES[0]).exists())
        self.assertEqual((roots[1]/bundle.NAMES[0]/'SKILL.md').read_text(),'new')

    def test_copy_failure_rolls_back_previous_install(self):
        prepared = self.prepared()
        target = self.root/'skills'
        for name in bundle.NAMES:
            (target/name).mkdir(parents=True)
            (target/name/'SKILL.md').write_text('old')
        real_copy = bundle.shutil.copytree
        def failing(src,dest,**kwargs):
            if src.name == bundle.NAMES[1]:
                raise OSError('simulated disk failure')
            return real_copy(src,dest,**kwargs)
        with patch.object(bundle.shutil,'copytree',side_effect=failing):
            with self.assertRaises(OSError):
                bundle.install_prepared(prepared,[target],target,self.root/'state')
        for name in bundle.NAMES:
            self.assertEqual((target/name/'SKILL.md').read_text(),'old')

    def test_custom_codex_home_and_agents_detection(self):
        with patch.dict(os.environ,{'CODEX_HOME':str(self.root/'custom')}):
            self.assertEqual(bundle.default_skills_dir(),self.root/'custom/skills')
            self.assertEqual(maps.profile_path(),self.root/'custom/overseas-web-prospecting/runtime.json')
        with patch.dict(os.environ,{},clear=True), patch.object(Path,'home',return_value=self.root):
            skill = self.root/'.agents/skills/overseas-web-prospecting'
            skill.mkdir(parents=True)
            (skill/'SKILL.md').touch()
            self.assertEqual(bundle.default_skills_dir(),skill.parent)

    def test_mac_loopback_mapping_and_wsl_host_network(self):
        for distro in (None,'Ubuntu'):
            test, container, download, host = config.proxy_urls('http://localhost:12345',distro)
            self.assertIn('@localhost:12345',test)
            self.assertEqual(host,bool(distro))
            self.assertIn('localhost' if distro else 'host.docker.internal',container)
            self.assertNotIn('@',download)

    def test_bad_proxy_urls_fail_before_commands(self):
        for value in ('file:///etc/passwd','http://localhost','http://user@localhost:12345','http://localhost:12345\nsecret'):
            with self.assertRaises(env.SetupError):
                config.proxy_urls(value,'Ubuntu')

    def test_proxy_values_never_in_container_command(self):
        runtime = env.Runtime()
        runtime.path = lambda p: str(p)
        args = maps.build_command(runtime,self.root/'q',self.root/'out','test',
                {'proxy_file':str(self.root/'secret.txt'),'download_env_file':str(self.root/'download.env')})
        self.assertIn('--env-file',args)
        self.assertIn('-proxies-file',args)
        self.assertFalse(any('http://' in a or 'https://' in a for a in args))

    def test_wsl_session_holds_client_until_exit(self):
        process = Mock()
        with patch.object(env.subprocess,'Popen',return_value=process) as popen:
            with env.Runtime('Ubuntu').session():
                popen.assert_called_once()
                process.stdin.close.assert_not_called()
            process.stdin.close.assert_called_once()
            process.wait.assert_called_once()

    def test_saved_proxy_reused_without_network_reconfiguration(self):
        proxy = self.root/'proxy.txt'
        proxy.write_text('private fixture')
        (self.root/'runtime.json').write_text(json.dumps({'wsl_distro':'Ubuntu','engine':'wsl','proxy_file':str(proxy)}))
        runtime = Mock(distro='Ubuntu')
        config.configure(runtime,self.root/'skills',self.root,engine='wsl')
        runtime.prepare.assert_not_called()
        runtime.command.assert_not_called()

    def test_direct_mode_does_not_reuse_old_proxy(self):
        (self.root/'runtime.json').write_text(json.dumps({'proxy_file':'old','wsl_distro':'Ubuntu','engine':'wsl'}))
        runtime = Mock(distro='Ubuntu')
        config.configure(runtime,self.root/'skills',self.root,mode='direct',engine='wsl')
        saved = json.loads((self.root/'runtime.json').read_text())
        self.assertNotIn('proxy_file',saved)
        runtime.command.assert_not_called()

    def fake_crawl(self, content, exit_code=0):
        output = self.root/'crawl'
        def command(*args,**kwargs):
            if args[:2] == ('docker','inspect') and args[-1] == 'gmaps-scraper-agent':
                return 1,'',''
            if args[:2] == ('docker','ps'):
                return 0,'',''
            if args[:2] == ('docker','run'):
                (output/'results.csv').write_text(content)
                return 0,'container-id',''
            return 0,json.dumps({'Status':'exited','ExitCode':exit_code}),'secret error never printed'
        runtime = Mock(distro=None)
        runtime.path = str
        runtime.command.side_effect = command
        return runtime, output

    def test_header_only_crawl_is_incomplete(self):
        runtime,output = self.fake_crawl('title,review_rating,review_count\n')
        with self.assertRaisesRegex(env.SetupError,'No named business'):
            maps.execute(runtime,output,'test query',{},poll_seconds=0)
        self.assertEqual(json.loads((output/'crawl.json').read_text())['status'],'incomplete')

    def test_nonzero_exit_cannot_accept_partial_results(self):
        runtime,output = self.fake_crawl('title\nExample\n',1)
        with self.assertRaisesRegex(env.SetupError,'exited with an error'):
            maps.execute(runtime,output,'test query',{},poll_seconds=0)
        self.assertTrue((output/'results.csv').is_file())

    def test_successful_crawl_preserves_evidence(self):
        runtime,output = self.fake_crawl('title,review_rating,review_count\nExample,4.5,25\n')
        result = maps.execute(runtime,output,'test query',{},poll_seconds=0)
        self.assertEqual(result['business_count'],1)
        self.assertEqual(result['status'],'completed')
        with self.assertRaisesRegex(env.SetupError,'Output already exists'):
            maps.execute(runtime,output,'test query',{})


if __name__ == '__main__':
    unittest.main()
