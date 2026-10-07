# YouTube downloader for Test

The **youtube downloader** task prompts for a URL, then asks you to enter **Video**
(default) or **Audio**. It runs [yt-dlp](https://github.com/yt-dlp/yt-dlp) through
[Termux:Tasker](https://github.com/termux/termux-tasker) in the background and reports
completion or failure. Files go to **Internal storage/Download/YouTube**. Audio is
converted to MP3; video keeps the source quality and merges separate streams into
MKV when needed (already combined streams retain their source container).
A video URL containing a playlist downloads only that video.

## Install on your phone

1. Install Termux and Termux:Tasker from compatible sources, such as F-Droid.
   Open Termux once. Grant Tasker Android's **Run commands in Termux environment**
   permission if it appears in App permissions (it may be under Additional permissions).
2. Run in Termux:

   ```sh
   pkg update
   pkg install python ffmpeg deno
   python -m pip install -U 'yt-dlp[default]'
   termux-setup-storage
   mkdir -p ~/.termux/tasker
   ```

   Accept the storage permission prompt. Deno and the yt-dlp default extras support
   YouTube's JavaScript challenges. Update yt-dlp with the same pip command when
   YouTube changes break extraction.
3. In `~/.termux/termux.properties`, set `allow-external-apps=true` (edit an existing
   entry if present). Run `termux-reload-settings`.
4. Download this folder's `youtube_downloader.py` into your phone's Download folder,
   then run:

   ```sh
   cp ~/storage/downloads/youtube_downloader.py ~/.termux/tasker/
   chmod 700 ~/.termux/tasker/youtube_downloader.py
   ```

5. Download [`youtube downloader.tsk.xml`](../../youtube%20downloader.tsk.xml).
   In Tasker, select the existing **Test** project. Long-press the **Tasks** tab,
   choose **Import Task**, and select the XML. If a task with that name already
   exists, rename the old one first. The new task should have **six actions**.
   The repository's `main.xml` also contains this task in Test; standalone import
   avoids replacing the phone's entire configuration with a backup restore.
6. Run **youtube downloader**, paste a video URL, and enter Video or Audio.
   Cancelling or timing out either input dialog stops the task. Each dialog has a
   120-second timeout. Invalid input stops with an error.

## Termux:Tasker configuration

The imported fifth action uses these settings:

- Executable: `youtube_downloader.py`
- Arguments: empty
- Stdin: `%yt_request`
- Execute in terminal session: off
- Wait for result: on
- Tasker plugin timeout: 3600 seconds
- Continue task after error: on, so the final action can report failure

The preceding JavaScriptlet builds JSON containing `url` and `mode`. The script
reads that JSON from stdin and launches yt-dlp with an argument list, without a
shell. User input is never interpolated into a shell command. yt-dlp user config
is ignored so it cannot change the intended output or single-video behavior.

Leave Continue Task After Error **off** for both dialogs and the JavaScriptlets.
Downloads run without a terminal progress window. Inspect the plugin's `%stderr`
output / Tasker Run Log when a download fails. Allow background execution for
Termux and Tasker. A one-hour Tasker timeout is not proof that the underlying
Termux process stopped; inspect Termux before retrying a large download.

To test the script independently in Termux:

```sh
printf '%s\n' '{"url":"https://www.youtube.com/watch?v=VIDEO_ID","mode":"audio"}' |
  ~/.termux/tasker/youtube_downloader.py
```

Replace `VIDEO_ID` with the video you want. The script checks storage access and
propagates yt-dlp failures; it reports success only after yt-dlp exits successfully.

## Development and validation

From the repository root:

```sh
python integrations/youtube-downloader/build_task.py
python -m unittest discover -s integrations/youtube-downloader -p 'test_*.py'
```

The generator reuses the repository's native Input Dialog, JavaScriptlet, and
Termux:Tasker action schemas. It updates only this task and Test's task membership.
Tests cover request validation, argument safety, download modes, failure reporting,
and export structure. No actual video is fetched during automated tests.

Phone verification remains required: import the six-action task, cancel each
prompt, try an invalid URL/mode, download a short video in each mode, verify the
files in Download/YouTube, and verify that a failed download is not reported as
complete. Android import, permissions, background execution, and live YouTube
extraction cannot be verified by host-side tests.
