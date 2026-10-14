# 眼球の位置と大きさ（2026-10-14、仮）
#   カメレオンの眼窩の間の仕切り（眼窩間中隔）は膜で、頭骨を横から透かすと眼窩は輪の穴に見える（X 線・写真 01 でも輪）。
#   1. 頭骨（静止の CT の形）の主軸: 最も長い向き = 前後、最も薄い向き = 左右（頭骨は横に薄い）、残り = 背腹
#   2. 強膜輪（眼球の前の縁の小さな骨の輪）: CT では左だけ写る（外径 約 4.3 mm の輪、頭骨のメッシュの別の部品）。
#      その中心（前後・背腹）を眼球の中心にする。右は左右の鏡（頭骨の左右の向きで）
#   3. 半径: 横から写した像で、輪の中心から眼窩の縁の骨（輪と、左右 1 mm の正中を除く）までの最短（0.05% 点）
#   4. 左右の位置: 左右の眼球が正中の膜（眼窩間中隔）を挟んで触れないよう、中心を正中から半径 + 0.2 mm に置く（仮）。
#      このとき強膜輪は眼球の外側の面の少し内にあり、眼球は輪より外へ約 0.9 mm ふくらむ（生体の目も縁より外へ出る）
#   出力: eyes.json（モデル座標の展示の姿勢での中心、半径 mm）
import numpy as np, scipy.ndimage as nd, json
from scipy.spatial import Delaunay
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k']); MM=k
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
d=np.load('chameleon_body_ct.npz')
ih=bn.index('head'); M=Mp[ih]; x=ct2m(d['head__v'])/MM          # 静止、mm
c0=x.mean(0); U,S,Vt=np.linalg.svd(x-c0,full_matrices=False)
ax_len,ax_h,ax_w=Vt[0],Vt[1],Vt[2]
q=x-c0; A=q@ax_len; B=q@ax_h; W=q@ax_w
print('skull extents mm: length %.1f height %.1f width %.1f'%(np.ptp(A),np.ptp(B),np.ptp(W)))
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components
f=d['head__f']; n=len(x)
Am=sp.coo_matrix((np.ones(3*len(f)),(f[:,[0,1,2]].ravel(),f[:,[1,2,0]].ravel())),shape=(n,n))
nc,lab=connected_components(Am,directed=False); sz=np.bincount(lab)
# 強膜輪: 1,000〜10,000 頂点の部品で、前後・背腹の広がりがどちらも 3.5〜5 mm、左右の広がり 3 mm 未満、正中から 2 mm より外
ring=None
for c in np.argsort(-sz):
    m=lab==c
    if not (1000<=sz[c]<=10000): continue
    ea,eb,ew=np.ptp(A[m]),np.ptp(B[m]),np.ptp(W[m])
    if 3.5<ea<5 and 3.5<eb<5 and ew<3 and abs(np.median(W[m]))>2: ring=m; break
assert ring is not None
ca,cb=A[ring].mean(),B[ring].mean(); rr=float(np.median(np.hypot(A[ring]-ca,B[ring]-cb)))
r2=np.hypot(A-ca,B-cb); other=~((r2<rr+0.6)&(np.abs(W)>2.0))&(np.abs(W)>1.0)
R=float(np.round(np.percentile(r2[other&(r2<6)],0.05),2))
print('scleral ring: centre (length, height) %.2f %.2f mm, mean radius %.2f mm, lateral %.2f mm; orbit radius %.2f mm'%(ca,cb,rr,np.median(W[ring]),R))
# 半径は測った眼窩の半径をそのまま使う
eyes={}
for side in (1,-1):
    wc=side*(R+0.2)
    cm=(c0+ca*ax_len+cb*ax_h+wc*ax_w)*MM; cmp_=M[:3,:3]@cm+M[:3,3]
    eyes[side]=dict(centre_rest_model=cm.tolist(),centre_model=cmp_.tolist(),radius_mm=R,lateral_mm=wc)
yy=[v['centre_model'][1] for v in eyes.values()]
eyes={('eye_r' if v['centre_model'][1]==max(yy) else 'eye_l'):v for v in eyes.values()}
for n_,v in eyes.items(): print(n_, 'radius %.2f mm'%v['radius_mm'], 'lateral %.2f mm'%v['lateral_mm'])
json.dump(eyes,open('eyes.json','w'),indent=1)
