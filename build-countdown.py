"""Render ticket artwork and synchronize the countdown JavaScriptlet exports."""
from pathlib import Path
import html
import re
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)
S = 3
im = Image.new('RGBA', (400*S, 800*S))
d = ImageDraw.Draw(im)
teal, muted, gold = '#082F38', '#80BAC4', '#FFC47B'
def poly(points, fill):
    d.polygon([(round(x*S),round(y*S)) for x,y in points], fill=fill)
def label(text,x,y,size,color='white'):
    d.text((x*S,y*S),text,font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',size*S),fill=color,anchor='mm')
# Proportional clear margins; no opaque white background or fixed dp card size.
d.rounded_rectangle((20*S,24*S,380*S,776*S),radius=44*S,fill=teal)
for y in (137,611):
    for x in (20,380):
        d.ellipse(((x-20)*S,(y-23)*S,(x+20)*S,(y+23)*S),fill=(0,0,0,0))
poly([(72,77),(88,75),(80,54),(86,53),(101,73),(119,71),(124,73),
      (125,77),(121,80),(101,82),(89,104),(83,104),(87,83),(74,84),
      (69,89),(65,89),(68,79),(64,71),(68,70)],gold)
label('BOARDING',238,79,33,gold)
label('HKG',200,224,123)
label('H O N G  K O N G',200,299,28,muted)
# Live countdown is centered at 50% height; live caption starts at 2/3 height.
d.line((60*S,619*S,340*S,619*S),fill=muted,width=3*S)
label('DEPARTURE',200,669,26,muted)
label('22 NOV 26',200,715,39)
im.resize((800,1600),Image.Resampling.LANCZOS).save(OUT/'hong-kong-boarding-pass.png')
js=(ROOT/'hong-kong-countdown.js').read_text(encoding='utf-8-sig').strip()
for name in ('Hong Kong Countdown.tsk.xml','main.xml'):
    path=ROOT/name
    source=path.read_bytes().decode('utf-8')
    pattern=r'(<nme>Hong Kong Countdown</nme>.*?<Str sr="arg0" ve="3">).*?(</Str>)'
    source,count=re.subn(pattern,lambda m:m[1]+html.escape(js,quote=False)+m[2],source,count=1,flags=re.S)
    assert count==1, f'Missing countdown task in {name}'
    path.write_bytes(source.encode('utf-8'))
# Enlarged, representative 100 x 200 dp preview, matching the native text sizes.
p=im.copy(); pd=ImageDraw.Draw(p)
pd.text((200*S,400*S),'58',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',184*S),fill=gold,anchor='mm')
pd.text((200*S,552*S),'DAYS TO GO',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',32*S),fill='white',anchor='mm')
p.resize((800,1600),Image.Resampling.LANCZOS).save(OUT/'countdown-preview.png')
print('Rendered simplified ticket and synchronized both XML exports.')
