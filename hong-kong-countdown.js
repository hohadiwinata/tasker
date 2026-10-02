// Copy output/hong-kong-boarding-pass.png to /sdcard/Tasker/.
// The artwork has proportional margins: 90% width x 94% height (84.6% area).
var widget_layout = (function () {
    // Increase for larger launcher widgets; this changes live text size only.
    var textScale = 1;
    var hk = new Date(Date.now() + 8 * 3600000);
    var today = Date.UTC(hk.getUTCFullYear(), hk.getUTCMonth(), hk.getUTCDate());
    var days = Math.round((Date.UTC(2026, 10, 22) - today) / 86400000);
    var number = days > 0 ? String(days) : days === 0 ? "TODAY" : "✈";
    var caption = days > 1 ? "DAYS TO GO" : days === 1 ? "DAY TO GO" : days === 0 ? "LET'S GO" : "ARRIVED";
    function text(value, size, color) {
        return { type: "Text", text: value, textSize: size * textScale,
            color: color, bold: true, maxLines: 1, align: "Center", fontFamily: "SansSerif" };
    }
    return JSON.stringify({
        type: "Box", fillMaxSize: true, useMaterialYouColors: false,
        task: "Hong Kong Countdown",
        children: [
            { type: "Image", url: "file:///storage/emulated/0/Tasker/hong-kong-boarding-pass.png",
                fillMaxSize: true, contentScale: "FillBounds" },
            { type: "Column", fillMaxSize: true, horizontalAlignment: "Center", children: [
                { type: "Spacer", isWeighted: true },
                { type: "Box", isWeighted: true, fillMaxWidth: true,
                    horizontalAlignment: "Center", verticalAlignment: "Center",
                    children: [text(number, days > 0 ? (days >= 100 ? 34 : 46) : 20, "#FFC47B")] },
                { type: "Box", isWeighted: true, fillMaxWidth: true,
                    horizontalAlignment: "Center", verticalAlignment: "Top",
                    children: [text(caption, 8, "#FFFFFF")] }
            ] }
        ]
    });
})();
