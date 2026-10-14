# A7h: エラの骨 5 対と底鰓（basibranchial）を作る。
#  形の順序と部品（咽鰓・上鰓・角鰓・下鰓・底鰓）は BIODIDAC の Squalus acanthias の内臓骨格の図（I. Livingstone、CC BY-NC 4.0、
#  https://omeka.uottawa.ca/biodidac/items/show/5134）と Kennesaw State Univ. 実習資料に従う。
#  置き場所は CT から: 左のエラ穴の帯（a7_slit.npy、エラの空気の内側の端 a7_uin.npy）。左で作り右へ鏡映する（右のエラは潰れている）
#  出力: mesh/HH_gill.ply、a7_gill_arches.json
import numpy as np, json
from scipy import ndimage as nd
from skimage.measure import marching_cubes
exec(open('a4_mesh.py').read().split("which=sys.argv[1]")[0])
d=np.load('a7_gill_field.npz'); og=d['origin']; Gg=float(d['step'])
uin,uout=np.load('a7_uin.npy')
def u_inner(z,v):
    iz=int(round((z-og[0])/Gg)); iv=int(round((v-og[1])/Gg))
    win=uin[max(iz-6,0):iz+7,max(iv-6,0):iv+7]; w=win[np.isfinite(win)]
    return float(np.clip(np.median(w),-36,-20)) if w.size>20 else -26.0
Z_D=[128,134,140,146,152]          # 背側の端（v=0）の位置
SLOPE=0.36                          # 腹側へ 1 mm 下がるごとに後ろへ（エラ穴の帯の傾き、約 20°）
arches=[]; segs=[]                  # segs: (点の列 (n,3) z,u,v, 半径)
GAP=0.7
def poly(pts,n=40):
    pts=np.asarray(pts,float); t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    s=np.linspace(0,t[-1],n); return np.stack([np.interp(s,t,pts[:,i]) for i in range(3)],1)
def trim(P,g):
    t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))]; keep=(t>=g)&(t<=t[-1]-g); return P[keep]
for k,zd in enumerate(Z_D):
    sc=1.0-0.04*k
    zz=lambda v: zd+v*SLOPE
    ua=u_inner(zz(24),24)+1.5        # 外側の角（上鰓と角鰓のつなぎ目）はエラの空気の内側の端のすぐ内
    pb=[(zd+9,-6,4),(zd+3,-11,2.5),(zz(2),-16,2)]
    eb=[(zz(2),-16,2),(zz(9),(ua-16)/2-2,8),(zz(22*sc),ua,22*sc)]
    cb=[(zz(22*sc),ua,22*sc),(zz(34*sc),ua+3,34*sc),(zz(44*sc),-15,44*sc)]
    hb=[(zz(44*sc),-15,44*sc),(zz(48*sc)+3,-9,48*sc),(zz(50*sc)+7,-3,50*sc)]
    for name,pts,r in (('pharyngobranchial',pb,1.0),('epibranchial',eb,1.2),('ceratobranchial',cb,1.4),('hypobranchial',hb,1.1)):
        P=trim(poly(pts,60),GAP); segs.append((P,r)); arches.append(dict(arch=k+1,part=name,points_zuv_mm=np.round(np.asarray(pts),1).tolist(),radius_mm=r))
# 底鰓: 正中の板（下鰓の内の端をつなぐ）
zb0=Z_D[0]+50*SLOPE+7-4; zb1=Z_D[-1]+50*0.84*SLOPE+7+10
B=poly([(zb0,0,50.5),(zb1,0,48)],60); segs.append((B,1.8)); arches.append(dict(arch=0,part='basibranchial',points_zuv_mm=[[zb0,0,50.5],[zb1,0,48]],radius_mm=1.8))
# 体積にして面を作る（0.35 mm）
G=0.35; Z0,Z1,U0b,U1b,V0b,V1b=110.0,205.0,-50.0,50.0,-10.0,62.0
shape=(int((Z1-Z0)/G),int((V1b-V0b)/G),int((U1b-U0b)/G))
mark=np.zeros(shape,bool); rad=np.zeros(shape,np.float32)
for P,r in segs:
    for sgn in ((-1,1) if np.abs(P[:,1]).max()>0.5 else (1,)):
        Pd=poly(P,int(np.linalg.norm(np.diff(P,axis=0),axis=1).sum()/0.1)+2)
        iz=np.round((Pd[:,0]-Z0)/G).astype(int); iv=np.round((Pd[:,2]-V0b)/G).astype(int); iu=np.round((sgn*Pd[:,1]-U0b)/G).astype(int)
        mark[iz,iv,iu]=True; rad[iz,iv,iu]=r
dist,ind=nd.distance_transform_edt(~mark,sampling=G,return_indices=True)
R=rad[ind[0],ind[1],ind[2]]; fld=nd.gaussian_filter((R-dist).astype(np.float32),1.2); del ind
v,f,_,_=marching_cubes(np.pad(fld,1,constant_values=-5),0.0,allow_degenerate=False); v-=1
Pm=np.stack([Z0+v[:,0]*G,U0b+v[:,2]*G,-(V0b+v[:,1]*G)],1)/1000
write_ply(f'{OUT}/HH_gill.ply',Pm,f); print('gill',len(v),len(f))
json.dump(dict(source='BIODIDAC Squalus acanthias visceral skeleton (I. Livingstone, CC BY-NC 4.0) https://omeka.uottawa.ca/biodidac/items/show/5134 / position from CT left gill air (a7_slit.npy)',
               z_dorsal_mm=Z_D,slope=SLOPE,elements=arches),open('a7_gill_arches.json','w'),indent=1)
