# 肋骨の帰属: 管（肋骨）の向きに沿ってだけ進みやすい最短路で、椎骨の近くの種から広げる
import numpy as np, scipy.ndimage as nd, sys
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from skimage.feature import hessian_matrix, hessian_matrix_eigvals
src,dst=sys.argv[1],sys.argv[2]; ALPHA=float(sys.argv[3]) if len(sys.argv)>3 else 6.0
B=np.load(src); X=np.load('ct_ms50726_vol4max.npz')['v']
C=np.load('axis5_s.npy')*2+0.5; tr=cKDTree(C); J=np.load('J.npy'); s=np.arange(len(C))*0.1
vid=(np.searchsorted(J,s)+1).astype(np.int16)+100
P=np.argwhere((B>101)&(B<=126)); d,ii=tr.query(P); trunk=s[ii]<104.0
selU=(d>20)&trunk; U=P[selU]; seedsel=(d[selU]<30)
lo=U.min(0)-4; hi=U.max(0)+5; sl=tuple(slice(a,b) for a,b in zip(lo,hi))
Xc=nd.gaussian_filter(X[sl].astype(np.float32),0.5)
H=hessian_matrix(Xc,sigma=1.2,order='rc',use_gaussian_derivatives=False)
q=U-lo
Hm=np.stack([np.stack([H[0][tuple(q.T)],H[1][tuple(q.T)],H[2][tuple(q.T)]],-1),
             np.stack([H[1][tuple(q.T)],H[3][tuple(q.T)],H[4][tuple(q.T)]],-1),
             np.stack([H[2][tuple(q.T)],H[4][tuple(q.T)],H[5][tuple(q.T)]],-1)],-2)
del H
w,v=np.linalg.eigh(Hm); k=np.argmin(np.abs(w),1); T=v[np.arange(len(U)),:,k]   # 管の向き
idx=-np.ones(hi-lo,np.int64); idx[tuple(q.T)]=np.arange(len(U))
rows=[];cols=[];wts=[]
offs=[(a,b,c) for a in (-1,0,1) for b in (-1,0,1) for c in (-1,0,1) if (a,b,c)>(0,0,0)]
for o in offs:
    o=np.array(o); qq=q+o; inb=np.all((qq>=0)&(qq<hi-lo),1)
    j=np.full(len(U),-1); j[inb]=idx[tuple(qq[inb].T)]; m=j>=0
    a=np.nonzero(m)[0]; b=j[m]; L=np.linalg.norm(o); u=o/L
    c=0.5*(np.abs(T[a]@u)+np.abs(T[b]@u))
    rows.append(a); cols.append(b); wts.append(L*(1+ALPHA*(1-c)))
G=coo_matrix((np.concatenate(wts),(np.concatenate(rows),np.concatenate(cols))),shape=(len(U),)*2).tocsr()
seeds=np.nonzero(seedsel)[0]
dist,pred,sources=dijkstra(G,directed=False,indices=seeds,min_only=True,return_predecessors=True)
lab=np.where(sources>=0,vid[ii[selU]][np.maximum(sources,0)],0)
print('unreached',(sources<0).sum(),'of',len(U))
lab[seedsel]=vid[ii[selU]][seedsel]
B[tuple(U.T)]=np.where(lab>0,lab,B[tuple(U.T)])
np.save(dst,B); print('saved')
