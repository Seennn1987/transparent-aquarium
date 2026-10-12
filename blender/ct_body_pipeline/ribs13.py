# 肋骨の帰属の最終（ribs9 → ribtrack2 の後）。
#   1. 肋骨の芯（骨の濃さ 0.2 以上、背骨から 3.1 mm より遠い）は、並んで接した肋骨どうしでも離れる。芯の塊を 1 つずつの肋骨の部分とする
#   2. たどった中心線（ribtrack2）が、塊の背骨に近い方の端を通る塊は、その肋骨のもの
#   3. 中心線が通らない塊（腹側の肋骨など、折れ目の先）は、背骨に近い方の端を、持ち主の決まった骨（2 の塊と、背骨から 3.1 mm 以内の肋骨）
#      のいちばん近い点につなぐ。1 つの肋骨に 2 つ以上つながるときは、隙間の小さい順に、まだ腹側の部分を持たない肋骨を優先する
#   4. 芯でない肋骨のボクセルは、最も近い芯のラベル（0.6 mm 以内）
import numpy as np, scipy.ndimage as nd, sys, json
from scipy.spatial import cKDTree
src,dst=sys.argv[1],sys.argv[2]; IT=float(sys.argv[3]) if len(sys.argv)>3 else 0.2; DCUT=30
B=np.load(src); z=np.load('r9_dbg.npz'); U,du,Iu=z['U'],z['du'],z['Iu']
lab=B[tuple(U.T)].astype(np.int32); isrib=(lab>=160)&(lab<202)
lo=U.min(0)-2; hi=U.max(0)+3; q=U-lo
core=isrib&(Iu>IT)&(du>DCUT)
M=np.zeros(hi-lo,bool); M[tuple(q[core].T)]=True; cl,nc=nd.label(M,np.ones((3,3,3))); cc=cl[tuple(q.T)]; cc[~core]=0
tk=np.load('ribtracks2.npz'); TP=np.concatenate([tk[k] for k in tk.files]); TL=np.concatenate([np.full(len(tk[k]),int(k)) for k in tk.files])
tt=cKDTree(TP); dd,jj=tt.query(U,distance_upper_bound=3.0); ontrack=np.isfinite(dd); tlab=np.where(ontrack,TL[np.minimum(jj,len(TL)-1)],0)
piece_lab=np.zeros(nc+1,np.int32); sizes=np.bincount(cc[core],minlength=nc+1)
for c in range(1,nc+1):
    if sizes[c]<150: continue
    m=(cc==c)&ontrack
    if m.sum()<30: continue
    l=np.bincount(tlab[m]).argmax()
    # 中心線が塊の背骨に近い方の端を通るときだけ（途中で接して横切るだけの塊は取らない）
    mm=np.nonzero(cc==c)[0]; pend=U[mm][du[mm]<=np.percentile(du[mm],5)].mean(0)
    tl=TP[TL==l]
    if np.min(np.linalg.norm(tl-pend,axis=1))<=8: piece_lab[c]=l
owned=np.zeros(len(U),np.int32)
owned[core]=piece_lab[cc[core]]
near_rib=isrib&(du<=DCUT); owned[near_rib]=lab[near_rib]
has_ventral=set()
cand=[]
for c in range(1,nc+1):
    if sizes[c]<150 or piece_lab[c]>0: continue
    mm=np.nonzero(cc==c)[0]; A=U[mm].astype(float)
    pend=A[du[mm]<=np.percentile(du[mm],5)].mean(0)
    sd=int(np.bincount((lab[mm]-160)%2).argmax())
    ow=np.nonzero((owned>0)&(((owned-160)%2)==sd)&(cc!=c))[0]
    ot=cKDTree(U[ow]); g,j=ot.query(pend,k=8)
    cand.append((float(g[0]),c,mm,[(float(gg),int(owned[ow[jj_]])) for gg,jj_ in zip(g,j)]))
cand.sort(key=lambda x:x[0])
rep=[]
for g0,c,mm,opts in cand:
    choice=None
    for gg,l in opts:
        if gg>60: break
        if l not in has_ventral and gg<=g0+15: choice=(gg,l); break
    if choice is None and opts[0][0]<=60: choice=opts[0]
    if choice is None: continue
    owned[mm]=choice[1]; has_ventral.add(choice[1]); rep.append((len(mm),round(choice[0]*0.104,2),choice[1]))
names=json.load(open('bone_names.json'))
for r_ in rep: print('ventral piece',r_[0],'gap mm',r_[1],'->',names[str(r_[2])])
# 4. 残り
ow=np.nonzero(owned>0)[0]; ot=cKDTree(U[ow])
rest=np.nonzero(isrib&(owned==0))[0]; g,j=ot.query(U[rest],distance_upper_bound=6)
ok=np.isfinite(g); owned[rest[ok]]=owned[ow[j[ok]]]
newlab=np.where(isrib&(owned>0),owned,lab)
print('rib voxels',int(isrib.sum()),'changed',int((newlab!=lab).sum()),'left as before',int((isrib&(owned==0)).sum()))
B[tuple(U.T)]=newlab.astype(B.dtype); np.save(dst,B)
