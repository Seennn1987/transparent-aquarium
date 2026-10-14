# A4: 頭の幅の案を絵で見せる（背中から。体の外形=薄い灰、骨=濃い灰）
#  今の CT: 頭の幅 340 mm ÷ 全長 約 1025 mm = 33%。ICCAT の説明は 26〜29%
#  案の絵は、頭（吻端〜130 mm）の左右の幅だけを縮めた見本（130〜160 mm でなめらかにつなぐ）
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22); Fs=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
D=np.load('derolled7.npy',mmap_mode='r')
body=np.zeros((1046,300),bool)
for k in range(0,1046,200):
    b=np.asarray(D[k:k+200]); body[k:k+b.shape[0]]=(b>-400).any(1)
body=ndi.binary_fill_holes(body)
# 骨は A4 の骨の体積（a4_skel_field.npy、0.735 mm）を背中から見た影を、derolled7 と同じ格子（z 1 mm, u 1.47 mm）に移す
Fk=np.load('a4_skel_field.npy',mmap_mode='r'); NZ=Fk.shape[0]; bt=np.zeros((NZ,Fk.shape[2]),bool)
for k in range(0,NZ,150): bt[k:k+150]=(np.asarray(Fk[k:k+150])>250).any(1)
zi=np.clip((np.arange(1046)/0.735).astype(int),0,NZ-1); ui=np.clip((( (np.arange(300)-150)*1.47+180)/0.735).astype(int),0,Fk.shape[2]-1)
bone=bt[zi][:,ui]
for f_ in ('pect_L','pect_R','girdle','pelv_L','pelv_R','dfin1','dfin2','anal'):
    d_=np.load(f'a4_{f_}.npz'); m_=d_['field']>0.5; o=d_['origin']; z_,v_,u_=np.nonzero(m_)
    zz=((z_+o[0])*0.735).astype(int); uu_=(((u_+o[2])*0.735-180)/1.47+150).astype(int); ok=(zz<1046)&(uu_>=0)&(uu_<300); bone[zz[ok],uu_[ok]]=True
TL=1025.0; HW=340.0
def scaled(m,f):
    out=np.zeros_like(m); uu=(np.arange(300)-150)*1.47
    for z in range(m.shape[0]):
        w=1.0 if z<=130 else max(0.0,1-(z-130)/30); s=1-(1-f)*w
        src=uu/s/1.47+150                          # 出力の u を、元の u に戻して引く
        out[z]=ndi.map_coordinates(m[z].astype(float),[src],order=0,cval=0)>0.5
    return out
cases=[(1.0,'今（CT の個体のまま）',HW/TL),(0.29*TL/HW,'資料の上限まで縮める',0.29),(0.26*TL/HW,'資料の下限まで縮める',0.26)]
tiles=[]
for f,lab,r in cases:
    bo=scaled(body,f); bn=scaled(bone,f)
    img=np.full((300,1046,3),255,np.uint8); img[bo.T]=(214,212,222); img[bn.T]=(90,90,95)
    im=Image.fromarray(img).resize((1046,441),Image.NEAREST); d=ImageDraw.Draw(im)   # 縦も 1 px = 1 mm
    # 頭の幅の線（翼の両端の z = 69 mm）
    hw=HW*f; y0=220.5-hw/2; y1=220.5+hw/2
    d.line((69,y0,69,y1),fill=(200,30,30),width=3); d.line((60,y0,78,y0),fill=(200,30,30),width=3); d.line((60,y1,78,y1),fill=(200,30,30),width=3)
    d.text((150,y0-4),f'頭の幅 {hw:.0f} mm',fill=(200,30,30),font=Fs)
    d.line((5,432,1020,432),fill=(30,30,200),width=3); d.text((440,402),f'全長 約 {TL:.0f} mm',fill=(30,30,200),font=Fs)
    T=Image.new('RGB',(1046,480),(255,255,255)); dd=ImageDraw.Draw(T)
    dd.text((6,4),f'{lab}：頭の幅 = 全長の {r*100:.0f}%',fill=(0,0,0),font=F); T.paste(im,(0,36)); tiles.append(T)
S=Image.new('RGB',(1046,len(tiles)*485+60),(255,255,255))
for i,t in enumerate(tiles): S.paste(t,(0,i*485))
d=ImageDraw.Draw(S)
d.text((6,S.height-54),'背中から見た図（左が頭）。薄い灰=体、濃い灰=骨。2・3 段目は頭の左右の幅だけを縮めた見本',fill=(60,60,60),font=Fs)
d.text((6,S.height-28),'資料: ICCAT の種の説明「頭の幅は全長の 26〜29%」',fill=(60,60,60),font=Fs)
S.save('headwidth_options.png'); print(S.size)
