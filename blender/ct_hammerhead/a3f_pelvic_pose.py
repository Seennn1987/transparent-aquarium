# A3 腹びれの姿勢（2026-10-14 プロデューサー決定「右を使う。後ろへ60度、下へ20度」）
#  - 右の塊（3064+3149+3077）を左右に使い、左は鏡映
#  - 付け根: 右の元の付け根（3048 にいちばん近い 3% の点の平均）とその鏡映
# 座標: derolled2 の (u 左右, z 吻→尾, v 背-/腹+) mm。入力 pelvic_uvz.npz（a3e0_pelvic_look.py）
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import cKDTree
exec(open(hh_paths.script('a3e_pelvic_options.py')).read().split("D=np.load('derolled2.npy'")[0])   # right, left, bb, local, place など
S_DEG,D_DEG=60,20
R=place(1,S_DEG,D_DEG); L=place(-1,S_DEG,D_DEG)
err=float(np.abs(L*[-1,1,1]-R).max())
np.savez('pelvic_posed.npz',left=L.astype(np.float32),right=R.astype(np.float32),mid=mid.astype(np.float32))
def bx(p): return [round(float(x),1) for x in np.r_[p.min(0),p.max(0)]]
meta={'source':'right (3064+3149+3077)','swept_deg':S_DEG,'down_deg':D_DEG,'base_right_uzv':[round(float(x),1) for x in bb],
      'mirror_max_err_mm':err,'points':int(len(R)),'reach_mm':round(float(np.linalg.norm(local,axis=1).max()),1),
      'left_bbox':bx(L),'right_bbox':bx(R),'min_gap_LR_mm':round(float(cKDTree(L).query(R)[0].min()),1)}
json.dump(meta,open('pelvic_posed.json','w'),ensure_ascii=False,indent=1); print(meta)
# 確認図: 前・腹側・横から、いまの CT と決定後
D=np.load('derolled2.npy',mmap_mode='r'); body=np.asarray(D[420:560])>-400
F=hh_paths.font(14)
def view(parts,kind):
    if kind=='front':
        m=body.any(0); W,H=130,140; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-50)/1.47+150).astype(int); uu=((ii-65)/1.47+150).astype(int)
        img[m[vv,uu]]=(225,220,228); f=lambda p:(p[:,0]+65,p[:,2]+50)
    elif kind=='vent':
        m=body.any(1); W,H=140,130; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; uu=((jj-65)/1.47+150).astype(int)
        img[m[ii,uu]]=(225,220,228); f=lambda p:(p[:,1]-420,p[:,0]+65)
    else:
        m=body.any(2); W,H=140,140; img=np.full((H,W,3),255,np.uint8)
        jj,ii=np.mgrid[0:H,0:W]; vv=((jj-50)/1.47+150).astype(int)
        img[m[ii,vv]]=(225,220,228); f=lambda p:(p[:,1]-420,p[:,2]+50)
    for p,col in parts:
        i,j=f(p); i=i.astype(int); j=j.astype(int); ok=(i>=0)&(i<W)&(j>=0)&(j<H); img[j[ok],i[ok]]=col
    return Image.fromarray(img).resize((W*2,H*2),Image.NEAREST)
GR,RD,BL,OR=(90,90,90),(220,60,60),(40,110,220),(230,150,20)
rows=[('いまのCT',[(spine,GR),(mid,OR),(left,RD),(right,BL)]),('決定後（右を使う・後ろへ60°・下へ20°）',[(spine,GR),(mid,OR),(L,RD),(R,BL)])]
heads=['前から','腹側から（左が吻）','横から（左が吻）']
tiles=[[view(p,k) for k in ('front','vent','side')] for _,p in rows]
Wt=sum(t.width for t in tiles[0])+40; rh=max(t.height for t in tiles[0])
S=Image.new('RGB',(Wt,2*rh+110),(255,255,255)); d=ImageDraw.Draw(S); y=22
for (title,_),r in zip(rows,tiles):
    d.text((4,y-20),title,fill=(0,0,0),font=F); x=0
    for k,t in enumerate(r): S.paste(t,(x,y)); d.text((x+4,y+2),heads[k],fill=(80,80,80),font=F); x+=t.width+20
    y+=rh+40
d.text((4,y-22),'灰=背骨、橙=正中の小片（腰帯か未確認）、赤=左、青=右。決定後は右の腹びれを左右に使用（左は鏡映）',fill=(60,60,60),font=F)
S.save('pelvic_posed.png'); print(S.size)
