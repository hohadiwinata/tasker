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
