import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
from scipy.spatial import cKDTree
kp=cKDTree(Cp)
def frame(x): j=kp.query(x)[1]; q=x-Cp[j]; return arc[j], -(q*Dp[j]).sum(1)/MM
d6=np.load('chameleon_body_ct.npz'); d4=np.load('chameleon_body_ct_ribs4.npz')
P3=np.load('pose_jar_v3.npz'); P4=np.load('pose_jar_v4.npz')
fig,ax=plt.subplots(1,2,figsize=(16,5.2))
for a,(dd,PP,t) in zip(ax,((d4,P3,'段階 1 の時（舌骨は頭について回る。左の角は椎骨 v05 のラベル）'),(d6,P4,'いま（左の角を舌骨へ戻し、角は CT での胴との位置を保つ）'))):
    for n in bn:
        if not (n.startswith('rib') or n.startswith('v')) or n+'__v' not in dd.files: continue
        M=PP['M'][bn.index(n)]; x=ct2m(dd[n+'__v'])[::4]@M[:3,:3].T+M[:3,3]; u,vd=frame(x); m=u<70
        a.scatter(u[m],vd[m],s=0.2,c='#7a1f2b' if n.startswith('rib') else 'k',lw=0)
    ca,cb,own=ct2m(dd['cart__a']),ct2m(dd['cart__b']),dd['cart__bone']
    for A_,B_,o in zip(ca,cb,own):
        M=PP['M'][bn.index(str(o))]; p=np.linspace(A_,B_,4)@M[:3,:3].T+M[:3,3]; u,vd=frame(p)
        if u.max()<70: a.plot(u,vd,c='tab:blue',lw=0.8)
    M=PP['M'][bn.index('hyoid')]; x=ct2m(dd['hyoid__v'])[::2]@M[:3,:3].T+M[:3,3]; u,vd=frame(x)
    a.scatter(u,vd,s=0.5,c='tab:orange',lw=0,label='舌骨')
    if 'v05' in t or True:
        M=PP['M'][bn.index('v05')]; x=ct2m(dd['v05__v'])@M[:3,:3].T+M[:3,3]; u,vd=frame(x); m=vd>8
        if m.any(): a.scatter(u[m],vd[m],s=0.5,c='tab:green',lw=0,label='v05 のラベルの角')
    a.invert_yaxis(); a.set_aspect('equal'); a.grid(alpha=.3); a.set_xlim(-5,70); a.set_ylim(32,-8); a.set_title(t,fontsize=11)
    a.set_xlabel('体軸 u [mm]（展示の姿勢）'); a.set_ylabel('腹へ [mm]'); a.legend(loc='lower right',markerscale=10)
plt.tight_layout(); plt.savefig('hyoidfig.png',dpi=70)
