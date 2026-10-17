# A5 腹びれの膜（仮）: 出典のある写真がまだ無いので、決めた向きの腹びれの骨の形を、板の面の中で 5 mm 広げた膜にする
#  厚さ 3 mm（付け根）→ 1.5 mm（先）。右を作り、左は鏡映
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os as _os
from scipy import ndimage as ndi
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX=0.735; U0,V0=-180.0,-150.0
P=np.load('pelvic_posed.npz')['right'].astype(float)          # (u,z,v)
c=P.mean(0); w,Vv=np.linalg.eigh(np.cov((P-c).T)); e1,e2,nrm=Vv[:,2],Vv[:,1],Vv[:,0]
B=np.array(json.load(open('pelvic_info.json'))['right_base_uzv'])
if np.dot(c-B,e1)<0: e1=-e1
X=(P-B)@e1; Y=(P-B)@e2
G=0.4; xi=np.round(X/G).astype(int); yi=np.round(Y/G).astype(int); x0,y0=xi.min()-20,yi.min()-20
P2=np.zeros((xi.max()-x0+21,yi.max()-y0+21),bool); P2[xi-x0,yi-y0]=True
P2=ndi.binary_fill_holes(ndi.binary_closing(P2,iterations=6)); P2=ndi.binary_dilation(P2,iterations=int(5/G))
# 2026-10-17 直し（プロデューサー「全てのヒレの色のつき方が変です。サイズを調整した時に色付けする箇所の修正を忘れたのではないでしょうか？」→「進めて」）:
#  HH_PELV_SCALE（例 1.4）で、膜の形を付け根（B）を中心に板の面の中でその倍に広げる（軟骨は CT のまま）。前は軟骨を 5 mm 広げただけで、
#  横から見て体の線から出る高さが全長比 0.037、参考の図は 0.058（Duane Raver）・0.040（FMIB 45527）だった（計画書「腹側のひれの大きさの検証」）
_ps=float(_os.environ.get('HH_PELV_SCALE','1') or 1)
if _ps!=1:
    px,py=np.nonzero(P2); X2=(px+x0)*G*_ps; Y2=(py+y0)*G*_ps
    xi2=np.round(X2/G).astype(int); yi2=np.round(Y2/G).astype(int); x0,y0=xi2.min()-20,yi2.min()-20
    P2=np.zeros((xi2.max()-x0+21,yi2.max()-y0+21),bool); P2[xi2-x0,yi2-y0]=True
    P2=ndi.binary_fill_holes(ndi.binary_closing(P2,iterations=int(np.ceil(_ps))+1))
gx,gy=np.nonzero(P2); LX=(gx+x0)*G; LY=(gy+y0)*G
th=np.clip(3.0-1.5*np.clip(LX,0,None)/max(LX.max(),1),1.5,3.0)
pts=[]
for wv in np.arange(-1.5,1.51,0.35):
    sel=np.abs(wv)<=th/2; pts.append(B+np.outer(LX[sel],e1)+np.outer(LY[sel],e2)+wv*nrm)
Q=np.concatenate(pts)
iz=np.round(Q[:,1]/VX).astype(int); iv=np.round((Q[:,2]-V0)/VX).astype(int); iu=np.round((Q[:,0]-U0)/VX).astype(int)
cart=np.load('a4_pelv_R.npz'); cm=cart['field']>0.5; co=cart['origin']; cz,cv,cu=np.nonzero(cm)
iz=np.r_[iz,cz+co[0]]; iv=np.r_[iv,cv+co[1]]; iu=np.r_[iu,cu+co[2]]
lo=np.array([iz.min(),iv.min(),iu.min()])-4; hi=np.array([iz.max(),iv.max(),iu.max()])+5
Mk=np.zeros(hi-lo,bool); Mk[iz-lo[0],iv-lo[1],iu-lo[2]]=True
Mk=ndi.binary_fill_holes(ndi.binary_closing(Mk,iterations=1))
cartm=np.zeros_like(Mk); cartm[cz+co[0]-lo[0],cv+co[1]-lo[1],cu+co[2]-lo[2]]=True; Mk|=ndi.binary_dilation(cartm)
Fd=ndi.gaussian_filter(Mk.astype(np.float32),0.6)
v,f,_,_=marching_cubes(np.pad(Fd,1),0.5,allow_degenerate=False); v=v-1+lo
write_ply(f'{OUT}/HH_pelvmem_R.ply',to_blender(v),f)
vL=v.copy(); vL[:,2]=(-(U0+vL[:,2]*VX)-U0)/VX
write_ply(f'{OUT}/HH_pelvmem_L.ply',to_blender(vL),f[:,::-1])
info={'fin_len_mm':round(float(LX.max()),1),'faces':int(len(f)),'margin_mm':5,'scale':_ps}
json.dump(info,open('a5_pelvmem.json','w'),indent=1); print(info)
