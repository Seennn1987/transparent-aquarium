# 肋骨を 1 本ずつ（椎骨 k・左右）のラベルにする（ribs8.py の改良）
#   胴の骨を全部（椎体のそば = 体軸から 2.1 mm 以内も含めて）つないだ網にし、各椎骨の椎体の芯（体軸から 1.25 mm 以内）を種にする。
#   費用は、肋骨の管の向きに沿うと安く（横へ進むと ALPHA × ずれの 2 乗）、骨の薄い所（接触）を通ると高い（BETA）。
#   後ろの胴の肋骨は背骨のすぐ脇を長く沿って走るので、体軸の近さではなく、肋骨を伝ってたどり着く椎体で持ち主を決める。
#   肋骨のラベル（体軸から 2.1 mm より遠い、神経棘でない骨）= 160 + 2*(k-1) + (0 右 / 1 左)。体軸から 2.1 mm 以内は椎骨のまま。
#   左右は、肋骨を根元へたどって背骨のそばに入った所の向きで決める（丸まった体では、遠い所の「体軸の最寄り」は別の場所になる）。
#   根元から届かない塊（骨の途切れの先）は、届いた骨に近い方の端で、いちばん近い肋骨のラベルを付ける（1 mm 以内）。
import numpy as np, scipy.ndimage as nd, sys, json
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from skimage.feature import hessian_matrix
src,dst=sys.argv[1],sys.argv[2]; ALPHA=float(sys.argv[3]) if len(sys.argv)>3 else 30.0; BETA=float(sys.argv[4]) if len(sys.argv)>4 else 2.0; BETA_FAR=float(sys.argv[6]) if len(sys.argv)>6 else 25.0
B=np.load(src); X=np.load('ct_ms50726_vol4max.npz')['v']
C=np.load('axis5_s.npy')*2+0.5; T=np.load('axis5_t.npy'); D=np.load('frame_D.npy'); J=np.load('J.npy'); tr=cKDTree(C); s_ax=np.arange(len(C))*0.1
P=np.argwhere(((B>=102)&(B<=123))|((B>=160)&(B<202)))
d,i=tr.query(P); s=s_ax[i]
t=T[i]; dd=D[i]-t*(D[i]*t).sum(1)[:,None]; dd/=np.linalg.norm(dd,axis=1)[:,None]; r=np.cross(-t,dd)
lat=((P-C[i])*r).sum(1); dor=((P-C[i])*dd).sum(1)
sel=(s<107.6); U=P[sel]; du=d[sel]; lat=lat[sel]; dor=dor[sel]; su=s[sel]
lab0=B[tuple(U.T)]; lab0=np.where(lab0>=160,101+(lab0-160)//2+1,lab0)    # 前のラベル（肋骨は椎骨へ戻す）
lo=U.min(0)-3; hi=U.max(0)+4; sl=tuple(slice(a,b) for a,b in zip(lo,hi)); q=U-lo
Xc=nd.gaussian_filter(X[sl].astype(np.float32),0.5)
Iu=Xc[tuple(q.T)]; Iu=np.clip((Iu-40)/(np.percentile(Iu,95)-40),0,1)
H=hessian_matrix(Xc,sigma=1.2,order='rc',use_gaussian_derivatives=False); del Xc
Hm=np.empty((len(U),3,3),np.float32)
for (a_,b_),h_ in zip(((0,0),(0,1),(0,2),(1,1),(1,2),(2,2)),H):
    v_=h_[tuple(q.T)]; Hm[:,a_,b_]=v_; Hm[:,b_,a_]=v_
del H
w,v=np.linalg.eigh(Hm); TT=v[np.arange(len(U)),:,np.argmin(np.abs(w),1)]; del Hm,w,v
np.save('r9_TT.npy',TT.astype(np.float16))
idx=-np.ones(hi-lo,np.int64); idx[tuple(q.T)]=np.arange(len(U))
rows=[];cols=[];wts=[]
OFFS=[np.array((a_,b_,c_)) for a_ in (-1,0,1) for b_ in (-1,0,1) for c_ in (-1,0,1) if (a_,b_,c_)>(0,0,0)]
for o in OFFS:
    qq=q+o; inb=np.all((qq>=0)&(qq<hi-lo),1); j=np.full(len(U),-1); j[inb]=idx[tuple(qq[inb].T)]; m=j>=0
    a=np.nonzero(m)[0]; b=j[m]; L=np.linalg.norm(o); u=o/L; c=0.5*(np.abs(TT[a]@u)+np.abs(TT[b]@u))
    ii=0.5*(Iu[a]+Iu[b])
    bt=np.where(np.minimum(du[a],du[b])>40,BETA_FAR,BETA)      # 背骨から 4 mm より遠い所の接触（肋骨どうし）は高くする
    rows.append(a); cols.append(b); wts.append(L*(1+ALPHA*(1-c)**2)*(1+bt*(1-ii)))
# 背骨のそば（体軸から 3.3 mm 以内）だけ、骨の表面どうしを短い橋でつなぐ（0.35 mm まで、費用は距離 × GAPC）。
# 肋骨の頭と椎骨のあいだの関節の隙間を越えて、肋骨が自分の椎骨にたどり着けるように。腹側では橋を作らない（隣の肋骨へ乗り移るので）
GAPC=float(sys.argv[5]) if len(sys.argv)>5 else 3.0
M=np.zeros(hi-lo,bool); M[tuple(q.T)]=True; labc,nc=nd.label(M,np.ones((3,3,3))); cl=labc[tuple(q.T)]
surf=M&~nd.binary_erosion(M,np.ones((3,3,3))); sv=surf[tuple(q.T)]&(du<32)
cand=np.nonzero(sv)[0]; kt=cKDTree(q[cand]); pr=kt.query_pairs(3.5,output_type='ndarray')
pa,pb=cand[pr[:,0]],cand[pr[:,1]]
gd=np.linalg.norm(q[pa]-q[pb],axis=1); keep=gd>1.8; pa,pb,gd=pa[keep],pb[keep],gd[keep]   # 隣どうし（つながっている）は除く。同じ塊の中でも隙間は越える
rows.append(pa); cols.append(pb); wts.append(gd*GAPC)
print('components',nc,'near-spine bridges',len(pa))
G=coo_matrix((np.concatenate(wts),(np.concatenate(rows),np.concatenate(cols))),shape=(len(U),)*2).tocsr()
core=(du<=12)&(lab0>=102)&(lab0<=122)
sidx=np.nonzero(core)[0]
dist,pred,srcs=dijkstra(G,directed=False,indices=sidx,min_only=True,return_predecessors=True)
owner=np.where(srcs>=0,lab0[np.maximum(srcs,0)]-101,0)      # 椎骨の番号 k
spin=(dor>10)&(np.abs(lat)<20)
rib=(du>20)&~spin&(owner>=1)&(owner<=21)
# 左右: 体軸に近い所（2.3 mm 以内）では体軸に対する横の向き。遠い所は、最短路を根元へたどって最初に体軸 2.3 mm 以内へ入った所の左右
side=np.full(len(U),-1,np.int8); order=np.argsort(np.where(np.isfinite(dist),dist,np.inf))
nearz=du<=22
for v_ in order:
    if not np.isfinite(dist[v_]): break
    if nearz[v_] or pred[v_]<0: side[v_]=int(lat[v_]<0)
    else: side[v_]=side[pred[v_]]
side[side<0]=(lat[side<0]<0)
out=np.where(rib,160+2*(owner-1)+side,0).astype(np.int16)
# 届かない遠い骨
far_un=(du>20)&~spin&(srcs<0)
Mu=np.zeros(hi-lo,bool); Mu[tuple(q[far_un].T)]=True; labu,nu=nd.label(Mu,np.ones((3,3,3))); cu=labu[tuple(q.T)]
reached=np.nonzero(rib)[0]; rt=cKDTree(U[reached]); fixed=0
for c in range(1,nu+1):
    mm=cu==c
    if mm.sum()<30: continue
    A=U[mm].astype(float); e=np.linalg.svd(A-A.mean(0),full_matrices=False)[2][0]
    tp=(A-A.mean(0))@e; ends=[A[tp<np.percentile(tp,3)].mean(0),A[tp>np.percentile(tp,97)].mean(0)]
    dq=[rt.query(x) for x in ends]; j=int(np.argmin([x[0] for x in dq]))
    if dq[j][0]<=10: out[mm]=out[reached[dq[j][1]]]; fixed+=int(mm.sum())
print('voxels',len(U),'rib voxels',int(rib.sum()),'unreached far',int(far_un.sum()),'re-attached',fixed)
newB=np.where(out>0,out,lab0).astype(B.dtype)
B[tuple(U.T)]=newB
names=json.load(open('bone_names.json'))
for k in range(1,22):
    for sd,nm in ((0,'R'),(1,'L')): names[str(160+2*(k-1)+sd)]=f'rib{k:02d}_{nm}'
json.dump(names,open('bone_names.json','w'))
np.save(dst,B); np.savez('r9_dbg.npz',U=U,du=du,pred=pred,srcs=srcs,owner=owner,dist=dist,Iu=Iu,su=su)
for k in range(1,22): print(f'v{k:02d}','R',int((out==160+2*(k-1)).sum()),'L',int((out==161+2*(k-1)).sum()))
