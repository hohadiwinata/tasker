# Termux Toto result to Mama on WhatsApp

**Test → Termux Toto Result** now snapshots images in **Internal storage/Pictures/Toto**, runs the existing `toto_tasker.py` with **Wait For Result** enabled and a **300-second timeout**, then shares the single new or updated PNG/JPG/JPEG/WebP to Mama. Mama's number (ending **3886**) was looked up in Google Contacts and is embedded as the WhatsApp recipient in the task. No caption is added.

Copy [Termux Toto Result.tsk.xml](Termux%20Toto%20Result.tsk.xml) to your phone. If a task with that name already exists, rename it to **Termux Toto Result old** first; if it is completely empty, you can delete that empty task instead. While **Test** is selected, long-press Tasker's **Tasks** tab, choose **Import Task**, and select the new XML copy. Open the imported task and confirm it has **10 actions**, starting with **Remember existing Toto images**. If profiles or shortcuts referred to the renamed task, point them to the newly imported task. This standalone import avoids restoring the entire backup. The same change is included in [main.xml](main.xml).

If an earlier copy imported as an empty task, replace the downloaded XML on the phone before importing again. The regenerated export uses native `sr`-then-`ve` action attribute ordering and a task reference matching its ID. Host-side checks validate those details and all ten actions; phone import still needs verification.

Tasker needs access to Pictures/Toto; keep Termux's existing storage permissions and script setup. The generator must finish writing the image before it exits and return exit code `0`. No changes to the Termux script are required. If it exits without changing an image, produces several images, fails, or leaves an empty/changing file, the task stops without sending an attachment. The folder is checked again after one second to catch files still being written.

The sharing steps first run Tasker's `FilePathToContentUri(%toto_image)`, then Java Code opens WhatsApp from a temporary Tasker activity with the resulting content URI, ClipData, and temporary read permission. This replaces the previous file-URI Send Intent attempt. Launch exceptions stop the task before AutoInput. Android returning from the launch call does not prove the preview was displayed or the image delivered. See [Android file sharing guidance](https://developer.android.com/training/secure-file-sharing/share-file).

The phone must be **on and unlocked**, WhatsApp signed in, and **AutoInput's accessibility service enabled**. The final AutoInput Actions v2 action waits up to 30 seconds for WhatsApp with **Mama** visible, then clicks `com.whatsapp:id/send`. Keep Mama saved under that name on the phone. This uses a WhatsApp sharing intent and UI automation; app updates can change the recipient extra, preview, or button ID. If the guard times out, the task fails instead of clicking elsewhere.

**On-device check:** import [Termux Toto Content Preview.tsk.xml](Termux%20Toto%20Content%20Preview.tsk.xml), which has AutoInput disabled and a distinct task name. Run it and verify that WhatsApp previews the correct image for Mama. Once the preview is correct, cancel it and import the updated main task to test automatic sending. If necessary, use AutoInput's Easy Setup on the image preview to update the Send button ID or recipient text. Local validation cannot confirm WhatsApp delivery. Nothing was sent from this computer.

