# A3 腹びれの向きの案（胸びれと同じ方法）
#  - 塊: 左 3067（1528 点）、右 3064+3149+3077（3014 点、右の方が形が多く残る）。3048 は正中の小片（左右 5 mm、z 460〜483 mm）
#    で腰帯（左右のひれをつなぐ横の棒）かは未確認。腰帯の横の棒は閾値 250 HU では写っていないか、細い（未確認）
#  - 右のひれを左右に使い（左は鏡映）、付け根は右の元の付け根 (5.5, 464.4, 46.8) とその鏡映。
#    付け根 = 3048 にいちばん近い 3% の点の平均。z 465 mm の断面で左右 5 mm の所の腹面は 56 mm なので体の内側
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree
d=np.load('pelvic_uvz.npz'); bar=d['3048']; spine=d['4']
right=np.concatenate([d[i] for i in ('3064','3149','3077')]); left=d['3067']; mid=np.concatenate([bar,d['3061'],d['3515']])
dist=cKDTree(bar).query(right)[0]; bb=right[dist<=np.percentile(dist,3)].mean(0)
c=right.mean(0); w,V=np.linalg.eigh(np.cov((right-c).T)); e1=V[:,2]; e3=V[:,0]
if np.dot(c-bb,e1)<0: e1=-e1
e2=np.cross(e3,e1); local=(right-bb)@np.stack([e1,e2,e3],1)
def frame_of(P,base):
    c=P.mean(0); w,V=np.linalg.eigh(np.cov((P-c).T)); a=V[:,2]; n_=V[:,0]
    if np.dot(c-base,a)<0: a=-a
    return (P-base)@np.stack([a,np.cross(n_,a),n_],1)
LB=left[cKDTree(left).query(bb)[1]] if False else None
dl=cKDTree(bar).query(left)[0]; lb=left[dl<=np.percentile(dl,3)].mean(0)
local_left=frame_of(left*np.array([-1,1,1]),lb*np.array([-1,1,1]))   # 左を鏡映して右のひれとして扱う
local_right=local
def place(side,s,dn,loc=None):
    loc=local if loc is None else loc
    s,dn=np.radians(s),np.radians(dn)
    a1=np.array([side*np.cos(dn)*np.cos(s), np.cos(dn)*np.sin(s), np.sin(dn)])
    n=np.array([0,0,1.0]); n=n-np.dot(n,a1)*a1; n/=np.linalg.norm(n)
    a2=np.cross(n,a1)
    if a2[1]>0: a2=-a2
    return loc[:,0:1]*a1+loc[:,1:2]*a2+loc[:,2:3]*n+bb*np.array([side,1,1])
D=np.load('derolled2.npy',mmap_mode='r'); body=np.asarray(D[420:560])>-400   # z 420..559
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14)
def view(parts,kind):
    if kind=='front':
        m=body.any(0); W,H=130,140; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-50)/1.47+150).astype(int); uu=((ii-65)/1.47+150).astype(int)
        img[m[vv,uu]]=(225,220,228); f=lambda p:(p[:,0]+65,p[:,2]+50)
    else:
        m=body.any(1); W,H=140,130; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; uu=((jj-65)/1.47+150).astype(int)
        img[m[ii,uu]]=(225,220,228); f=lambda p:(p[:,1]-420,p[:,0]+65)
    for p,col in parts:
        i,j=f(p); i=i.astype(int); j=j.astype(int); ok=(i>=0)&(i<W)&(j>=0)&(j<H); img[j[ok],i[ok]]=col
    return Image.fromarray(img).resize((W*2,H*2),Image.NEAREST)
GR,RD,BL,OR=(90,90,90),(220,60,60),(40,110,220),(230,150,20)
sets=[('いまのCT',[(spine,GR),(mid,OR),(left,RD),(right,BL)])]
OPTS=[(45,10),(60,20),(75,30)]
for s,dn in OPTS: sets.append((f'右を使う: 後ろへ{s}°・下へ{dn}°',[(spine,GR),(mid,OR),(place(-1,s,dn),RD),(place(1,s,dn),BL)]))
sets2=[('（比べる）左の 1 枚の形',[(spine,GR),(mid,OR),(left,RD)])]
for s,dn in OPTS: sets2.append((f'左を使う: 後ろへ{s}°・下へ{dn}°',[(spine,GR),(mid,OR),(place(-1,s,dn,local_left),RD),(place(1,s,dn,local_left),BL)]))
cols=[]
for title,parts in sets:
    a=view(parts,'front'); b=view(parts,'vent')
    out=Image.new('RGB',(max(a.width,b.width),a.height+b.height+60),(255,255,255)); dr=ImageDraw.Draw(out)
    dr.text((2,2),title+'（前から）',fill=(0,0,0),font=F); out.paste(a,(0,22)); dr.text((2,a.height+30),'腹側から（左が吻）',fill=(60,60,60),font=F); out.paste(b,(0,a.height+50)); cols.append(out)
cols2=[]
for title,parts in sets2:
    a=view(parts,'front'); b=view(parts,'vent')
    out=Image.new('RGB',(max(a.width,b.width),a.height+b.height+60),(255,255,255)); dr=ImageDraw.Draw(out)
    dr.text((2,2),title,fill=(0,0,0),font=F); out.paste(a,(0,22)); out.paste(b,(0,a.height+50)); cols2.append(out)
Wt=sum(c_.width for c_ in cols)+30; h1=max(c_.height for c_ in cols); Ht=h1*2+60
S=Image.new('RGB',(Wt,Ht),(255,255,255)); x=0
for c_ in cols: S.paste(c_,(x,0)); x+=c_.width+10
x=0
for c_ in cols2: S.paste(c_,(x,h1+20)); x+=c_.width+10
ImageDraw.Draw(S).text((5,Ht-22),'灰=背骨、橙=正中の小片（腰帯か未確認）。上段=右の 2 つの塊（3064+3149）を使う、下段=左の 1 枚（3067）を使う。どちらも片方は鏡映、付け根は同じ位置',fill=(60,60,60),font=F)
S.save('pelvic_options.png')
info={'right_base_uzv':bb.round(1).tolist(),'right_dir':e1.round(2).tolist(),'right_len_mm':round(float((local[:,0]).max()),1),
      'right_n':int(len(right)),'left_n':int(len(left)),'left_len_note':'PCA 長さ 60.0 mm','options':OPTS}
json.dump(info,open('pelvic_info.json','w'),ensure_ascii=False); print(info,S.size)
