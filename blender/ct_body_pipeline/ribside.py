# 胸郭の横・腹の図（展示の姿勢）: 体軸の枠に直して（u = 体軸の長さ、下 = 腹）
import numpy as np, sys, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
from scipy.spatial import cKDTree
kp=cKDTree(Cp); files=sys.argv[1].split(','); titles=sys.argv[2].split(',')
fig,ax=plt.subplots(2,len(files),figsize=(9*len(files),9),squeeze=False)
for c,(fn,tt) in enumerate(zip(files,titles)):
    d=np.load(fn); ca,cb,own=ct2m(d['cart__a']),ct2m(d['cart__b']),d['cart__bone']
    for n in bn:
        if not (n.startswith(('v','rib','hyoid')) or 'girdle' in n) or n+'__v' not in d.files: continue
        M=Mof(n); x=(ct2m(d[n+'__v'])[::3])@M[:3,:3].T+M[:3,3]
        j=kp.query(x)[1]; q=x-Cp[j]; u=arc[j]; vd=-(q*Dp[j]).sum(1)/MM; lt=(q*Ep[j]).sum(1)/MM
        m=u<125; col='tab:red' if n.startswith('rib') else ('tab:orange' if n=='hyoid' else ('tab:green' if 'girdle' in n else 'k'))
        ax[0,c].scatter(u[m],vd[m],s=0.2,c=col); ax[1,c].scatter(u[m],lt[m],s=0.2,c=col)
        mm_=own==n
        if mm_.any():
            for A_,B_ in zip(ca[mm_],cb[mm_]):
                p=np.linspace(A_,B_,6)@M[:3,:3].T+M[:3,3]; j=kp.query(p)[1]; q=p-Cp[j]
                ax[0,c].plot(arc[j],-(q*Dp[j]).sum(1)/MM,c='tab:blue',lw=1); ax[1,c].plot(arc[j],(q*Ep[j]).sum(1)/MM,c='tab:blue',lw=1)
    ax[0,c].invert_yaxis(); ax[0,c].set_title(tt+'（横、下 = 腹）'); ax[1,c].set_title(tt+'（腹から）')
    for a in ax[:,c]: a.set_aspect('equal'); a.grid(alpha=.3); a.set_xlim(-10,125)
    ax[1,c].set_xlabel('体軸 u [mm]')
plt.tight_layout(); plt.savefig(sys.argv[3],dpi=60)
