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
# 2026-10-18（プロデューサー「CTを原本にしない方が良いのでは？もっと良い事例を探してみて」→「その案で進めてください」）: HH_PELV_RODS=1 で、
#  腹びれの軟骨を CT の代わりに図と写真から作る（hh_finrods.py の見本: ウチワシュモクザメの透明標本（© Adam Summers）、Reynolds 1897 Fig. 8）。
#  ひれの板（e1・e2、付け根 B）の中に: 内側の縁から 2 mm 内に沿う基鰭軟骨（幅 2.4・厚さ 2.0 mm、膜の長さの 0.85 まで）、そこから体軸の後ろから外へ 45° で
#  平行に並ぶ 17 本の 2 節の棒（幅 2.0・厚さ 1.6 mm、膜の縁の 1.2 mm 内まで、節の間 0.5 mm）、付け根から正中までの腰帯の横棒（幅 4・厚さ 3 mm）。
#  CT の腹びれの軟骨（HH_pelv_R/L.ply）を置き換える（同じ名前で書くので、a6a_export_gltf.py・b1_rig.py の扱いは前と同じ）
if _os.environ.get('HH_PELV_RODS') == '1':
    import hh_finrods as R
    insideP = lambda X_, Y_: (lambda ix, iy: np.where((ix >= 0) & (ix < P2.shape[0]) & (iy >= 0) & (iy < P2.shape[1]), P2[np.clip(ix, 0, P2.shape[0] - 1), np.clip(iy, 0, P2.shape[1] - 1)], False))(np.round(np.atleast_1d(X_) / G).astype(int) - x0, np.round(np.atleast_1d(Y_) / G).astype(int) - y0)
    gx, gy = np.nonzero(P2); SX = (gx + x0) * G; SY = (gy + y0) * G
    U3 = B[0] + SX * e1[0] + SY * e2[0]
    smed = 1.0 if np.mean(SY[np.abs(U3) < np.median(np.abs(U3))]) > np.mean(SY) else -1.0   # 内側（正中に近い）縁の Y の向き
    Xmax = SX.max(); Xa, Xb = 2.0, 0.85 * Xmax
    def ymed(X_):
        m = np.abs(SX - X_) < G * 1.5
        return (SY[m].max() if smed > 0 else SY[m].min()) - smed * 2.0 if m.any() else 0.0
    to3 = lambda X_, Y_, W_=0.0: B + X_ * e1 + Y_ * e2 + W_ * nrm
    parts = []
    xs = np.arange(Xa, Xb + 0.01, 4.0); cl = [(x_, ymed(x_)) for x_ in xs]
    for (xa_, ya_), (xb_, yb_) in zip(cl[:-1], cl[1:]):
        d2 = np.array([xb_ - xa_, yb_ - ya_]); d2 /= np.linalg.norm(d2); w2 = np.array([-d2[1], d2[0]])
        parts.append(R.box(to3(xa_, ya_), to3(xb_, yb_), w2[0] * e1 + w2[1] * e2, 2.4, nrm, 2.0))
    # 棒の向き: 体軸（後ろ）から外へ 45°（Reynolds 1897 Fig. 8 で、腹びれの棒の多くは外・後ろへ向く）。60° を基鰭軟骨から測った版は、腹から見て真横を向いた
    ax2 = np.array([e1[1], e2[1]]); ax2 /= np.linalg.norm(ax2); lat2 = np.array([-ax2[1], ax2[0]])
    if np.sign(lat2[1]) == np.sign(smed): lat2 = -lat2                  # 内側（正中）と反対へ
    dirR = np.cos(np.radians(45)) * ax2 + np.sin(np.radians(45)) * lat2
    NR = 17; rod_info = []
    for k in range(NR):
        xk = Xa + 2 + (Xb - Xa - 4) * k / (NR - 1); yk = ymed(xk) - smed * 1.4
        d = dirR; p = np.array([xk, yk])
        s = np.arange(0, 80, 0.2); q = p[None] + s[:, None] * d[None]
        ok = insideP(*(q + 1.2 * d).T) & insideP(*q.T)
        bad = np.nonzero(~ok)[0]; L = float(s[bad[0] - 1]) if len(bad) and bad[0] > 0 else 0.0
        if L < 3: continue
        Lm = 0.55 * L; w2 = np.array([-d[1], d[0]])
        for a_, b_ in [(0, Lm - 0.25), (Lm + 0.25, L)]:
            pa, pb = p + d * a_, p + d * b_
            parts.append(R.box(to3(*pa), to3(*pb), w2[0] * e1 + w2[1] * e2, 2.0, nrm, 1.6))   # 幅 2 mm（透明標本の写真で棒の幅 ≒ 棒の間）
        rod_info.append(round(L, 1))
    b0 = to3(0.0, ymed(Xa) if False else 0.0); bm_ = b0.copy(); bm_[0] = 0.0
    parts.append(R.box(b0, bm_, np.array([0.0, 1.0, 0.0]), 4.0, np.array([0.0, 0.0, 1.0]), 3.0))   # 腰帯: 付け根から正中（u = 0）へ、体軸の向きに幅 4、背腹に厚さ 3
    Vr, Fr = R.merge(parts)                                   # (u, z, v) の mm、外向き
    Vb = np.stack([Vr[:, 1], Vr[:, 0], -Vr[:, 2]], 1) / 1000.0   # Blender（x = z、y = u、z = −v）、向きは変わらない
    write_ply(f'{OUT}/HH_pelv_R.ply', Vb, Fr[:, ::-1])         # write_ply は面を裏返して書く（マーチングキューブの内向きの面のため）
    VbL = Vb.copy(); VbL[:, 1] = -VbL[:, 1]
    write_ply(f'{OUT}/HH_pelv_L.ply', VbL, Fr)                # 鏡映で回りが逆になる
    info['rods'] = {'radials': len(rod_info), 'radial_len_mm': rod_info, 'medial_sign': smed, 'basipterygium_mm': [Xa, round(Xb, 1)]}
    json.dump(info, open('a5_pelvmem.json', 'w'), indent=1); print('pelvic rods', info['rods'])
