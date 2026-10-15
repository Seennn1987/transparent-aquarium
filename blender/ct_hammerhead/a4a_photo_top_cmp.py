# A4 前: 背中からの外形を、出典のある写真（NOAA、パブリックドメイン）と重ねる
#  写真: Wikimedia Commons "Sphyrna corona-zygaena compare.jpg"（右の個体が S. zygaena。590×366 px）
#   暗い画素（輝度 < 90）の行ごとの区間を、ブラウザで画像から読んだもの（ref/noaa_compare_right_runs.txt、行 30〜365、列 300〜565）
#  合わせ方: 頭の翼の両端 (326,86)・(554,66) を結ぶ線を水平に回し（5.0°）、両端の距離を CT の頭の幅にそろえ、翼の両端の中点を正中・同じ z にそろえる
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
F=hh_paths.font(15)
runs=open(hh_paths.REF+'/noaa_compare_right_runs.txt').read().strip().split(';')
M=np.zeros((366,590),bool)
for k,r in enumerate(runs):
    for seg in filter(None,r.split(',')):
        a,b=map(int,seg.split('-')); M[30+k,a:b+1]=True
lab,n=ndi.label(M); sizes=ndi.sum(M,lab,range(1,n+1)); M=lab==(1+int(np.argmax(sizes)))   # 最大の塊（この個体）だけ
M=ndi.binary_fill_holes(ndi.binary_closing(M,iterations=2))
tl,tr=np.array([326,86.]),np.array([554,66.]); ang=np.arctan2(tr[1]-tl[1],tr[0]-tl[0]); width_px=np.linalg.norm(tr-tl); mid=(tl+tr)/2
D=np.load('derolled7.npy',mmap_mode='r'); H=np.asarray(D[0:400]); top=ndi.binary_fill_holes((H>-400).any(1))   # (z mm, u 1.47mm)
zi,ui=np.nonzero(top[:130]); um=(ui-150)*1.47; head_w=um.max()-um.min()
# CT で翼の端がある z（左右の端の点の z の平均）
zt=np.mean([zi[np.argmin(um)],zi[np.argmax(um)]])
s=head_w/width_px                                     # mm / px
yy,xx=np.nonzero(M); p=np.stack([xx-mid[0],yy-mid[1]],1)
c,sn=np.cos(-ang),np.sin(-ang); q=np.stack([p[:,0]*c-p[:,1]*sn,p[:,0]*sn+p[:,1]*c],1)*s   # 回して水平に
pu=q[:,0]; pz=q[:,1]+zt
# 図: 横=u、縦=z（上が吻）。1 px = 1 mm
W,Hh=420,400; img=np.full((Hh,W,3),255,np.uint8)
jj,ii=np.mgrid[0:Hh,0:W]; uu=((ii-W/2)/1.47+150).astype(int); ok=(uu>=0)&(uu<300)
img[ok&top[jj.clip(0,399),uu.clip(0,299)]]=(200,200,210)
PM=np.zeros((Hh,W),bool); i=(pu+W/2).astype(int); j=pz.astype(int); k=(i>=0)&(i<W)&(j>=0)&(j<Hh); PM[j[k],i[k]]=True
PM=ndi.binary_closing(PM,iterations=2); edge=PM&~ndi.binary_erosion(PM); img[ndi.binary_dilation(edge)]=(220,30,30)
im=Image.fromarray(img).resize((W*2,Hh*2),Image.NEAREST); d=ImageDraw.Draw(im)
for mm in range(0,400,50): d.line((0,mm*2,12,mm*2),fill=(0,0,0)); d.text((14,mm*2-8),f'{mm}',fill=(0,0,0),font=F)
d.text((10,Hh*2-50),'灰=CT（A3 の後、背中から）  赤線=写真の S. zygaena（頭の幅をそろえた）',fill=(0,0,0),font=F)
d.text((10,Hh*2-28),'写真: NOAA（NMFS-PIRO Observer Program）、Wikimedia Commons、パブリックドメイン',fill=(80,80,80),font=F)
im.save('photo_top_cmp.png')
# 幅の比べ（z ごと）
res=[]
for z in range(130,330,20):
    a=np.nonzero(top[z])[0]; ctw=(a.max()-a.min()+1)*1.47 if len(a) else None
    sel=np.abs(pz-z)<1.5; phw=(pu[sel].max()-pu[sel].min()) if sel.sum() else None
    res.append((z,round(ctw,1) if ctw else None,round(float(phw),1) if phw is not None else None))
json.dump({'scale_mm_per_px':round(s,3),'head_width_mm':round(float(head_w),1),'rot_deg':round(float(np.degrees(ang)),1),'width_by_z':res},open('photo_top_cmp.json','w'),ensure_ascii=False)
print(s,head_w,res)
