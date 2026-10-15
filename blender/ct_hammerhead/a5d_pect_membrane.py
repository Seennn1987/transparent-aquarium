# A5 胸びれの膜: 写真（NOAA、背中から、パブリックドメイン）の胸びれの外形を、決めた向きの胸びれの骨に合わせて付ける
#  写真の右の個体の、画面の左の胸びれ（先まで写っている方）を使い、鏡映して左右に使う（画面の右の胸びれは短く写っている）
#  写真の縮尺: 頭の翼の両端の距離 228.9 px = 頭の幅 266 mm（決定後）。写真は 5.0° 回して頭を水平にする
#  置き方: 写真で、ひれの付け根（胴の縁）の中点から先端への向きを、骨の向き（後ろへ 35°・下へ 15°）に合わせる。
#         付け根は、骨の付け根から骨の向きに進んで体の膜の外へ出る点から 6 mm 内側（体と重ねる）
#  厚さ: 付け根 4 mm → 先 1.5 mm。骨（1 ボクセル広げたもの）を必ず膜に含める
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX=0.735; U0,V0=-180.0,-150.0
d=np.load('photo_pect.npz'); fin=d['L']; L0,R0,L1,R1=d['trunk']
tl,tr=np.array([326,86.]),np.array([554,66.]); ang=np.arctan2(tr[1]-tl[1],tr[0]-tl[0]); mid=(tl+tr)/2
s=266.0/np.linalg.norm(tr-tl)
def to_mm(x,y):
    p=np.stack([x-mid[0],y-mid[1]],1); c,sn=np.cos(-ang),np.sin(-ang)
    q=np.stack([p[:,0]*c-p[:,1]*sn,p[:,0]*sn+p[:,1]*c],1)*s
    return -q[:,0], q[:,1]            # 鏡映して右側（u>0）に。z は頭の翼の線から後ろへ
yy,xx=np.nonzero(fin); pu,pz=to_mm(xx.astype(float),yy.astype(float))
# 付け根: 胴の縁の線に 2 px 以内の点
a=(yy-195)/110.0; edge=L0*(1-a)+L1*a
base=np.abs(xx-edge)<=2
bu,bz=pu[base],pz[base]; Bp=np.array([bu.mean(),bz.mean()])
dd=np.hypot(pu-Bp[0],pz-Bp[1]); tip=np.array([pu[np.argmax(dd)],pz[np.argmax(dd)]])
ex=(tip-Bp)/np.linalg.norm(tip-Bp); ey=np.array([ex[1],-ex[0]])
if ey[1]>0: ey=-ey                                   # 前（z が小さい方）を向く
X=(pu-Bp[0])*ex[0]+(pz-Bp[1])*ex[1]; Y=(pu-Bp[0])*ey[0]+(pz-Bp[1])*ey[1]
info={'photo_scale_mm_per_px':round(s,3),'fin_len_mm':round(float(X.max()),1),'base_len_mm':round(float(np.ptp((bu-Bp[0])*ey[0]+(bz-Bp[1])*ey[1])),1),
      'photo_sweep_deg_from_lateral':round(float(np.degrees(np.arctan2(ex[1],ex[0]))),1)}
# 2D の膜の形（0.4 mm 格子）
G=0.4; xi=np.round(X/G).astype(int); yi=np.round(Y/G).astype(int)
x0,y0=xi.min(),yi.min(); P2=np.zeros((xi.max()-x0+1,yi.max()-y0+1),bool); P2[xi-x0,yi-y0]=True
P2=ndi.binary_fill_holes(ndi.binary_closing(P2,iterations=int(1.5/G)+1))
gx,gy=np.nonzero(P2); LX=(gx+x0)*G; LY=(gy+y0)*G
# 骨の向き（a4d_fins / pect_pose と同じ）
pe=json.load(open('pect_posed.json')); B=np.array(pe['base_right_uzv'])   # (u,z,v)
sd,dn=np.radians(35),np.radians(15)
a1=np.array([np.cos(dn)*np.cos(sd),np.cos(dn)*np.sin(sd),np.sin(dn)])
n=np.array([0,0,1.0]); n=n-np.dot(n,a1)*a1; n/=np.linalg.norm(n); a2=np.cross(n,a1)
if a2[1]>0: a2=-a2
# 体の膜の外へ出る点
S=np.load('a5_S.npy',mmap_mode='r')
def inside(p):
    iz=int(round(p[1]/VX)); iv=int(round((p[2]-V0)/VX)); iu=int(round((p[0]-U0)/VX)); return bool(S[iz,iv,iu])
t=0.0
while inside(B+t*a1) and t<80: t+=0.5
P0=B+(t-6.0)*a1; info['surface_from_base_mm']=t   # ひれ全体を 6 mm 体の中へ入れて、付け根を体と重ねる
# 3D の点（厚さ方向に並べる）
th=np.clip(4.0-2.5*np.clip(LX,0,None)/max(LX.max(),1),1.5,4.0)
pts=[]
for w in np.arange(-2.0,2.01,0.35):
    sel=np.abs(w)<=th/2
    pts.append(P0+np.outer(LX[sel],a1)+np.outer(LY[sel],a2)+w*n)
P=np.concatenate(pts)
iz=np.round(P[:,1]/VX).astype(int); iv=np.round((P[:,2]-V0)/VX).astype(int); iu=np.round((P[:,0]-U0)/VX).astype(int)
cart=np.load('a4_pect_R.npz'); cm=cart['field']>0.5; co=cart['origin']; cz,cv,cu=np.nonzero(cm)
iz=np.r_[iz,cz+co[0]]; iv=np.r_[iv,cv+co[1]]; iu=np.r_[iu,cu+co[2]]
lo=np.array([iz.min(),iv.min(),iu.min()])-4; hi=np.array([iz.max(),iv.max(),iu.max()])+5
Mk=np.zeros(hi-lo,bool); Mk[iz-lo[0],iv-lo[1],iu-lo[2]]=True
Mk=ndi.binary_closing(Mk,iterations=1); Mk=ndi.binary_fill_holes(Mk)
cartm=np.zeros_like(Mk); cartm[cz+co[0]-lo[0],cv+co[1]-lo[1],cu+co[2]-lo[2]]=True
Mk|=ndi.binary_dilation(cartm)
info['cartilage_outside_membrane_vox']=int((cartm&~Mk).sum())
Fd=ndi.gaussian_filter(Mk.astype(np.float32),0.6)
v,f,_,_=marching_cubes(np.pad(Fd,1),0.5,allow_degenerate=False); v=v-1+lo
write_ply(f'{OUT}/HH_pectmem_R.ply',to_blender(v),f)
vL=v.copy(); vL[:,2]=(-(U0+vL[:,2]*VX)-U0)/VX          # u を反転（左）
write_ply(f'{OUT}/HH_pectmem_L.ply',to_blender(vL),f[:,::-1])
np.savez_compressed('a5_pectmem.npz',mask=Mk,origin=lo)
info['faces']=int(len(f)); json.dump(info,open('a5_pectmem.json','w'),ensure_ascii=False,indent=1); print(info)
