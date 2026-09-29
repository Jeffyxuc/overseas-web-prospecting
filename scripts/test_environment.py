"""No installations, network calls, or real containers; verify readiness boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import check_environment as env


class FakeRuntime:
    distro = 'Ubuntu'

    def __init__(self, docker=True):
        self.docker = docker
        self.calls = []

    def command(self, *args, timeout=30):
        self.calls.append(args)
        if args[:2] == ('docker', 'info'):
            return (0, 'linux', '') if self.docker else (1, '', 'unavailable')
        return 0, 'tool version', ''

    def path(self, value):
        return str(value)


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / 'skills'
        for name in ('overseas-web-prospecting', 'google-maps-scraper'):
            skill = self.skills / name
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('test fixture')
        scripts = self.skills / 'google-maps-scraper' / 'scripts'
        scripts.mkdir()
        (scripts / 'run-local.sh').touch()
        self.reports = self.root / 'reports'

    def test_dependencies_only_cannot_claim_crawl_ready(self):
        result = env.check(FakeRuntime(), self.skills, self.reports)
        self.assertEqual(result['status'], 'dependencies_ok_crawl_unverified')
        self.assertEqual(result['crawl']['status'], 'not_run')

    def test_missing_daemon_prevents_crawl(self):
        with patch.object(env, 'crawl') as crawl:
            result = env.check(FakeRuntime(False), self.skills, self.reports, True)
        crawl.assert_not_called()
        self.assertEqual(result['status'], 'needs_action')
        self.assertIn('Ubuntu', result['next_action'])

    def test_failed_crawl_replaces_previous_success_report(self):
        with patch.object(env, 'crawl', return_value={'business_count': 2}):
            self.assertEqual(env.check(FakeRuntime(), self.skills, self.reports, True)['status'], 'ready')
        with patch.object(env, 'crawl', side_effect=env.SetupError('No data')):
            env.check(FakeRuntime(), self.skills, self.reports, True)
        saved = json.loads((self.reports / 'environment-report.json').read_text())
        self.assertEqual(saved['status'], 'needs_action')
        self.assertEqual(saved['crawl']['status'], 'failed_or_incomplete')

    def test_csv_requires_real_rows_and_ratings(self):
        csv = self.root / 'results.csv'
        for content in ('title,link,review_rating,review_count\n', 'title,link,review_rating,review_count\nSample,https://example.com,,,\n'):
            csv.write_text(content)
            with self.assertRaises(env.SetupError):
                env.validate_results(csv)
        csv.write_text('title,link,review_rating,review_count\n"Sample\nBakery",https://www.google.com/maps?cid=1,4.5,12\n')
        self.assertEqual(env.validate_results(csv)['businesses_with_rating_and_count'], 1)

    def test_busy_container_is_not_replaced(self):
        runtime = FakeRuntime()
        runtime.command = lambda *args, **kw: (0, 'running', '')
        with self.assertRaisesRegex(env.SetupError, 'another task'):
            env.crawl(runtime, self.skills, self.reports)
        self.assertFalse(self.reports.exists())

    def test_timeout_keeps_container_and_does_not_claim_success(self):
        runtime = FakeRuntime()
        responses = iter([(1, '', ''), (0, '', ''), (0, 'id', ''), (0, 'unique-container-id', '')])
        def command(*args, **kwargs):
            runtime.calls.append(args)
            return next(responses)
        runtime.command = command
        self.reports.mkdir()
        with self.assertRaisesRegex(env.SetupError, 'timed out'):
            env.crawl(runtime, self.skills, self.reports, timeout=0)
        self.assertFalse(any(call[:2] in (('docker', 'stop'), ('docker', 'rm')) for call in runtime.calls))

    def test_rejects_internal_docker_distribution(self):
        with self.assertRaises(env.SetupError):
            env.Runtime('docker-desktop')

    def test_missing_upstream_entrypoint_does_not_claim_ready(self):
        (self.skills / 'google-maps-scraper' / 'scripts' / 'run-local.sh').unlink()
        result = env.check(FakeRuntime(), self.skills, self.reports)
        self.assertEqual(result['status'], 'needs_action')


if __name__ == '__main__':
    unittest.main()
