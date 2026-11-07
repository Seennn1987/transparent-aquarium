"""手足の膜の重みの取り違えを直す（記録 143）: fix_limb_weights.py <入力 glb> <出力 glb>
静止の形（瓶の姿勢）で、手足の骨（名前が fL_/fR_/hL_/hR_ で始まる骨）を親から子への線分にし、膜の頂点ごとに:
1 いちばん重い骨が脚 X の足・手・指の骨なのに、別の脚 Y の上・下の骨の線分のほうが近く、3.5 mm 以内のとき、X の脚の骨の重みをすべてその骨へ移す
  （瓶の姿勢で左足の指が右の太ももの横にあり、右の太ももの膜 180 点が左足の指の骨に付いていた）。指の骨から 1.2 mm より離れた頂点は、指の膜（0.5〜0.73 mm）でないので、別の脚の骨が近くなくても移す
2 同じ脚で、いちばん重い骨が下の骨（すね・前腕）なのに、上の骨（大腿・上腕）の線分の中ほど（0.1〜0.8）に下の骨より 1 mm 以上近いとき、その重みを上の骨へ移す
CH_Skin だけ。重みの和は変えない"""
import sys,numpy as np
from glbio import GLB,skin_data
src,dst=sys.argv[1],sys.argv[2]
g=GLB(src); d=skin_data(g); P,J,W,nm,B=d['P'],d['J'].astype(int),d['W'].astype(float),d['names'],d['bind']
MM=1.04/23.1; DIGIT_SKIN_MM=1.2   # 指の膜は 0.5〜0.73 mm（README 66）。それより離れた頂点は指の膜でない
mm=lambda x:x/MM
ix={n:i for i,n in enumerate(nm)}
# 骨の子（skin の joints の中で）
kids={i:[] for i in range(len(nm))}
for i,jn in enumerate(d['skin']['joints']):
    for c in g.J['nodes'][jn].get('children',[]):
        if c in d['skin']['joints']: kids[i].append(d['skin']['joints'].index(c))
limbb=[i for i,n in enumerate(nm) if n[:3] in ('fL_','fR_','hL_','hR_')]
limb=lambda i: nm[i][:2]
def segdist(i):
    ends=[B[c] for c in kids[i]] or [B[i]]
    best=np.full(len(P),np.inf); ubest=np.zeros(len(P))
    for e in ends:
        a=B[i]; ab=e-a; L2=max(ab@ab,1e-12); u=np.clip(((P-a)@ab)/L2,0,1); dd=np.linalg.norm(P-(a+u[:,None]*ab),axis=1)
        m=dd<best; best[m]=dd[m]; ubest[m]=u[m]
    return mm(best),ubest
D={};U={}
for i in limbb: D[i],U[i]=segdist(i)
n=len(P); top=J[np.arange(n),W.argmax(1)]
c1=c2=0
for v in range(n):
    t=top[v]
    if t not in D: continue
    X=limb(t); dX=min(D[i][v] for i in limbb if limb(i)==X)
    nb=min(limbb,key=lambda i:D[i][v])
    distalX=('_foot' in nm[t]) or ('_hand' in nm[t]) or nm[t].endswith(('1','2','_end'))
    longY=[i for i in limbb if limb(i)!=X and nm[i].endswith(('_upper','_lower'))]
    nbL=min(longY,key=lambda i:D[i][v])
    digitX=nm[t].endswith(('1','2','_end')) and ('_med' in nm[t] or '_lat' in nm[t])
    if distalX and D[nbL][v]<3.5 and (D[nbL][v]<dX or (digitX and D[t][v]>DIGIT_SKIN_MM)):
        nb=nbL
        w=0
        for c in range(4):
            if J[v,c] in D and limb(J[v,c])==X: w+=W[v,c]; W[v,c]=0
        # nb へ足す（同じ骨が既にあればそこへ、無ければ重み 0 の欄へ）
        cs=[c for c in range(4) if J[v,c]==nb] or [c for c in range(4) if W[v,c]==0]
        J[v,cs[0]]=nb; W[v,cs[0]]+=w; c1+=1; continue
    if nm[t].endswith('_lower'):
        up=ix[X+'_upper']
        if 0.1<=U[up][v]<=0.8 and D[up][v]+1.0<D[t][v]:
            for c in range(4):
                if J[v,c]==t:
                    w=W[v,c]; W[v,c]=0
                    cs=[k for k in range(4) if J[v,k]==up] or [k for k in range(4) if W[v,k]==0 or k==c]
                    J[v,cs[0]]=up; W[v,cs[0]]+=w
            c2+=1
# 3（記録 144）: 上の骨（上腕・大腿）がいちばん重い頂点で、その骨の線分から UPPER_FAR_MM より遠く、胴の重みの頂点が 1.5 mm 以内にあるものは、
#   胴の膜（展示の姿勢で腕が胸に触れて、胸の膜が上腕に付いた）なので、いちばん近い胴の頂点の骨と重みを写す
from scipy.spatial import cKDTree
UPPER_FAR_MM=float(__import__("os").environ.get("UPPER_FAR_MM","3.5"))
top=J[np.arange(n),W.argmax(1)]
isT=np.array([not(nm[t][:3] in ('fL_','fR_','hL_','hR_')) for t in top])
kd=cKDTree(P[isT]); tid=np.where(isT)[0]; c3=0
for v in range(n):
    t=top[v]
    if t not in D or not nm[t].endswith('_upper') or D[t][v]<=UPPER_FAR_MM: continue
    dd,j=kd.query(P[v])
    if mm(dd)>1.5: continue
    J[v]=J[tid[j]]; W[v]=W[tid[j]]; c3+=1
print(f'胸・腹の膜を胴の重みにした頂点 {c3}')
pr=d['prim']; g.put(pr['attributes']['JOINTS_0'],J); g.put(pr['attributes']['WEIGHTS_0'],W)
g.save(dst); print(f'別の脚から移した頂点 {c1}、下の骨から上の骨へ移した頂点 {c2}')
