# A3 尾: 背骨の線でまっすぐにせず、胴の直線（z 200〜800 mm の背骨の線に合わせた直線）を中心に起こして見る
import hh_paths; hh_paths.cd_work()
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image, ImageDraw, ImageFont
C=np.load('zyg_clean.npy',mmap_mode='r'); cxs,cys=np.load('spine_line.npy'); t=np.load('tilt_sym.npy')
z=np.arange(len(cxs)); sel=(z>=400)&(z<=1600)
lx=np.polyval(np.polyfit(z[sel],cxs[sel],1),z); ly=np.polyval(np.polyfit(z[sel],cys[sel],1),z)
N=200; c0=N/2; uu,vv=np.meshgrid((np.arange(N)-c0),(np.arange(N)-c0))   # 1 px = 0.735 mm
Z0,Z1=1500,2093; side=np.full((Z1-Z0,N),-1000,np.int16); top=side.copy(); bside=np.zeros((Z1-Z0,N),bool); btop=bside.copy()
for i,zz in enumerate(range(Z0,Z1)):
    s=np.asarray(C[zz]).astype(np.float32); th=np.radians(t[zz])
    x=uu*np.cos(th)-vv*np.sin(th)+lx[zz]; y=uu*np.sin(th)+vv*np.cos(th)+ly[zz]
    o=map_coordinates(s,[y,x],order=1,cval=-1000)
    side[i]=o.max(1); top[i]=o.max(0); bside[i]=(o>-400).any(1); btop[i]=(o>-400).any(0)
np.savez('tail_view.npz',side=side,top=top,bside=bside,btop=btop,lx=lx,ly=ly)
def img(a,b):
    g=np.clip((a.astype(float)-0)/600,0,1); rgb=np.where(b[...,None],np.array([225,220,228]),255).astype(float)
    rgb=rgb*(1-g[...,None])+np.array([30,30,30])*g[...,None]
    return Image.fromarray(rgb.astype(np.uint8).transpose(1,0,2))   # 横=z（左が吻）, 縦=v または u
F=hh_paths.font(14)
a=img(side,bside); b=img(top,btop); W,H=a.width*2,a.height*2
S=Image.new('RGB',(W+10,2*H+80),(255,255,255)); d=ImageDraw.Draw(S)
S.paste(a.resize((W,H),Image.NEAREST),(0,22)); S.paste(b.resize((W,H),Image.NEAREST),(0,H+60))
d.text((4,2),'横から（体を起こしただけ、背骨はまっすぐにしていない。上が背、左が吻。z 750〜1046 mm）',fill=(0,0,0),font=F)
d.text((4,H+38),'背中から（上が体の左右の一方）',fill=(0,0,0),font=F)
for mm in range(750,1050,50):
    x=int((mm*2-Z0)*2); d.line((x,22+H-8,x,22+H),fill=(255,0,0)); d.text((x+2,22+H-22),str(mm),fill=(200,0,0),font=F)
S.save('tail_look.png'); print(S.size)
