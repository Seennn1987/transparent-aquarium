# 膜のメッシュに、骨への重みと、肋骨の復元（ribrestore）と同じ変形を付ける。
#   重み: 各頂点の近く（σ 1 mm）にある骨のボクセルのラベルごとの重みの和。上位 3 本
#   変形: 近くの肋骨のボクセルが復元で動いた量を、同じ重みで混ぜて頂点を動かす（肋骨以外の骨の近くは動かない）
#   面を切る: CT では体が丸まって、手足が胴に、尾の巻きどうしが触れているので、外形がつながって写る。
#     主な骨（重み最大）が、別々の肢・肢と胴（肢帯のそば以外）・体軸で 2 個より離れた椎骨、の面は外す
#   出力: soft_rigged.npz（v: CT の mm、f、w_idx/w_val: 骨名の番号と重み、names）
import numpy as np, json, sys
from scipy.spatial import cKDTree
import ribrestore
z=np.load('soft_mesh.npz'); Vt=z['v'].astype(np.float64); F=z['f']
B=np.load('B_h10.npy'); names=json.load(open('bone_names.json')); SIDE=json.load(open('sides.json'))
def rename(n): return SIDE.get(n[:2],n[:2])+n[2:] if n[:2] in SIDE else n
P=np.argwhere(B>0); L=B[tuple(P.T)].astype(int)
ok=np.array([str(l) in names for l in L]); P=P[ok]; L=L[ok]
kt=cKDTree(P)
K=24; d,j=kt.query(Vt,k=K); lab=L[j]
w=np.exp(-0.5*(d*0.104/1.0)**2)
labs=np.unique(L); lid={l:i for i,l in enumerate(labs)}
# ラベルごとの和（頂点 × 近い K 点）
W=np.zeros((len(Vt),len(labs)),np.float32)
for c in range(K): np.add.at(W,(np.arange(len(Vt)),np.vectorize(lid.get)(lab[:,c])),w[:,c])
top=np.argsort(-W,1)[:,:3]; tw=np.take_along_axis(W,top,1); s=tw.sum(1,keepdims=True); tw=np.where(s>0,tw/np.maximum(s,1e-9),0)
tw[s[:,0]<=0,0]=1.0
# 肋骨の復元の変形
isrib=(L>=160)&(L<202); RP=P[isrib].astype(float); RL=L[isrib]
disp=np.zeros((len(P),3)); disp[isrib]=ribrestore.restore(RP,RL)-RP
dn=disp[j]                                     # (n,K,3)
wsum=w.sum(1,keepdims=True); move=(w[...,None]*dn).sum(1)/np.maximum(wsum,1e-9)
Vr=Vt+move
# 面を切る
nm=[rename(names[str(l)]) for l in labs]
# 肢の付け根の椎骨（rig.log の親: 肢帯・上腕の親の椎骨）
ROOTV={'fR':6,'fL':5,'hL':23,'hR':23}
def info(n):
    if n.startswith('v'): return ('ax',int(n[1:]))
    if n.startswith('rib'): return ('ax',int(n[3:5]))
    if n in ('head','hyoid'): return ('ax',0)
    limb=n.split('_')[0]; part=n.split('_')[1]
    return (limb,part)
inf=[info(n) for n in nm]
prim=top[:,0]
def bad(a,b):
    ia,ib=inf[a],inf[b]
    if ia[0]=='ax' and ib[0]=='ax': return abs(ia[1]-ib[1])>2
    SEG={'girdle':0,'upper':1,'lower':2,'hand':3,'foot':3}
    if ia[0]!='ax' and ib[0]!='ax': return ia[0]!=ib[0] or abs(SEG[ia[1]]-SEG[ib[1]])>1   # 同じ肢の隣り合う骨だけ
    limb,ax=(ia,ib) if ia[0]!='ax' else (ib,ia)
    # 肢は肢帯だけが、付け根の椎骨の前後 3 個までの体軸とつながる（上腕・大腿から先は胴とつながらない。CT では胴に押し付けられている）
    return limb[1]!='girdle' or abs(ax[1]-ROOTV[limb[0]])>3
# 頂点の重みも、主な骨とつながらない骨の分は落とす
for c in (1,2):
    badw=np.array([bad(a_,b_) if a_!=b_ else False for a_,b_ in zip(prim.tolist(),top[:,c].tolist())])
    tw[badw,c]=0
tw=tw/np.maximum(tw.sum(1,keepdims=True),1e-9)
pa,pb,pc=prim[F[:,0]],prim[F[:,1]],prim[F[:,2]]
uniq={}
cut=np.zeros(len(F),bool)
pairs=set()
for x,y in ((pa,pb),(pb,pc),(pa,pc)):
    m=x!=y
    for a_,b_ in set(zip(x[m].tolist(),y[m].tolist())):
        if bad(a_,b_): pairs.add((a_,b_))
pairset=pairs
def facebad(x,y): 
    return np.array([(a_,b_) in pairset for a_,b_ in zip(x.tolist(),y.tolist())])
for x,y in ((pa,pb),(pb,pc),(pa,pc)):
    m=x!=y; idx=np.nonzero(m)[0]
    cut[idx[facebad(x[idx],y[idx])]]=True
F2=F[~cut]
print('verts',len(Vt),'faces',len(F),'cut',int(cut.sum()),'max move mm',round(float(np.linalg.norm(move,axis=1).max())*0.104,2))
np.savez_compressed('soft_rigged.npz',v=(Vr*0.104).astype(np.float32),f=F2.astype(np.int32),w_idx=top.astype(np.int16),w_val=tw.astype(np.float32),names=np.array(nm))
