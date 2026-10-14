# A3 胸びれと肩帯の姿勢（2026-10-14 決定）
#  - 向き: 後ろへ35°・下へ15°（案1、プロデューサー決定）
#  - 形の残りがよい右側（u>0、青）のひれを左右に使い、左は鏡映（了承済み）
#  - 付け根: 青のひれの元の付け根 (u,z,v)=(13.7,232.7,40.3) とその鏡映。
#    v=40 は体の横の下寄り（体の断面 z=232: 背 -37 / 腹 74 mm）。
#    案の図では左右の付け根の平均 v=59.5 を使ったが、そこは u=±12 で体の腹面の外になるため変更
#  - 肩帯: 青のひれ側の半分（u>=0）を鏡映して左右に使う。
#    元の肩帯は左右で高さが違う（正中付近 u=±7.5 で v 57 と 50）。背骨(0,0)と肩帯中央(u≈0,v≈53)は
#    縦に並ぶので、座標の傾きではなく肩帯そのものの変形と判断
# 座標: derolled2 の (u 左右, z 吻→尾, v 背-/腹+) mm。背骨の中心が u=0,v=0
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
# 2026-10-14: 頭〜胸の倒れの残り（a3l_neck_roll_fix.py）を戻した後の点を使う
zm,u,v=np.load('c833_uvz_r.npy'); lab=np.load('c833_split.npy'); info=json.load(open('pect_info.json'))
P=np.stack([u,zm,v],1); G=P[lab==0]; blue=P[lab==2]; red=P[lab==1]
S_DEG,D_DEG=35,15
from scipy.spatial import cKDTree
_d=cKDTree(G).query(blue)[0]; bb=blue[_d<=np.percentile(_d,3)].mean(0)   # 付け根 = 肩帯にいちばん近い 3% の点の平均（pect_info.json と同じ決め方）
c=blue.mean(0); w,V=np.linalg.eigh(np.cov((blue-c).T)); e1=V[:,2]; e3=V[:,0]
if np.dot(c-bb,e1)<0: e1=-e1
e2=np.cross(e3,e1)
local=(blue-bb)@np.stack([e1,e2,e3],1)
def place(side,s,d,base):
    s,d=np.radians(s),np.radians(d)
    a1=np.array([side*np.cos(d)*np.cos(s), np.cos(d)*np.sin(s), np.sin(d)])
    n=np.array([0,0,1.0]); n=n-np.dot(n,a1)*a1; n/=np.linalg.norm(n)
    a2=np.cross(n,a1)
    if a2[1]>0: a2=-a2
    return local[:,0:1]*a1+local[:,1:2]*a2+local[:,2:3]*n+base
baseR=bb.copy(); baseL=bb*np.array([-1,1,1])
R=place(1,S_DEG,D_DEG,baseR)
keep=R[:,0]>4                      # 正中線付近（u<=4mm）に飛んだ分割の残りを除く
local=local[keep]; R=R[keep]; L=place(-1,S_DEG,D_DEG,baseL)
GR=G[G[:,0]>=0]; GL=GR*np.array([-1,1,1]); GL=GL[GL[:,0]<0]; Gs=np.concatenate([GL,GR])
err=np.abs(L*[-1,1,1]-R).max()
np.savez('pect_posed.npz',left=L.astype(np.float32),right=R.astype(np.float32),
         girdle=Gs.astype(np.float32),girdle_orig=G.astype(np.float32))
def bx(p): return [round(float(x),1) for x in np.r_[p.min(0),p.max(0)]]
meta={'swept_deg':S_DEG,'down_deg':D_DEG,'base_right_uzv':[round(float(x),1) for x in baseR],'mirror_max_err_mm':float(err),
      'fin_points':int(len(R)),'dropped_cross_midline':int((~keep).sum()),
      'fin_reach_mm':round(float(np.linalg.norm(local,axis=1).max()),1),
      'left_bbox':bx(L),'right_bbox':bx(R),'girdle_bbox':bx(Gs),'girdle_points':int(len(Gs))}
json.dump(meta,open('pect_posed.json','w'),indent=1,ensure_ascii=False); print(meta)

# ---- 確認図: 前から / 腹側から / 横から（体の輪郭は皮膚の影）----
D=np.load('derolled6.npy',mmap_mode='r'); sub=np.asarray(D[150:420])>-400   # z 150..419 mm
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',15)
BODY=np.array([225,220,228],np.uint8)
def sil(mask): return np.where(mask[...,None],BODY,255).astype(np.uint8)
def view(parts,kind):
    # 体の影を mm 格子 (1px=1mm) に作り直してから点を重ねる
    if kind=='front':   # 横=u(-90..90) 縦=v(-60..120)
        m=sub.any(0); W,H=180,180; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-60)/1.47+150).astype(int); uu=((ii-90)/1.47+150).astype(int)
        ok=(vv>=0)&(vv<300)&(uu>=0)&(uu<300); img[ok]=sil(m)[vv[ok],uu[ok]]
        f=lambda p:(p[:,0]+90,p[:,2]+60)
    elif kind=='vent':  # 横=z(150..420) 縦=u(-90..90)
        m=sub.any(1); W,H=270,180; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; uu=((jj-90)/1.47+150).astype(int); zz=ii
        ok=(uu>=0)&(uu<300); img[ok]=sil(m)[zz[ok],uu[ok]]
        f=lambda p:(p[:,1]-150,p[:,0]+90)
    else:               # 横=z 縦=v  （右側から）
        m=sub.any(2); W,H=270,180; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-60)/1.47+150).astype(int); zz=ii
        ok=(vv>=0)&(vv<300); img[ok]=sil(m)[zz[ok],vv[ok]]
        f=lambda p:(p[:,1]-150,p[:,2]+60)
    for p,col in parts:
        i,j=f(p); i=i.astype(int); j=j.astype(int); ok=(i>=0)&(i<W)&(j>=0)&(j<H); img[j[ok],i[ok]]=col
    return Image.fromarray(img).resize((W*2,H*2),Image.NEAREST)
GR_,RD,BL=(90,90,90),(220,60,60),(40,110,220)
before=[(G,GR_),(red,RD),(blue,BL)]; after=[(Gs,GR_),(L,RD),(R,BL)]
rows=[('いまのCT',before),('決定後（後ろへ35°・下へ15°）',after)]
heads=['前から','腹側から（左が吻）','横から（左が吻）']
tiles=[[view(p,k) for k in ('front','vent','side')] for _,p in rows]
cw=[t.width for t in tiles[0]]; rh=[max(t.height for t in r) for r in tiles]
S=Image.new('RGB',(sum(cw)+40,sum(rh)+130),(255,255,255)); d=ImageDraw.Draw(S)
y=25
for (title,_),r,h in zip(rows,tiles,rh):
    d.text((5,y-22),title,fill=(0,0,0),font=F); x=0
    for k,t in enumerate(r):
        S.paste(t,(x,y)); d.text((x+4,y+2),heads[k],fill=(80,80,80),font=F); x+=t.width+20
    y+=h+40
d.text((5,y-25),'灰=肩帯（決定後は右半分を鏡映）、赤=左、青=右。決定後は青のひれを左右に使用（左は鏡映）。1マス=1mm を2倍表示',fill=(60,60,60),font=F)
S.save('pect_posed.png'); print(S.size)
