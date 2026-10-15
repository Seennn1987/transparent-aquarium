# 手足の骨を 2 つの束に分ける（2026-10-15、記録 17。手 (I,II,III)(IV,V)、足 (I,II)(III,IV,V): Diaz & Trainor 2015）: 手根・足根（手首から CARP_MM 以内）を除いた骨の点の近傍グラフを、つながりが 1 つなら
# Fiedler ベクトルで 2 つに切る（輪の形なら、束の先どうしが触れる所で切れる）。2 つ以上なら大きい 2 つ
import numpy as np, json
from scipy.spatial import cKDTree
import scipy.sparse as sp; from scipy.sparse.csgraph import connected_components, laplacian
from scipy.sparse.linalg import eigsh
exec(open('digits_posed.py').read().split('VX=0.1')[0])
CARP_MM=float(__import__('os').environ.get('CARP_MM','3.0'))
def bundles(n, lower):
    X=posed(n); Lw=posed(lower)
    dl=cKDTree(Lw).query(X)[0]; wrist=X[dl<np.percentile(dl,1.5)].mean(0)
    far=np.linalg.norm(X-wrist,axis=1)>CARP_MM
    Y=X[far][::2]; kd=cKDTree(Y); pr=kd.query_pairs(0.35,output_type='ndarray')
    A=sp.coo_matrix((np.ones(len(pr)),(pr[:,0],pr[:,1])),shape=(len(Y),len(Y))); A=(A+A.T).tocsr()
    nc,lab=connected_components(A,directed=False); sz=np.bincount(lab); big=np.argsort(-sz)
    if nc>=2 and sz[big[1]]>0.15*len(Y):
        part=np.where(lab==big[0],0,np.where(lab==big[1],1,-1)); how='components'
    else:
        m=lab==big[0]; idx=np.where(m)[0]; As=A[idx][:,idx]
        Lp=laplacian(As,normed=True); vals,vecs=eigsh(Lp,k=3,sigma=-1e-3,which='LM')
        f=vecs[:,np.argsort(vals)[1]]; part=-np.ones(len(Y),int); fs=np.sort(f); gi=np.argmax(np.diff(fs)[len(fs)//10:-len(fs)//10])+len(fs)//10; part[idx]=(f>0.5*(fs[gi]+fs[gi+1])).astype(int); how='fiedler'
    return X,Y,part,wrist,how
if __name__=='__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,4,figsize=(24,12)); res={}
    for i,(n,lw) in enumerate((('fR_hand','fR_lower'),('fL_hand','fL_lower'),('hR_foot','hR_lower'),('hL_foot','hL_lower'))):
        X,Y,part,wr,how=bundles(n,lw); c=X.mean(0); U=np.linalg.svd(X-c,full_matrices=False)[2]
        print(n,how,'bundle sizes',[(part==q).sum() for q in (0,1)],'unassigned',(part<0).sum())
        for r,(a,b) in enumerate(((0,1),(0,2))):
            A_=ax[r,i]; pr=lambda p:(np.asarray(p)-c)@U[[a,b]].T
            q=pr(X[::3]); A_.scatter(q[:,0],q[:,1],s=0.3,c='0.8')
            for qq,col in ((0,'tab:red'),(1,'tab:blue')):
                z=pr(Y[part==qq]); A_.scatter(z[:,0],z[:,1],s=0.6,c=col)
            w=pr(wr); A_.plot(w[0],w[1],'ko'); A_.set_aspect('equal'); A_.set_title(f'{n} ({how})'); A_.set_xlim(-9,9); A_.set_ylim(-9,9)
    plt.tight_layout(); plt.savefig('bundles.png',dpi=45)
