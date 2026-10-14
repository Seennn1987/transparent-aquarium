# 肋骨ごとの「端から見た形」: 肋骨の頭の体軸の枠（右 r、腹 v）と横から（尾 t、腹 v）へ全体を投影。前 = いま、後 = 並べ直し
import numpy as np, pickle, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
P=np.load('pose_jar.npz'); k=float(P['k']); MM=k
c=np.load('organs_cav.npz'); us=c['us']; AP=c['AP']; AV=c['AV']; AR=c['AR']
T=np.gradient(AP,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)
from scipy.spatial import cKDTree; kd=cKDTree(AP)
R=pickle.load(open('rib_pts.pkl','rb'))
idx=sorted({int(n[3:5]) for n in R})
fig,ax=plt.subplots(4,len(idx),figsize=(2.2*len(idx),10))
for col,i in enumerate(idx):
    for row,which in enumerate((0,1)):
        for s,cc in (('L','C0'),('R','C3')):
            n=f'rib{i:02d}_{s}'
            if n not in R: continue
            p=R[n][which]; dd,jj=kd.query(p); j=jj[np.argmin(dd)]; o=AP[j]
            ax[row,col].scatter(((p-o)@AR[j])/MM,((p-o)@AV[j])/MM,s=0.2,c=cc)
            ax[row+2,col].scatter(((p-o)@T[j])/MM,((p-o)@AV[j])/MM,s=0.2,c=cc)
        for a in (ax[row,col],ax[row+2,col]):
            a.set_xlim(-15,15); a.set_ylim(28,-4); a.set_aspect('equal'); a.set_xticks([]); a.set_yticks([])
        ax[row,col].set_title(f'{i:02d} '+('いま' if which==0 else '後'),fontsize=8)
ax[0,0].set_ylabel('端から（右←→左）'); ax[1,0].set_ylabel('端から 後'); ax[2,0].set_ylabel('横から（頭←→尾）'); ax[3,0].set_ylabel('横から 後')
plt.tight_layout(); plt.savefig('ribend.png',dpi=60)
