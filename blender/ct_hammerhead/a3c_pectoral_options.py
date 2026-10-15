import hh_paths; hh_paths.cd_work()
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
zm,u,v=np.load('c833_uvz.npy'); lab=np.load('c833_split.npy'); info=json.load(open('pect_info.json'))
P=np.stack([u,zm,v],1); G=P[lab==0]; blue=P[lab==2]
D=np.load('derolled2.npy',mmap_mode='r'); sub=np.asarray(D[150:420])>-400
front_body=sub.any(0); vent_body=sub.any(1); side_body=sub.any(2)
F=hh_paths.font(15)
bb=np.array(info['blue']['base']); rb=np.array(info['red']['base'])
mid=(rb+bb)/2; half=abs(rb[0]-bb[0])/2
c=blue.mean(0); w,V=np.linalg.eigh(np.cov((blue-c).T)); e1=V[:,2]; e3=V[:,0]
if np.dot(c-bb,e1)<0: e1=-e1
e2=np.cross(e3,e1)
local=(blue-bb)@np.stack([e1,e2,e3],1)   # coords in fin frame
def place(side,s,d):
    s,d=np.radians(s),np.radians(d)
    a1=np.array([side*np.cos(d)*np.cos(s), np.cos(d)*np.sin(s), np.sin(d)])
    n=np.array([0,0,1.0]); n=n-np.dot(n,a1)*a1; n/=np.linalg.norm(n)
    a2=np.cross(n,a1)
    if a2[1]>0: a2=-a2          # in-plane width axis points forward
    if side<0: pass
    pts=local[:,0:1]*a1+local[:,1:2]*a2+local[:,2:3]*n
    base=np.array([side*half,mid[1],mid[2]])
    return pts+base
def put(img,pts,col,i_ax,j_ax,o_i,o_j,sc):
    i=((pts[:,i_ax]-o_i)*sc).astype(int); j=((pts[:,j_ax]-o_j)*sc).astype(int)
    ok=(i>=0)&(i<img.shape[1])&(j>=0)&(j<img.shape[0]); img[j[ok],i[ok]]=col
def bodyimg(mask,box,size):
    im=Image.fromarray(np.where(mask[...,None],np.array([225,220,228],np.uint8),255).astype(np.uint8)).crop(box).resize(size)
    return np.asarray(im.convert('RGB')).copy()
def panel(L,R,title,orig=None):
    sc=2.0; W,H=320,400
    a=bodyimg(front_body,(150-80/1.47,150-50/1.47,150+80/1.47,150+150/1.47),(W,H))
    put(a,G,(90,90,90),0,2,-80,-50,sc)
    for pts,col in ([(L,(220,60,60)),(R,(40,110,220))] if orig is None else orig):
        put(a,pts,col,0,2,-80,-50,sc)
    vb=Image.fromarray(np.where(vent_body[...,None],np.array([225,220,228],np.uint8),255).astype(np.uint8)).crop((150-80/1.47,0,150+80/1.47,270))
    vb=vb.transpose(Image.Transpose.ROTATE_90).transpose(Image.Transpose.FLIP_TOP_BOTTOM).resize((324,192)); b=np.asarray(vb.convert('RGB')).copy()
    def pv(pts,col):
        i=((pts[:,1]-150)*1.2).astype(int); j=((pts[:,0]+80)*1.2).astype(int); ok=(i>=0)&(i<b.shape[1])&(j>=0)&(j<b.shape[0]); b[j[ok],i[ok]]=col
    pv(G,(90,90,90))
    for pts,col in ([(L,(220,60,60)),(R,(40,110,220))] if orig is None else orig): pv(pts,col)
    out=Image.new('RGB',(334,H+b.shape[0]+50),(255,255,255)); out.paste(Image.fromarray(a),(0,25)); out.paste(Image.fromarray(b),(0,H+45))
    d=ImageDraw.Draw(out); d.text((3,3),title,fill=(0,0,0),font=F); d.text((3,H+27),'腹側から（左が吻）',fill=(80,80,80),font=F); return out
cols=[panel(None,None,'いまのCT（前から）',orig=[(P[lab==1],(220,60,60)),(blue,(40,110,220))])]
for s,dd in [(35,15),(50,30),(65,45)]:
    cols.append(panel(place(-1,s,dd),place(1,s,dd),f'案: 後ろへ{s}°・下へ{dd}°'))
Wt=sum(c.width for c in cols)+30; Ht=max(c.height for c in cols)+30
S=Image.new('RGB',(Wt,Ht),(255,255,255)); x=0
for c_ in cols: S.paste(c_,(x,0)); x+=c_.width+10
ImageDraw.Draw(S).text((5,Ht-22),'灰=肩帯。案では、形の残りがよい方の胸びれ（青）を左右に使い、片方は鏡映。付け根を左右対称の位置にそろえ、向きだけ変えた',fill=(60,60,60),font=F)
S.save('pect_options.png'); print(S.size)
