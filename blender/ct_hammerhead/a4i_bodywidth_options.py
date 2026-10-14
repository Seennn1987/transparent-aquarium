# 頭の幅を全長の 26% に決めた後の、胴の幅の案（背中から。体の外形=薄い灰、骨=濃い灰）
#  頭（〜130 mm）は左右を 0.784 倍（340→266 mm）。胴（160 mm〜）は左右を k 倍。130〜160 mm はなめらかにつなぐ
#  骨は広げない（頭の骨だけ 0.784 倍）
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
exec(open('a4_headwidth_opts.py').read().split("TL=1025.0")[0])        # body, bone を作る部分だけ流用
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22); Fs=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
FH=266.0/340.0
def prof(k):
    z=np.arange(1046.); w=np.clip((z-130)/30,0,1); w=w*w*(3-2*w); return FH*(1-w)+k*w
def apply(m,sc):
    out=np.zeros_like(m); uu=(np.arange(300)-150)*1.47
    for z in range(m.shape[0]): out[z]=ndi.map_coordinates(m[z].astype(float),[uu/sc[z]/1.47+150],order=0,cval=0)>0.5
    return out
bone_sc=np.where(np.arange(1046)<160,prof(1.0),1.0)
bn=apply(bone,bone_sc)
def width_at(m,z): a=np.nonzero(m[z])[0]; return (a.max()-a.min()+1)*1.47
cases=[(1.0,'胴は CT のまま'),(266/2.6/66,'胴の幅を写真の「頭の幅 ÷ 胴の幅 = 2.6」に合わせる'),(2.0,'胴は CT の 2 倍（前回の決定）')]
tiles=[]
for k,lab in cases:
    bo=apply(body,prof(k)); tw=np.median([width_at(bo,z) for z in range(180,260,10)])
    img=np.full((300,1046,3),255,np.uint8); img[bo.T]=(214,212,222); img[bn.T]=(90,90,95)
    im=Image.fromarray(img).resize((1046,441),Image.NEAREST); d=ImageDraw.Draw(im)
    T=Image.new('RGB',(1046,480),(255,255,255)); dd=ImageDraw.Draw(T)
    dd.text((6,4),f'{lab}：胴の幅 約 {tw:.0f} mm（頭の幅 266 mm ÷ 胴 = {266/tw:.1f}）',fill=(0,0,0),font=F); T.paste(im,(0,36)); tiles.append(T)
S=Image.new('RGB',(1046,len(tiles)*485+60),(255,255,255))
for i,t in enumerate(tiles): S.paste(t,(0,i*485))
d=ImageDraw.Draw(S)
d.text((6,S.height-54),'背中から（左が頭）。頭の幅は全長の 26%（決定）。胴の幅は 180〜250 mm の中央値。骨は広げていない',fill=(60,60,60),font=Fs)
d.text((6,S.height-28),'写真の比: NOAA の背中からの写真（パブリックドメイン）で、頭の幅 ÷ 胴の幅 = 2.6',fill=(60,60,60),font=Fs)
S.save('bodywidth_options.png'); print(S.size)