The JavaScript is embedded in the exports: edit `toto-files.js`, `toto-before.js`, or `toto-after.js`, or `toto-share.java`, then run `python build-toto.py`. Run `node test-toto.js` for file-selection and failure-path checks. Source references: [Termux:Tasker completion/results](https://github.com/termux/termux-tasker), [Tasker JavaScript functions](https://tasker.joaoapps.com/userguide/en/javascript.html), and [AutoInput Actions v2](https://joaoapps.com/autoinput-actions-v2-single-action-total-ui-automation/).

# Singapore morning haze notification

[main.xml](main.xml) includes **Singapore Haze Morning** and its **Singapore Haze** task in **Base**. The enabled profile runs every day at **06:55 in the phone's time zone**. Keep your phone set to **Asia/Singapore (GMT+8)** for 6:55 AM Singapore time.

The task fetches the latest [official NEA PSI feed on data.gov.sg](https://api-open.data.gov.sg/v2/real-time/api/psi), then sends an Android notification with the **24-hour PSI range across all five regions**, the highest value and region, its health category, a short activity advisory, and the reading time in SGT. Categories follow [MOH's haze advisory](https://www.moh.gov.sg/others/haze/): **0–50 Good; 51–100 Moderate; 101–200 Unhealthy; 201–300 Very Unhealthy; above 300 Hazardous**. The displayed category uses the highest regional reading. PSI is a rolling 24-hour measure, updated hourly, so the morning notification may show the 06:00 reading.

Restore this backup in Tasker to activate the included profile; restoring replaces your existing Tasker configuration. To keep your current configuration, import [Singapore Haze.tsk.xml](Singapore%20Haze.tsk.xml) while viewing **Base**, then create a daily **Time** profile with both **From** and **To** set to **06:55**, linked to **Singapore Haze**. Run the task once to check delivery. Allow Tasker notifications and background execution; internet access is required. This repository edit does not install the automation on your phone.

If the request fails or readings are invalid, the task sends **PSI unavailable**. Readings older than two hours are labelled **stale**, with no current health judgement. Edit [singapore-haze.js](singapore-haze.js), then run `python build-haze.py` to synchronise the task exports. Run `node test-singapore-haze.js` to check parsing and health categories.

# Hong Kong trip countdown widget

A compact **1 × 2** [Tasker Widget v2](https://tasker.joaoapps.com/userguide/en/help/ah_widget_v2.html) for the trip on **22 November 2026**. It counts calendar days in Hong Kong (UTC+8), so the displayed day changes at Hong Kong midnight. It shows **TODAY** on the 22nd and a post-trip message afterward.

## Add it to your Android home screen

The [Tasker backup](main.xml) now includes **Hong Kong Countdown** in the **Base** project, plus a daily refresh profile at 00:05 (phone time). If you use this backup, restore it in Tasker and run the task once. Restoring a full backup replaces the phone's current Tasker configuration, so use this only if this backup is the configuration you want to restore.

First copy [hong-kong-boarding-pass.png](output/hong-kong-boarding-pass.png) to **Internal storage/Tasker/hong-kong-boarding-pass.png** on your phone. Keep the filename unchanged and allow Tasker to read that file. The artwork supplies the transparent ticket cutouts, boarding header, destination, divider, and departure labels; the countdown and its caption remain live Android text.

To add just the task to your current setup, import [Hong Kong Countdown.tsk.xml](Hong%20Kong%20Countdown.tsk.xml) while viewing **Base** in Tasker. Then run it once and add a daily **Time** profile at 00:05 that runs the task. The standalone task import does not include the profile.

If you prefer to set it up manually:

1. Use your existing **1 × 2 Tasker Widget v2** widget named **Countdown**.
2. In Tasker, create a task named **Hong Kong Countdown**.
3. Add a **Code → JavaScriptlet** action. Paste in the contents of [hong-kong-countdown.js](hong-kong-countdown.js), leaving **Auto Exit** enabled.
4. Add a **Tasker → Widget v2** action. Select **Countdown** for **Widget Name** (use the magnifying glass), set **Layout** to `Custom`, and set **Custom Layout** to `%widget_layout`. Leave the other layout fields empty.
5. Run the task once to draw the widget. Tapping the card also runs the task to refresh it.
6. Add a Tasker **Time** profile set to run daily at **00:05** in your phone's time zone, with **Hong Kong Countdown** as its task. If your phone is outside UTC+8, schedule it shortly after Hong Kong midnight instead. You can also run the task any time to refresh it.

The JavaScriptlet creates JSON for Tasker's custom layout and sets `%widget_layout` for the next action. No network access is needed after copying the PNG. The card scales to **90% of the available width and 94% of the available height**, giving a bounding area of **84.6%** (slightly less visible ink after rounded corners and ticket cutouts). These margins are built into the transparent PNG, so they scale when you resize the widget. Launcher-imposed padding is outside Tasker's content area and may reduce coverage of the full grid cell.

The live text sits in weighted layout sections so it stays positioned as the widget height changes. Its font size stays readable for a compact 1 × 2 widget; edit `var textScale = 1` in the JavaScriptlet for a larger widget or different Android font scaling. A portrait widget near a 1:2 aspect ratio best matches the reference; other shapes stretch the artwork. Replace the previous PNG on your phone as well as re-importing the task for this design update.

Open [the preview](output/countdown-widget.html) to see the design at an enlarged size with the current Hong Kong countdown. Native Android font spacing can differ slightly. The layout uses the Image and Box elements described in [Tasker's custom layout reference](https://tasker.joaoapps.com/userguide/en/widgetv2_custom.html). Phone rendering and local image access still need to be checked on the device.

For source edits, update `hong-kong-countdown.js`, then run `python build-countdown.py` (requires Pillow and Windows Arial fonts). This regenerates the PNG and synchronizes only the countdown JavaScriptlet in both XML exports. The PNG contains the static departure date, so change the artwork labels as well if you change trips.
