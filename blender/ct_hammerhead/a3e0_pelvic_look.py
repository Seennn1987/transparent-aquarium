# A3 腹びれの所の塊を、起こした座標（u,z,v mm）に移して見る
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
L=np.load('skel_lab.npy',mmap_mode='r'); cxs,cys=np.load('spine_line.npy'); t=np.load('tilt_sym.npy')
IDS=[3067,3064,3149,3048,3077,3061,3515,4]
sub=np.asarray(L[880:1080]); pts={}
for i in IDS:
    zz,yy,xx=np.nonzero(sub==i); z=zz+880
    c=np.cos(np.radians(t[z])); s=np.sin(np.radians(t[z])); dx=xx-cxs[z]; dy=yy-cys[z]
    P=np.stack([(c*dx+s*dy)*0.735, z*0.5, (-s*dx+c*dy)*0.735],1)
    if i==4: P=P[(P[:,1]>=440)&(P[:,1]<540)]
    pts[i]=P.astype(np.float32)
np.savez('pelvic_uvz.npz',**{str(k):v for k,v in pts.items()})
D=np.load('derolled2.npy',mmap_mode='r'); body=np.asarray(D[440:540])>-400
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14)
COL={3067:(220,60,60),3064:(40,110,220),3149:(30,170,200),3048:(230,150,20),3077:(150,60,200),3061:(60,160,60),3515:(120,120,0),4:(90,90,90)}
def view(kind):
    if kind=='front':
        m=body.any(0); W,H=120,140; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-50)/1.47+150).astype(int); uu=((ii-60)/1.47+150).astype(int)
        img[m[vv,uu]]=(225,220,228); f=lambda p:(p[:,0]+60,p[:,2]+50)
    elif kind=='vent':
        m=body.any(1); W,H=100,120; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; uu=((jj-60)/1.47+150).astype(int)
        img[m[ii,uu]]=(225,220,228); f=lambda p:(p[:,1]-440,p[:,0]+60)
    else:
        m=body.any(2); W,H=100,140; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-50)/1.47+150).astype(int)
        img[m[ii,vv]]=(225,220,228); f=lambda p:(p[:,1]-440,p[:,2]+50)
    for k in IDS:
        i,j=f(pts[k]); i=i.astype(int); j=j.astype(int); ok=(i>=0)&(i<W)&(j>=0)&(j<H); img[j[ok],i[ok]]=COL[k]
    return Image.fromarray(img).resize((W*3,H*3),Image.NEAREST)
# 断面（起こした体積、z=470/490/510 mm）
def xsec(z):
    a=np.asarray(D[z]).astype(float); a=np.clip((a+200)/700,0,1)
    im=Image.fromarray((a*255).astype(np.uint8)).crop((150-40,150-34,150+40,150+68)).resize((240,306),Image.NEAREST)
    return im.convert('RGB')
tiles=[(view('front'),'前から（体の中の背骨の所が 0）'),(view('vent'),'腹側から（左が吻、z 440〜540mm）'),(view('side'),'横から（左が吻）')]
xs=[(xsec(z),f'断面 z={z}mm') for z in (465,480,495,510,525)]
W=sum(t.width for t,_ in tiles)+40; H=max(t.height for t,_ in tiles)+xs[0][0].height+110
S=Image.new('RGB',(max(W,sum(x.width for x,_ in xs)+50),H),(255,255,255)); d=ImageDraw.Draw(S); x=0
for t_,lab in tiles: S.paste(t_,(x,22)); d.text((x+2,2),lab,fill=(0,0,0),font=F); x+=t_.width+20
y=max(t.height for t,_ in tiles)+50; x=0
for im,lab in xs: S.paste(im,(x,y+20)); d.text((x+2,y),lab,fill=(0,0,0),font=F); x+=im.width+10
leg='  '.join(f'{k}' for k in IDS); x=5
for k in IDS:
    d.rectangle((x,H-22,x+12,H-10),fill=COL[k]); d.text((x+15,H-25),str(k) if k!=4 else '4(背骨)',fill=(0,0,0),font=F); x+=90
S.save('pelvic_look.png'); print(S.size)
for k in IDS:
    P=pts[k]; print(k,len(P),P.min(0).round(0),P.max(0).round(0))
