"""Generate a standalone Tasker export and update only its task/project in main.xml."""
from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
NAME = 'youtube downloader'
source = (ROOT / 'main.xml').read_text()
root = ET.fromstring(source)
existing = next((t for t in root.findall('Task') if t.findtext('nme') == NAME), None)
used_ids = [int(n.text) for n in root.findall('./Task/id') + root.findall('./Profile/id')]
task_id = existing.findtext('id') if existing is not None else str(max(used_ids) + 1)
input_template = next(a for a in root.iter('Action') if a.findtext('code') == '360')
plugin_template = next(a for a in root.iter('Action') if a.findtext("Str[@sr='arg1']") == 'com.termux.tasker')
js_template = next(a for a in root.iter('Action') if a.findtext('code') == '129')
task = ET.Element('Task', {'sr': 'task' + task_id})
for tag, value in [('cdate', '1791360000000'), ('edate', '1791360000000'),
                   ('id', task_id), ('nme', NAME), ('pri', '6')]:
    ET.SubElement(task, tag).text = value


def add(action, label):
    action.set('sr', 'act' + str(len(task.findall('Action'))))
    for child in list(action):
        if child.tag in ('label', 'ConditionList'): action.remove(child)
    ET.SubElement(action, 'label').text = label
    task.append(action)
    return action


def dialog(title, prompt, default=''):
    action = deepcopy(input_template)
    for arg, value in [(1, title), (2, prompt), (3, default), (5, '1')]:
        action.find(f"Str[@sr='arg{arg}']").text = value
    add(action, title)


def js(label, code):
    action = deepcopy(js_template)
    action.find("Str[@sr='arg0']").text = code
    add(action, label)


dialog('YouTube downloader', 'Paste the video URL')
js('Validate and remember URL', '''var yt_url = String(local("input") || "").trim();
if (!/^https?:\\/\\/[^\\s/]+(?:[/?#][^\\s]*)?$/i.test(yt_url)) {
    flash("Enter a complete HTTP or HTTPS URL.");
    throw new Error("Invalid download URL");
}
setLocal("yt_url", yt_url);''')
dialog('Download format', 'Enter Video or Audio (MP3)', 'Video')
js('Prepare download request', '''var yt_mode = String(local("input") || "").trim().toLowerCase();
if (yt_mode !== "video" && yt_mode !== "audio") {
    flash("Enter Video or Audio.");
    throw new Error("Invalid download mode");
}
setLocal("yt_request", JSON.stringify({url: local("yt_url"), mode: yt_mode}));
flash("Downloading " + yt_mode + " in Termux...");''')
plugin = deepcopy(plugin_template)
vals = plugin.find('Bundle/Vals')
for tag, value in {
    'com.termux.execute.arguments': '<null>',
    'com.termux.tasker.extra.EXECUTABLE': 'youtube_downloader.py',
    'com.termux.tasker.extra.STDIN': '%yt_request',
    'com.termux.tasker.extra.TERMINAL': 'false',
    'com.termux.tasker.extra.WAIT_FOR_RESULT': 'true',
    'com.twofortyfouram.locale.intent.extra.BLURB': 'youtube_downloader.py\nStdin: %yt_request\nTerminal Session: false\nWait For Result: true',
}.items():
    vals.find(tag).text = value
plugin.find("Int[@sr='arg3']").set('val', '3600')
# Continue after plugin errors so the final action can report failure.
if plugin.find('se') is None: ET.SubElement(plugin, 'se').text = '1'
add(plugin, 'Download with Termux:Tasker')
js('Report download result', '''if (String(local("result")) !== "0" || local("err")) {
    flash("Download failed or timed out. Check Tasker Run Log and Termux setup.");
    throw new Error(String(local("stderr") || local("errmsg") || "No successful Termux result"));
}
flash("Download complete: Download/YouTube");''')

# Use native ordering: code, continuation flag, label, action arguments.
for action in task.findall('Action'):
    children = list(action)
    rank = {'code': 0, 'se': 1, 'label': 2}
    action[:] = sorted(children, key=lambda child: rank.get(child.tag, 3))
ET.indent(task, space='\t', level=1)
task_xml = ET.tostring(task, encoding='unicode', short_empty_elements=False)
export = '<TaskerData sr="" dvi="1" tv="' + root.get('tv') + '">\n\t' + task_xml + '\n</TaskerData>\n'
(ROOT / (NAME + '.tsk.xml')).write_text(export)
if existing is not None:
    pattern = r'\t<Task sr="task' + task_id + r'">.*?</Task>'
    source, count = re.subn(pattern, lambda _: '\t' + task_xml, source, flags=re.S)
    assert count == 1
else:
    source = source.replace('</TaskerData>', '\t' + task_xml + '\n</TaskerData>')
project_pattern = r'(<Project\b[^>]*>)(.*?)(</Project>)'
found = False

def update_project(match):
    global found
    if '<name>Test</name>' not in match[2]: return match[0]
    found = True
    def add_id(ids):
        values = ids[1].split(',')
        if task_id not in values: values.append(task_id)
        return '<tids>' + ','.join(values) + '</tids>'
    body, count = re.subn(r'<tids>(.*?)</tids>', add_id, match[2])
    assert count == 1
    return match[1] + body + match[3]
source = re.sub(project_pattern, update_project, source, flags=re.S)
assert found, 'Test project missing'
(ROOT / 'main.xml').write_text(source)
print(f'Generated {NAME}: task {task_id}, {len(task.findall("Action"))} actions')
