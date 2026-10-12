# 肋骨を根元から 1 本ずつたどる（向きを保つ）。ribs9 の根元（各肋骨ラベルの背骨に最も近い 5%）から出発し、
# 各点の管の向き（ヘッセ行列、r9_TT.npy）に沿って 1 ボクセルずつ進む。進む先は、前の向きから 30° 以内の円錐の中の、
# 2.5 ボクセル以内の骨のボクセル（前へ最も進むもの）。骨が無ければ同じ向きで進み、6 歩（0.6 mm）無ければ止める。
# 曲がりは 1 歩 12° まで。たどった線から 2.5 ボクセル以内の肋骨のボクセルを、その肋骨のものにする（近い方の線）。
import numpy as np, sys, json
from scipy.spatial import cKDTree
src,dst=sys.argv[1],sys.argv[2]
B=np.load(src); z=np.load('r9_dbg.npz'); U,du=z['U'],z['du']; TT=np.load('r9_TT.npy').astype(np.float64)
lab=B[tuple(U.T)].astype(np.int32); isrib=(lab>=160)&(lab<202)
R_=np.nonzero(isrib|(du>18))[0]; P=U[R_].astype(float); kt=cKDTree(P)
C=np.load('axis5_s.npy')*2+0.5; tr=cKDTree(C)
tracks={}
for l in range(160,202):
    m=isrib&(lab==l)
    if m.sum()<40: continue
    A=U[m].astype(float); root=A[du[m]<=np.percentile(du[m],5)].mean(0)
    # 最初の向き: 根元から、この肋骨のラベルの点で根元から 1〜2 mm の点の重心へ
    dr=np.linalg.norm(A-root,axis=1); ring=A[(dr>10)&(dr<20)]
    if len(ring)<5: continue
    e=ring.mean(0)-root; e/=np.linalg.norm(e)
    p=root.copy(); pts=[p.copy()]; miss=0
    for step in range(600):
        nb=kt.query_ball_point(p+e,2.5)
        best=None
        if nb:
            Q=P[nb]; v=Q-p; dv=np.linalg.norm(v,axis=1)+1e-9; cosv=(v@e)/dv
            ok=(cosv>np.cos(np.radians(30)))&(dv>0.5)
            if ok.any():
                j=np.argmax(np.where(ok,v@e,-1e9)); best=Q[j]; gi=R_[nb[j]]
        if best is None:
            miss+=1
            if miss>6: break
            p=p+e; pts.append(p.copy()); continue
        miss=0
        t=TT[gi]; t=t if t@e>0 else -t
        f=0.6*e+0.4*t; f/=np.linalg.norm(f)
        ang=np.degrees(np.arccos(np.clip(f@e,-1,1)))
        if ang>12: 
            k=np.radians(12)/np.radians(ang); f=e+(f-e)*k; f/=np.linalg.norm(f)
        e=f; p=best.copy(); pts.append(p)
    pts=np.array(pts[:len(pts)-miss] if miss else pts)
    if pts.ndim!=2 or len(pts)<3: continue
    tracks[l]=pts
    print(l,'steps',len(pts),'length mm',round(np.sum(np.linalg.norm(np.diff(pts,axis=0),axis=1))*0.104,1))
np.savez('ribtracks2.npz',**{str(k):v for k,v in tracks.items()})
# ボクセルの割り当て
TL=[];TP=[]
for l,pts in tracks.items(): TP.append(pts); TL.append(np.full(len(pts),l))
TP=np.concatenate(TP); TL=np.concatenate(TL); tt=cKDTree(TP)
ri=np.nonzero(isrib)[0]; dd,jj=tt.query(U[ri])
newlab=lab.copy(); close=dd<=3.0
newlab[ri[close]]=TL[jj[close]]
print('rib voxels',len(ri),'assigned by tracks',int(close.sum()),'changed',int((newlab!=lab).sum()))
B[tuple(U.T)]=newlab.astype(B.dtype); np.save(dst,B)
