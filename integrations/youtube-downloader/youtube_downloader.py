#!/data/data/com.termux/files/usr/bin/python
"""Read a Tasker JSON request from stdin and download one video or audio file."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit


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
        raise ValueError('Enter Video or Audio for the download mode.')
    return url, mode


def command(url, mode, destination):
    args = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist',
            '--no-progress', '-P', str(destination),
            '-o', '%(title).180B [%(id)s].%(ext)s']
    if mode == 'audio':
        args += ['-f', 'bestaudio/best', '--extract-audio', '--audio-format', 'mp3']
    else:
        args += ['-f', 'bv*+ba/b', '--merge-output-format', 'mkv']
    return args + ['--', url]


def main():
    try:
        url, mode = parse_request(sys.stdin)
        storage = Path.home() / 'storage/shared'
        if not storage.is_dir():
            raise ValueError('Run termux-setup-storage and allow storage access first.')
        destination = storage / 'Download/YouTube'
        destination.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(command(url, mode, destination), check=False)
        if result.returncode:
            print('Download failed; see yt-dlp output above.', file=sys.stderr)
            return result.returncode if result.returncode > 0 else 1
        print(f'Saved to: {destination}')
        return 0
    except (ValueError, OSError) as error:
        print(f'Download error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
