# A4: 背中からの骨の静止画（a4_top.png）に、写真の外形（頭の幅をそろえた）を重ねる
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18)
import os; R=os.path.expanduser('~/mnt/transparent-aquarium/transparent-aquarium')
img=Image.open(R+'/docs/hammerhead_ct/a4_top.png').convert('RGB'); W,H=img.size
# a4f_render_outline.py の外接と同じ数（Blender の出力 bbox m (0.005,-0.167,-0.073)-(1.012,0.166,0.113)）
mn=np.array([0.005,-0.167]); mx=np.array([1.012,0.166]); ctr=(mn+mx)/2; ortho=(mx[0]-mn[0])*1.05; mpp=ortho/W
def to_px(z_mm,u_mm):
    X=z_mm/1000; Y=u_mm/1000
    return (X-ctr[0])/mpp+W/2, H/2-(Y-ctr[1])/mpp
# 写真の外形（a4a_photo_top_cmp.py と同じ合わせ方。頭の幅は骨の外接ではなく、体の外形の 339.6 mm）
runs=open('ref/noaa_compare_right_runs.txt').read().strip().split(';')
M=np.zeros((366,590),bool)
for k,r in enumerate(runs):
    for seg in filter(None,r.split(',')):
        a,b=map(int,seg.split('-')); M[30+k,a:b+1]=True
lab,n=ndi.label(M); sizes=ndi.sum(M,lab,range(1,n+1)); M=lab==(1+int(np.argmax(sizes))); M=ndi.binary_fill_holes(ndi.binary_closing(M,iterations=2))
E=M&~ndi.binary_erosion(M); yy,xx=np.nonzero(E)
tl,tr=np.array([326,86.]),np.array([554,66.]); ang=np.arctan2(tr[1]-tl[1],tr[0]-tl[0]); mid=(tl+tr)/2
s=339.6/np.linalg.norm(tr-tl); p=np.stack([xx-mid[0],yy-mid[1]],1); c,sn=np.cos(-ang),np.sin(-ang)
q=np.stack([p[:,0]*c-p[:,1]*sn,p[:,0]*sn+p[:,1]*c],1)*s
ZT=69.0   # CT の頭の翼の両端の z（体の外形、derolled7 で測った値）
px,py=to_px(q[:,1]+ZT,q[:,0])
d=ImageDraw.Draw(img)
for x,y in zip(px,py): d.ellipse((x-1.5,y-1.5,x+1.5,y+1.5),fill=(220,30,30))
d.text((10,H-56),'灰=A4 の骨（背中から）  赤=写真の S. zygaena の外形（頭の幅 339.6 mm にそろえた。尾は写真に写っていない）',fill=(0,0,0),font=F)
d.text((10,H-30),'写真: NMFS-PIRO Observer Program（NOAA）、Wikimedia Commons「Sphyrna corona-zygaena compare.jpg」、パブリックドメイン',fill=(80,80,80),font=F)
img.save(R+'/docs/hammerhead_ct/a4_top_photo.png'); print('ok')
