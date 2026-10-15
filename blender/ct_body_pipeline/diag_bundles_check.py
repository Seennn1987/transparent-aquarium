# 束の間（2 つの束の点の中点で骨から 1.2 mm 以上）と、束の中（同じ束の 0.9〜2.2 mm 離れた点の中点で骨から 0.5 mm 以上）が膜の内側か
#   CARP_MM（手首から除く半径）: 手 5.5、右足 6.5、左足 5.5（図 hand_bundles.png で束を目で確かめた値）
import numpy as np, os
from scipy.spatial import cKDTree
z=np.load('diag_inside.npz'); I=z['inside']; lo=z['lo']; VOX=float(z['vox'])
P=np.load('pose_jar.npz'); k=float(P['k'])
src=open('diag_bundles.py').read().split("if __name__=='__main__':")[0]
CFG={'fR_hand':('fR_lower',5.5),'fL_hand':('fL_lower',5.5),'hR_foot':('hR_lower',6.5),'hL_foot':('hL_lower',5.5)}
res={}
for n,(lw,c) in CFG.items():
    os.environ['CARP_MM']=str(c); g={}; exec(src,g)
    X,Y,part,wr,how=g['bundles'](n,lw)
    A=Y[part==0]; B=Y[part==1]
    # 2 つの束の間の点: 束 A の点と束 B の点の中点のうち、どちらの骨からも 1.2 mm 以上離れた所
    ka,kb=cKDTree(A),cKDTree(B); ia=np.random.default_rng(0).choice(len(A),2000); jb=kb.query(A[ia])[1]
    M=(A[ia]+B[jb])/2; gap=np.linalg.norm(A[ia]-B[jb],axis=1)
    far=(ka.query(M)[0]>1.2)&(kb.query(M)[0]>1.2)
    gi=np.round((M[far]*k-lo)/VOX).astype(int); ok=np.all((gi>=0)&(gi<I.shape),1)
    ins=I[tuple(gi[ok].T)]
    print(n,how,'bundles',len(A),len(B),'between-points',far.sum(),'inside skin %.0f%%'%(100*ins.mean() if len(ins) else -1),'gap median %.1f mm'%np.median(gap[far]) if far.any() else '')
print('--- within bundles')
for n,(lw,c) in CFG.items():
    os.environ['CARP_MM']=str(c); g={}; exec(src,g)
    X,Y,part,wr,how=g['bundles'](n,lw); kx=cKDTree(X)
    for q in (0,1):
        A=Y[part==q]; ka=cKDTree(A); pr=ka.query_pairs(2.2,output_type='ndarray'); rng=np.random.default_rng(1)
        pr=pr[rng.choice(len(pr),min(len(pr),200000),replace=False)]
        dd=np.linalg.norm(A[pr[:,0]]-A[pr[:,1]],axis=1); M=(A[pr[:,0]]+A[pr[:,1]])/2
        sel=(dd>0.9)&(kx.query(M)[0]>0.5)
        gi=np.round((M[sel]*k-lo)/VOX).astype(int); ok=np.all((gi>=0)&(gi<I.shape),1); ins=I[tuple(gi[ok].T)]
        print(n,'bundle',q,'gap points',sel.sum(),'inside skin %.0f%%'%(100*ins.mean() if len(ins) else -1))
