import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

import youtube_downloader as downloader

ROOT = Path(__file__).resolve().parents[2]


class DownloaderTests(unittest.TestCase):
    def test_valid_request(self):
        self.assertEqual(downloader.parse_request(io.StringIO(json.dumps({
            'url': ' https://youtu.be/example?t=10 ', 'mode': ' Audio '
        }))), ('https://youtu.be/example?t=10', 'audio', 'best'))

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

    def test_resolution_and_audio_options(self):
        notification = downloader.ProgressNotification()
        for resolution in downloader.RESOLUTIONS:
            opts = downloader.options('video', resolution, '/tmp/output', notification)
            cap = '' if resolution == 'best' else f'[height<={resolution}]'
            self.assertEqual(opts['format'], f'bv*{cap}+ba/b{cap}')
            self.assertTrue(opts['noplaylist'])
        opts = downloader.options('audio', '720', '/tmp/output', notification)
        self.assertEqual(opts['format'], 'bestaudio/best')
        self.assertEqual(opts['postprocessors'][0]['preferredcodec'], 'mp3')
        with self.assertRaises(ValueError):
            downloader.parse_request(io.StringIO('{"url":"https://host/video","mode":"video","resolution":"999"}'))

    def run_download(self, home, result):
        request = io.StringIO('{"url":"https://youtu.be/example","mode":"video"}')
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(Path, 'home', return_value=home), patch('sys.stdin', request), \
             patch.object(downloader, 'download', return_value=result) as run, \
             patch.object(downloader.shutil, 'which', return_value=None), \
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
            self.assertEqual(run.call_args.args[0], 'https://youtu.be/example')
            code, output, errors, run = self.run_download(home, 7)
            self.assertEqual(code, 7)
            self.assertNotIn('Saved to:', output)
            self.assertIn('Download failed', errors)

    def test_api_receives_literal_url_and_hooks(self):
        module = MagicMock()
        url = 'https://example.com/watch?v=a&x=$(touch${IFS}/tmp/oops)'
        with patch.dict('sys.modules', {'yt_dlp': module}):
            notification = downloader.ProgressNotification()
            opts = downloader.options('video', '720', '/tmp/output', notification)
            downloader.download(url, opts)
        module.YoutubeDL.assert_called_once_with(opts)
        module.YoutubeDL.return_value.__enter__.return_value.download.assert_called_once_with([url])
        self.assertEqual(opts['progress_hooks'], [notification.progress])

    def test_download_exception_does_not_report_success(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / 'storage/shared').mkdir(parents=True)
            output, errors = io.StringIO(), io.StringIO()
            with patch.object(Path, 'home', return_value=home), \
                 patch('sys.stdin', io.StringIO('{"url":"https://host/video","mode":"video"}')), \
                 patch.object(downloader.shutil, 'which', return_value=None), \
                 patch.object(downloader, 'download', side_effect=RuntimeError('extraction failed')), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(downloader.main(), 1)
            self.assertNotIn('Saved to:', output.getvalue())
            self.assertIn('extraction failed', errors.getvalue())

    def test_exports(self):
        exported = ET.parse(ROOT / 'youtube downloader.tsk.xml').find('Task')
        backup = ET.parse(ROOT / 'main.xml')
        task = next(t for t in backup.findall('Task') if t.findtext('nme') == 'youtube downloader')
        self.assertEqual(ET.tostring(exported).strip(), ET.tostring(task).strip())
        task_id = task.findtext('id')
        project = next(p for p in backup.findall('Project') if p.findtext('name') == 'Test')
        self.assertEqual(project.findtext('tids').split(',').count(task_id), 1)
        actions = task.findall('Action')
        self.assertEqual([a.get('sr') for a in actions], [f'act{i}' for i in range(8)])
        self.assertEqual([a.findtext('code') for a in actions],
                         ['360', '129', '378', '129', '378', '129', '1256900802', '129'])
        self.assertIsNone(actions[0].find('se'))
        self.assertIsNone(actions[2].find('se'))
        self.assertEqual(actions[2].findtext("Str[@sr='arg3']"), 'Video,Audio')
        self.assertEqual(actions[4].findtext('ConditionList/Condition/lhs'), '%yt_mode')
        self.assertEqual(actions[4].findtext('ConditionList/Condition/rhs'), 'video')
        vals = actions[6].find('Bundle/Vals')
        self.assertEqual(vals.findtext('com.termux.tasker.extra.STDIN'), '%yt_request')
        self.assertEqual(vals.findtext('com.termux.execute.arguments'), '<null>')
        self.assertEqual(vals.findtext('com.termux.tasker.extra.WAIT_FOR_RESULT'), 'true')

    def test_progress_throttling_silent_flags_and_completion(self):
        with patch.object(downloader.shutil, 'which', return_value='termux-notification'), \
             patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)) as run, \
             patch.object(downloader.time, 'monotonic', side_effect=[0, 1, 3, 3.1]):
            notification = downloader.ProgressNotification()
            event = {'status': 'downloading', 'downloaded_bytes': 50, 'total_bytes': 100,
                     'speed': 1048576, 'eta': 75}
            notification.progress(event)
            notification.progress(event)
            notification.progress(event)
            self.assertEqual(run.call_count, 2)
            args = run.call_args.args[0]
            self.assertIn('50.0% • 1.00 MiB/s • ETA 1:15', args)
            self.assertIn('--alert-once', args)
            self.assertIn('low', args)
            self.assertNotIn('--sound', args)
            self.assertNotIn('--vibrate', args)
            notification.update('Download complete', force=True)
            self.assertEqual(run.call_count, 3)

    def test_notification_failure_is_nonfatal(self):
        with patch.object(downloader.shutil, 'which', return_value='termux-notification'), \
             patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('notification', 3)) as run:
            notification = downloader.ProgressNotification()
            notification.update('Starting', force=True)
            notification.update('Still downloading', force=True)
            self.assertIsNone(notification.executable)
            self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
