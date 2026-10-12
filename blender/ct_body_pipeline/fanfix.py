# 束になった肋骨ラベル（同じ側の他の肋骨の 1.6 倍より大きい）のうち、中心線（ribtrack2）から 0.4 mm より遠い部分を、
# 骨格線（細線化）の枝に分け、枝どうしを向きのつながり（接続点で 35° 以内、まっすぐな方を優先）で 1 本ずつの肋骨につなぐ。
# 各 1 本の背骨に近い端を、同じ側で腹側の部分をまだ持たない肋骨の「根元の部分の先」へ、隙間の合計が最小になるように
# 1 対 1 で割り当てる（ハンガリー法）。隙間が 6 mm を超える組は割り当てない。
import numpy as np, scipy.ndimage as nd, sys, json, networkx as nx
from scipy.spatial import cKDTree
from scipy.optimize import linear_sum_assignment
from skimage.morphology import skeletonize
src,dst=sys.argv[1],sys.argv[2]
B=np.load(src); z=np.load('r9_dbg.npz'); U,du=z['U'],z['du']
lab=B[tuple(U.T)].astype(np.int32); isrib=(lab>=160)&(lab<202)
names=json.load(open('bone_names.json'))
tk=np.load('ribtracks2.npz'); TP=np.concatenate([tk[k] for k in tk.files]); tt=cKDTree(TP); dtr,_=tt.query(U,distance_upper_bound=4)
cnt={l:int((lab==l).sum()) for l in range(160,202)}
for sd in (0,1):
    ls=[l for l in range(160+sd,202,2)]; med=np.median([cnt[l] for l in ls if cnt[l]>2000])
    bundles=[l for l in ls if cnt[l]>1.6*med]
    print('side',sd,'median',med,'bundles',[names[str(l)] for l in bundles])
    for bl in bundles:
        rest=np.nonzero((lab==bl)&~np.isfinite(dtr))[0]
        if len(rest)<500: continue
        lo=U[rest].min(0)-2; hi=U[rest].max(0)+3; q=U[rest]-lo
        M=np.zeros(hi-lo,bool); M[tuple(q.T)]=True
        S=skeletonize(M); sp=np.argwhere(S); spi={tuple(p):i for i,p in enumerate(sp)}
        G=nx.Graph(); G.add_nodes_from(range(len(sp)))
        for i,p in enumerate(sp):
            for o in np.array(np.meshgrid([-1,0,1],[-1,0,1],[-1,0,1])).reshape(3,-1).T:
                j=spi.get(tuple(p+o))
                if j is not None and j>i: G.add_edge(i,j)
        junc=[v for v in G if G.degree(v)>2]; H=G.copy(); H.remove_nodes_from(junc)
        segs=[]
        for comp in nx.connected_components(H):
            sub=H.subgraph(comp); en=[v for v in sub if sub.degree(v)<=1]
            if len(en)<2: continue
            path=nx.shortest_path(sub,en[0],en[1])
            if len(path)>=6: segs.append(np.array(path))
        W=sp+lo
        def enddir(sg,w):
            Q=W[sg].astype(float); m=min(6,len(Q)-1)
            return (Q[0],(Q[0]-Q[m])/np.linalg.norm(Q[0]-Q[m]+1e-9)) if w==0 else (Q[-1],(Q[-1]-Q[-1-m])/np.linalg.norm(Q[-1]-Q[-1-m]+1e-9))
        ends=[(k,w)+enddir(sg,w) for k,sg in enumerate(segs) for w in (0,1)]
        EP=np.array([e[2] for e in ends]); et=cKDTree(EP)
        cand=[]
        for a,b in et.query_pairs(8):
            ka,wa,pa,ua=ends[a]; kb,wb,pb,ub=ends[b]
            if ka==kb: continue
            cos=-ua@ub
            if cos>np.cos(np.radians(35)): cand.append((np.linalg.norm(pa-pb)/8+(1-cos)*3,a,b))
        cand.sort(); used=set(); L=nx.Graph(); L.add_nodes_from(range(len(segs)))
        for sc,a,b in cand:
            if a in used or b in used: continue
            used.add(a); used.add(b); L.add_edge(ends[a][0],ends[b][0])
        chains=[list(c) for c in nx.connected_components(L)]
        # 各 1 本の点（骨格線）と、背骨に近い端
        cpts=[np.concatenate([W[segs[k]] for k in ch]).astype(float) for ch in chains]
        ctree=[cKDTree(p) for p in cpts]
        clen=[len(p) for p in cpts]
        keep=[i for i in range(len(chains)) if clen[i]>=25]
        # 背骨に近い端
        Ut=cKDTree(U); 
        prox=[]
        for i in keep:
            p=cpts[i]; j=Ut.query(p)[1]; prox.append(p[np.argmin(du[j])])
        # 根元の部分の先（同じ側の肋骨、中心線の終わり）
        stubs=[int(k) for k in tk.files if (int(k)-160)%2==sd]
        tips=np.array([tk[str(l)][-1] for l in stubs])
        if not keep: continue
        Cst=np.array([[np.linalg.norm(pp-t) for t in tips] for pp in prox])
        r,c=linear_sum_assignment(Cst)
        assign={}
        for ri_,ci_ in zip(r,c):
            if Cst[ri_,ci_]<=60: assign[keep[ri_]]=stubs[ci_]
        # ボクセル → 最も近い 1 本
        allp=np.concatenate([cpts[i] for i in keep]); alll=np.concatenate([np.full(clen[i],assign.get(i,bl)) for i in keep])
        at=cKDTree(allp); g,j=at.query(U[rest].astype(float))
        newl=alll[j]
        lab[rest]=newl
        print(' ',names[str(bl)],'voxels',len(rest),'segments',len(segs),'chains',len(keep),'assigned',{names[str(v)]:round(float(Cst[keep.index(k),stubs.index(v)])*0.104,1) for k,v in assign.items()})
B[tuple(U.T)]=lab.astype(B.dtype); np.save(dst,B)
