# Digimorph の肋骨を 1 本ずつ取り出し、背骨に対する向きを測る
import numpy as np, scipy.ndimage as nd
from scipy.spatial import cKDTree
Q=np.load('dm_uwL.npy'); z=np.load('dm_spine_s.npz'); C,arc,T,N=z['C'],z['arc'],z['T'],z['N']
tr=cKDTree(C); d,i=tr.query(Q[:,:2]); s=arc[i]; ven=-((Q[:,:2]-C[i])*N[i]).sum(1); L=Q[:,2]
ok=(i>2)&(i<len(C)-3)
m=ok&(ven>2.5)&(ven<48)&(np.abs(L)<12)&(np.abs(L)>0.8)&(s>18)
P=Q[m]; h=0.15; lo=P.min(0); g=((P-lo)/h).astype(int)
G=np.zeros(g.max(0)+1,bool); G[tuple(g.T)]=True; G=nd.binary_closing(G,iterations=1)
lab,n=nd.label(G,np.ones((3,3,3))); sz=np.bincount(lab.ravel()); sz[0]=0
rows=[]
for c in np.nonzero(sz>400)[0]:
    V=np.argwhere(lab==c)*h+lo
    dd,ii=tr.query(V[:,:2]); vs=arc[ii]; vv=-((V[:,:2]-C[ii])*N[ii]).sum(1)
    if np.ptp(vv)<15: continue          # 肋骨は腹側へ長い。短い塊（四肢のかけらなど）は除く
    # 背骨に近い側 1/3 の点で、矢状面の向き（体軸の接線に対する角）と横への開き
    near=vv<np.percentile(vv,40); A=V[near]
    u,_,vt=np.linalg.svd(A-A.mean(0),full_matrices=False); e=vt[0]
    if e@np.r_[-N[ii[near]].mean(0),0]<0: e=-e        # 腹側を向く
    k=int(np.median(ii[near])); t=np.r_[T[k],0]; nv=np.r_[-N[k],0]; lat=np.r_[0,0,1.0]
    rake=np.degrees(np.arctan2(e@t, e@nv))           # 0 = 背骨に垂直、+ = 後ろへ寝る
    side=np.sign(np.median(V[:,2])); splay=np.degrees(np.arctan2(abs(e@lat),e@nv))
    rows.append((round(np.median(vs),1),int(side),round(np.ptp(vv),1),round(rake,1),round(splay,1),len(V)))
rows.sort()
print('s(mm) side ventral_extent(mm) rake(deg) splay(deg) nvox')
for r in rows: print(r)
R=np.array(rows); print('rake median',np.median(R[:,3]),'IQR',np.percentile(R[:,3],[25,75]),'splay median',np.median(R[:,4]))
