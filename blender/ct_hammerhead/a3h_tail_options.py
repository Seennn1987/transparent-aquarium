# A3 尾の反りの案: CT のまま / 写真で読んだ角度に近づける（横から見た図だけ。体積は決定後に作る）
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import shift as ndshift
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',15)
keep=np.load('tail_keep_v.npy'); B=np.load('derolled3_mips.npy')[1]    # (z mm, v px 1.47mm)
zz=np.arange(760,1011); p=np.polyfit(zz,keep[zz*2],1); ct_deg=float(np.degrees(np.arctan(-p[0])))
print('CT 上葉の背骨の角度（760〜1010 mm、胴の軸から）', round(ct_deg,1))
HINGE=750
def bent(extra):
    img=B[600:1046].astype(float).copy()
    out=np.full_like(img,-1000)
    for i,mm in enumerate(range(600,1046)):
        r=np.clip((mm-HINGE)/30,0,1); d=np.tan(np.radians(extra))*max(mm-HINGE-15*r,0)*r   # 付け根でなめらかに曲げる
        out[i]=ndshift(img[i],-d/1.47,order=1,cval=-1000)
    return out
def im(m):
    g=np.clip((m+600)/1100,0,1); a=(255-g*225).astype(np.uint8).T[70:235]
    return Image.fromarray(a).resize((a.shape[1]*2,int(a.shape[0]*2*1.47)),Image.BILINEAR)   # 縦横の mm をそろえる
opts=[(0,f'① CT のまま（上葉の背骨は胴の軸から約 {ct_deg:.0f}°）'),(10-ct_deg+5,'② 約 15°'),(20-ct_deg,'③ 約 20°（写真で読んだ値に近い）')]
tiles=[(im(bent(e)),t) for e,t in opts]
W=tiles[0][0].width+10; H=sum(t.height+34 for t,_ in tiles)+40
S=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(S); y=0
for t,lab in tiles:
    d.text((4,y+6),lab,fill=(0,0,0),font=F); S.paste(t,(0,y+30))
    for mm in range(650,1046,50):
        x=(mm-600)*2; d.line((x,y+30,x,y+38),fill=(220,0,0)); d.text((x+2,y+30),str(mm),fill=(200,0,0),font=F)
    y+=t.height+34
d.text((4,H-28),'横から（上が背、左が吻、数字は吻端からの mm）。②③は 750 mm（尾びれの付け根）から後ろを背へ曲げた見本',fill=(60,60,60),font=F)
S.save('tail_options.png'); print(S.size)
