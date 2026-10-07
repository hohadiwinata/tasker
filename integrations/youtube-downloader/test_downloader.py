import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import youtube_downloader as downloader

ROOT = Path(__file__).resolve().parents[2]


class DownloaderTests(unittest.TestCase):
    def test_valid_request(self):
        self.assertEqual(downloader.parse_request(io.StringIO(json.dumps({
            'url': ' https://youtu.be/example?t=10 ', 'mode': ' Audio '
        }))), ('https://youtu.be/example?t=10', 'audio'))

    def test_invalid_requests(self):
        for request in [[], {}, {'url': 42, 'mode': 'audio'},
                        {'url': 'file:///tmp/video', 'mode': 'video'},
                        {'url': 'https://', 'mode': 'video'},
                        {'url': 'https://host/a\nb', 'mode': 'video'},
                        {'url': 'https://host/video', 'mode': 'other'}]:
            with self.subTest(request=request), self.assertRaises(ValueError):
                downloader.parse_request(io.StringIO(json.dumps(request)))
        with self.assertRaises(ValueError):
            downloader.parse_request(io.StringIO('not json'))

    def test_modes_and_literal_url(self):
        url = 'https://example.com/watch?v=a&x=$(touch${IFS}/tmp/oops)'
        for mode in ('audio', 'video'):
            args = downloader.command(url, mode, Path('/tmp/output with spaces'))
            self.assertEqual(args[-2:], ['--', url])
            self.assertIn('--no-playlist', args)
            self.assertIn('--ignore-config', args)
            self.assertEqual('--extract-audio' in args, mode == 'audio')
            self.assertEqual('--merge-output-format' in args, mode == 'video')

    def run_download(self, home, result):
        request = io.StringIO('{"url":"https://youtu.be/example","mode":"video"}')
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(Path, 'home', return_value=home), patch('sys.stdin', request), \
             patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], result)) as run, \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = downloader.main()
        return code, output.getvalue(), errors.getvalue(), run

    def test_success_failure_and_missing_storage(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            code, output, errors, run = self.run_download(home, 0)
            self.assertEqual(code, 1)
            run.assert_not_called()
            self.assertIn('termux-setup-storage', errors)
            (home / 'storage/shared').mkdir(parents=True)
            code, output, errors, run = self.run_download(home, 0)
            self.assertEqual(code, 0)
            self.assertIn('Saved to:', output)
            self.assertEqual(run.call_args.kwargs, {'check': False})
            code, output, errors, run = self.run_download(home, 7)
            self.assertEqual(code, 7)
            self.assertNotIn('Saved to:', output)
            self.assertIn('Download failed', errors)

    def test_exports(self):
        exported = ET.parse(ROOT / 'youtube downloader.tsk.xml').find('Task')
        backup = ET.parse(ROOT / 'main.xml')
        task = next(t for t in backup.findall('Task') if t.findtext('nme') == 'youtube downloader')
        self.assertEqual(ET.tostring(exported).strip(), ET.tostring(task).strip())
        task_id = task.findtext('id')
        project = next(p for p in backup.findall('Project') if p.findtext('name') == 'Test')
        self.assertEqual(project.findtext('tids').split(',').count(task_id), 1)
        actions = task.findall('Action')
        self.assertEqual([a.get('sr') for a in actions], [f'act{i}' for i in range(6)])
        self.assertEqual([a.findtext('code') for a in actions],
                         ['360', '129', '360', '129', '1256900802', '129'])
        self.assertIsNone(actions[0].find('se'))
        self.assertIsNone(actions[2].find('se'))
        vals = actions[4].find('Bundle/Vals')
        self.assertEqual(vals.findtext('com.termux.tasker.extra.STDIN'), '%yt_request')
        self.assertEqual(vals.findtext('com.termux.execute.arguments'), '<null>')
        self.assertEqual(vals.findtext('com.termux.tasker.extra.WAIT_FOR_RESULT'), 'true')


if __name__ == '__main__':
    unittest.main()
