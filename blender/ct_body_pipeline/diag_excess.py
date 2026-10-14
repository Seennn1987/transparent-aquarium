# 膜の自己検証 2（2026-10-14）: 膜が骨から離れすぎていないか
#   これまでの検証（diag_bones.py）は「骨が膜の外に出ていないか」だけで、「骨の無い所に膜が張られていないか」を見ていなかった
#   いくつかの向きから写した像で、膜の像のうち、骨・軟骨・臓器・眼球の像を ALLOW_MM ふくらませた範囲の外にある所を数え、図にする
#   胴は肋骨の輪の中が体腔なので、胴の像は骨の像の凸包の中も許す（体腔は空でよい）。頭と手足と尾は許さない
import numpy as np, sys, json, scipy.ndimage as nd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
def apply(M, x): return x @ M[:3, :3].T + M[:3, 3]
d=np.load('chameleon_body_ct.npz')
pts=[]; lab=[]
for n in bn:
    if n+'__v' in d.files:
        x=apply(Mof(n),ct2m(d[n+'__v'])); pts.append(x); lab.append(np.full(len(x),n))
ca,cb,own=ct2m(d['cart__a']),ct2m(d['cart__b']),d['cart__bone']
for a_,b_,o in zip(ca,cb,own):
    x=apply(Mof(str(o)),np.linspace(a_,b_,8)); pts.append(x); lab.append(np.full(len(x),'cart'))
EY=json.load(open('eyes.json'))
for e in EY.values():
    c=np.array(e['centre_model']); r=e['radius_mm']*MM; g=np.random.default_rng(0).standard_normal((3000,3)); g/=np.linalg.norm(g,axis=1,keepdims=True)
    pts.append(c+g*r*np.random.default_rng(1).uniform(0,1,(3000,1))**(1/3)); lab.append(np.full(3000,'eye'))
X=np.concatenate(pts)/MM; LB=np.concatenate(lab)
S=np.load(sys.argv[1] if len(sys.argv)>1 else 'skin_posed.npz'); v=S['v']/MM; f=S['f']
ALLOW_MM=float(sys.argv[2]) if len(sys.argv)>2 else 1.5
import os
VIEWS_ONLY=os.environ.get('VIEWS')
views={'右から':(np.array([0,1.,0]),np.array([-1.,0,0])),'左から':(np.array([0,-1.,0]),np.array([-1.,0,0])),'背から':(np.array([-1.,0,0]),np.array([0,0,-1.])),'腹から':(np.array([1.,0,0]),np.array([0,0,-1.])),'前から':(np.array([0,0,-1.]),np.array([-1.,0,0]))}
if VIEWS_ONLY: views={k:v for k,v in views.items() if k in VIEWS_ONLY.split(',')}
XL=[float(t) for t in os.environ['XLIM'].split(',')] if os.environ.get('XLIM') else None
from skimage.draw import polygon
res={}
fig,axs=plt.subplots(1,len(views),figsize=(float(os.environ.get('FW','7'))*len(views),float(os.environ.get('FW','7'))),squeeze=False); axs=axs[0]
for ax,(nm,(vd,up)) in zip(axs,views.items()):
    rt=np.cross(up,vd); px=0.1
    P2=np.c_[X@rt,X@up]; V2=np.c_[v@rt,v@up]
    lo=np.minimum(P2.min(0),V2.min(0))-3; hi=np.maximum(P2.max(0),V2.max(0))+3; sh=tuple(np.ceil((hi-lo)/px).astype(int)+1)
    sk=np.zeros(sh,bool)
    T=((V2[f]-lo)/px)
    for t in T:
        rr,cc=polygon(t[:,0],t[:,1],sh); sk[rr,cc]=True
    bone=np.zeros(sh,bool); g=((P2-lo)/px).round().astype(int); bone[tuple(g.T)]=True
    bone=nd.binary_closing(bone,iterations=3)
    allow=nd.distance_transform_edt(~bone)*px<=ALLOW_MM
    # 胴: 肋骨・椎骨・軟骨・肢帯の像の、それぞれの縦の列ごとの最小〜最大の間（体腔）も許す（輪の中は空でよい）
    trunk=np.isin(LB,[n for n in np.unique(LB) if n.startswith(('rib','v')) or n in ('cart','fR_girdle','fL_girdle','hL_girdle')])
    tb=np.zeros(sh,bool); g2=((P2[trunk]-lo)/px).round().astype(int); tb[tuple(g2.T)]=True
    tb=nd.binary_closing(tb,iterations=10); tb=nd.binary_fill_holes(tb)
    allow|=nd.distance_transform_edt(~tb)*px<=ALLOW_MM
    ex=sk&~allow
    lab_,n_=nd.label(ex); sizes=nd.sum(ex,lab_,range(1,n_+1))*px*px
    big=[(float(s),[float(c) for c in nd.center_of_mass(ex,lab_,i+1)]) for i,s in enumerate(sizes) if s>=0.5]
    res[nm]=dict(excess_mm2=float(ex.sum()*px*px),skin_mm2=float(sk.sum()*px*px),patches=[(round(s,1),[round(lo[0]+c[0]*px,1),round(lo[1]+c[1]*px,1)]) for s,c in sorted(big,reverse=True)[:6]])
    img=np.zeros(sh+(3,)); img[sk]=[0.75,0.85,1]; img[bone]=[0.5,0.15,0.2]; img[ex]=[1,0.2,0]
    ax.imshow(np.transpose(img,(1,0,2))[::-1],extent=[lo[0],hi[0],lo[1],hi[1]]); ax.set_title(f'{nm}: 骨から {ALLOW_MM} mm より外の膜（赤）{res[nm]["excess_mm2"]:.0f} mm²'); ax.set_aspect('equal')
    if XL: ax.set_xlim(XL[0],XL[1]); ax.set_ylim(XL[2],XL[3])
plt.tight_layout(); plt.savefig(sys.argv[3] if len(sys.argv)>3 else 'diag_excess.png',dpi=55)
for nm,r in res.items(): print(nm,'excess %.1f mm2 of skin %.0f mm2'%(r['excess_mm2'],r['skin_mm2']),'largest patches (mm2, centre):',r['patches'][:4])
json.dump(res,open('diag_excess.json','w'),ensure_ascii=False,indent=1)
