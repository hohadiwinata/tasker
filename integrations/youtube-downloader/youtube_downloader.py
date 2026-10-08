#!/data/data/com.termux/files/usr/bin/python
"""Read a Tasker JSON request and download media with silent progress updates."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit

RESOLUTIONS = ('best', '2160', '1440', '1080', '720', '480', '360')


def parse_request(stream):
    request = json.load(stream)
    if not isinstance(request, dict):
        raise ValueError('Expected a JSON object containing url and mode.')
    url, mode = request.get('url'), request.get('mode')
    if not isinstance(url, str) or not isinstance(mode, str):
        raise ValueError('URL and mode must be text.')
    url, mode = url.strip(), mode.strip().lower()
    parsed = urlsplit(url)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname
            or any(c.isspace() or ord(c) < 32 for c in url)):
        raise ValueError('Enter a complete HTTP or HTTPS URL without whitespace.')
    if mode not in ('video', 'audio'):
        raise ValueError('Select Video or Audio for the download mode.')
    resolution = str(request.get('resolution', 'best'))
    if resolution not in RESOLUTIONS:
        raise ValueError('Unsupported resolution.')
    return url, mode, resolution


class ProgressNotification:
    """Replace a single low-priority notification, at most once every two seconds."""
    def __init__(self):
        self.executable = shutil.which('termux-notification')
        self.last_update = float('-inf')
        if not self.executable:
            print('Progress notifications unavailable: install Termux:API and termux-api.', file=sys.stderr)

    def update(self, content, force=False):
        now = time.monotonic()
        if not self.executable or (not force and now - self.last_update < 2):
            return
        self.last_update = now
        try:
            result = subprocess.run([
                self.executable, '--id', 'youtube-downloader',
                '--title', 'YouTube downloader', '--content', content,
                '--priority', 'low', '--alert-once',
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, check=False)
            if result.returncode:
                self.disable()
        except (OSError, subprocess.TimeoutExpired):
            self.disable()

    def disable(self):
        print('Progress notifications unavailable. Check Termux:API and notification permissions.', file=sys.stderr)
        self.executable = None

    def progress(self, data):
        if data.get('status') == 'finished':
            self.update('Stream downloaded; merging or converting...', force=True)
            return
        if data.get('status') != 'downloading':
            return
        total = data.get('total_bytes') or data.get('total_bytes_estimate')
        downloaded = data.get('downloaded_bytes', 0)
        percent = f'{min(100, downloaded / total * 100):.1f}%' if total else 'Downloading'
        speed, eta = data.get('speed'), data.get('eta')
        parts = [percent]
        if speed is not None:
            parts.append(f'{speed / 1024 / 1024:.2f} MiB/s')
        if eta is not None:
            minutes, seconds = divmod(int(eta), 60)
            parts.append(f'ETA {minutes}:{seconds:02d}')
        self.update(' • '.join(parts))

    def postprocess(self, data):
        if data.get('status') == 'started':
            self.update('Processing downloaded media...', force=True)


def options(mode, resolution, destination, notification):
    opts = {
        'noplaylist': True,
        'noprogress': True,
        'paths': {'home': str(destination)},
        'outtmpl': '%(title).180B [%(id)s].%(ext)s',
        'progress_hooks': [notification.progress],
        'postprocessor_hooks': [notification.postprocess],
    }
    if mode == 'audio':
        opts.update(format='bestaudio/best', postprocessors=[{
            'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3',
        }])
    else:
        cap = '' if resolution == 'best' else f'[height<={resolution}]'
        opts.update(format=f'bv*{cap}+ba/b{cap}', merge_output_format='mkv')
    return opts


def download(url, opts):
    import yt_dlp
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.download([url])


def main():
    notification = ProgressNotification()
    try:
        url, mode, resolution = parse_request(sys.stdin)
        storage = Path.home() / 'storage/shared'
        if not storage.is_dir():
            raise ValueError('Run termux-setup-storage and allow storage access first.')
        destination = storage / 'Download/YouTube'
        destination.mkdir(parents=True, exist_ok=True)
        notification.update('Starting download...', force=True)
        result = download(url, options(mode, resolution, destination, notification))
        if result:
            notification.update('Download failed. Check Tasker or Termux output.', force=True)
            print('Download failed; see yt-dlp output above.', file=sys.stderr)
            return result if result > 0 else 1
        notification.update('Download complete: Download/YouTube', force=True)
        print(f'Saved to: {destination}')
        return 0
    except Exception as error:
        # yt-dlp also raises DownloadError on extraction/network/postprocessing failure.
        notification.update('Download failed. Check Tasker or Termux output.', force=True)
        print(f'Download error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
