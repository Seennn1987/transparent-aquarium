# 膜の断面（体軸に直角、展示の姿勢）と、断面の前後 1 mm の骨・軟骨の点
import numpy as np, sys, time, matplotlib; t0=time.time(); matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
def apply(M, x): return x @ M[:3, :3].T + M[:3, 3]
rest={n:ct2m(d[n+'__v']) for n in bn if n+'__v' in d.files}
B=open('skinbody.py').read(); exec(B[B.index('# 軟骨: 1.5 mm'):B.index('def ray_hull')])
files=sys.argv[1].split(','); labels=sys.argv[2].split(','); out=sys.argv[3]
US=[float(x) for x in (sys.argv[4] if len(sys.argv)>4 else '15,35,55,75,95').split(',')]
fig,ax=plt.subplots(1,len(US),figsize=(4.2*len(US),5.5))
cols=['tab:blue','tab:orange','tab:green']
for a_,u in zip(ax,US):
    i=int(np.argmin(abs(arc-u))); o=Cp[i]; t=Tp[i]; dv=Dp[i]; e=Ep[i]
    for nm in PX:
        x=PX[nm]; s=(x-o)@t; m=np.abs(s)<1.0*MM
        if m.any(): a_.scatter((x[m]-o)@e/MM,-(x[m]-o)@dv/MM,s=0.3,c='k' if nm.startswith('v') else ('tab:red' if nm.startswith('rib') else '0.4'))
    for fi,(fn,lb) in enumerate(zip(files,labels)):
        S=np.load(fn); v=S['v'].astype(float); f=S['f']; dd=(v-o)@t
        tri=dd[f]; cross=(tri.min(1)<0)&(tri.max(1)>0)
        segs=[]
        for tr in f[cross]:
            p=[]
            for a,b in ((0,1),(1,2),(2,0)):
                da,db=dd[tr[a]],dd[tr[b]]
                if (da<0)!=(db<0): w=da/(da-db); p.append(v[tr[a]]+(v[tr[b]]-v[tr[a]])*w)
            if len(p)==2: segs.append(p)
        segs=np.array(segs)
        # 体軸から 30 mm 以内（手足の断面を除く）
        for sg in segs:
            q=sg-o
            if np.linalg.norm(q,axis=1).max()/MM>32: continue
            a_.plot(q@e/MM,-(q@dv)/MM,'-',c=cols[fi],lw=1.2,label=lb)
    h,l=a_.get_legend_handles_labels(); dct=dict(zip(l,h)); a_.legend(dct.values(),dct.keys(),fontsize=8,loc='lower right')
    a_.set_aspect('equal'); a_.set_xlim(-16,16); a_.set_ylim(-14,32); a_.invert_yaxis(); a_.grid(alpha=0.3); a_.set_title(f'体軸 {u:.0f} mm（下が腹）')
plt.tight_layout(); plt.savefig(out,dpi=70)
