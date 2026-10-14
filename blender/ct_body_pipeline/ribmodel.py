# 段階 1（肋骨の作り直し）: CT で測った長さ・太さ・向きから、左右対称にそろった肋骨を作り直す（展示の姿勢で作り、静止の姿勢へ戻す）
#   CT の肋骨のメッシュは、保存の変形（胸が横へずれる）と、ラベルの切れ・混ざり（ほかの骨のかけら）で、
#   回して並べ直すだけではそろわなかった（ribpose2.py の試し）。そこで形を単純化して作り直す。形は単純化した模型
#   肋骨 i ごとに（左右で同じ値）:
#     頭: 左右の肋骨の頭（背骨にいちばん近い頂点）を、体軸の枠（尾 t、腹 v、外 r×側）で平均
#     背側の部分: 長さ Ld = 中心線の頭 → 折れ角（無ければ先）の弦の長さの左右の大きい方（CT のラベルが切れた側があるため）。
#       向き = 左右の弦の向きの平均。外への膨らみ = 長さの 12%（仮。CT の断面の胸の幅に合わせて目で決めた）
#     腹側の部分（骨。CT に折れ角がある肋骨 05〜14）: 長さ Lv = 左右の大きい方、横から見た向き（t と v）= 左右の平均。
#       先は腹の正中（左右の先が向き合う。0.3 mm 手前）
#     腹側の軟骨（腹側の骨が無い肋骨 03〜04 と 15〜21、骨の部分が正中に届かない肋骨）: 骨の先から腹の正中まで。
#       カメレオンのほとんどの肋骨は胸骨か反対側の肋骨の軟骨につながる（madcham.de）。トカゲの腹の肋骨は V 字で、ふつう軟骨
#       （Williston 1925）。向きは隣の肋骨の腹側の部分の向きを補間
#     長さと向きは肋骨の番号に沿ってならす（σ 1.5 本）。太さ = メッシュの体積 ÷ (π × 長さ) の平方根（左右の中央値）
#   出力: chameleon_body_ct_ribs3.npz（肋骨のメッシュと軟骨 cart__ を置き換え）、ribmodel.json
import numpy as np, json, pickle, scipy.sparse as sp
from scipy.sparse import csgraph
from scipy.spatial import cKDTree
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; k=float(P['k']); MM=k
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
def m2ct(m): m=np.asarray(m,float)/k; return np.stack([-m[...,2],m[...,0],-m[...,1]],-1)
d=dict(np.load('chameleon_body_ct.npz')); c=np.load('organs_cav.npz'); us=c['us']; AP=c['AP']; AV=c['AV']; AR=c['AR']
T=np.gradient(AP,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True); kd=cKDTree(AP)
def centerline(p,f):
    E=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]); w=np.linalg.norm(p[E[:,0]]-p[E[:,1]],axis=1)
    G=sp.coo_matrix((w,(E[:,0],E[:,1])),shape=(len(p),len(p))).tocsr()
    h0=int(np.argmin(kd.query(p)[0])); g=csgraph.dijkstra(G,directed=False,indices=h0); fin=np.isfinite(g)
    if (~fin).any(): g[~fin]=g[fin][cKDTree(p[fin]).query(p[~fin])[1]]
    bins=np.arange(0,g.max()+0.4*MM,0.4*MM); bi=np.digitize(g,bins)
    tp=np.array([p[bi==q].mean(0) for q in np.unique(bi)])
    s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(tp,axis=0),axis=1))]
    return tp,s
def find_bend(tp,s):
    if s[-1]<5*MM: return None
    w=1.5*MM; best=0; bend=None
    for i in range(len(tp)):
        if s[i]<0.3*s[-1] or s[i]<w or s[i]>s[-1]-w: continue
        a=tp[i]-tp[np.searchsorted(s,s[i]-w)]; b=tp[min(np.searchsorted(s,s[i]+w),len(tp)-1)]-tp[i]
        na,nb=np.linalg.norm(a),np.linalg.norm(b)
        if na<1e-9 or nb<1e-9: continue
        ang=np.degrees(np.arccos(np.clip(a@b/na/nb,-1,1)))
        if ang>35 and ang>best: best,bend=ang,i
    return bend
def loc(vec,j,side): return np.array([vec@T[j],vec@AV[j],(vec@AR[j])*side])
def glob(lc,j,side): return lc[0]*T[j]+lc[1]*AV[j]+lc[2]*AR[j]*side
meas={}
for n in bn:
    if not n.startswith('rib') or n+'__v' not in d: continue
    M=P['M'][bn.index(n)]; v=ct2m(d[n+'__v']); p=v@M[:3,:3].T+M[:3,3]; f=d[n+'__f']
    tp,s=centerline(p,f); b=find_bend(tp,s); side=1 if n.endswith('_R') else -1
    j=kd.query(tp[0])[1]; e=b if b is not None else len(tp)-1
    vol=abs(np.einsum('ij,ij->i',v[f[:,0]],np.cross(v[f[:,1]],v[f[:,2]])).sum()/6)
    meas[n]=dict(i=int(n[3:5]),side=side,j=int(j),head=loc(tp[0]-AP[j],j,side)/MM,Ld=np.linalg.norm(tp[e]-tp[0])/MM,Lv=np.linalg.norm(tp[-1]-tp[b])/MM if b is not None else 0.0,
                 dch=loc(tp[e]-tp[0],j,side),vch=(loc(tp[-1]-tp[b],j,side) if b is not None else None),
                 rad=float(np.sqrt(vol/(np.pi*max(np.linalg.norm(tp[e]-tp[0])+(np.linalg.norm(tp[-1]-tp[b]) if b is not None else 0),1e-9))))/MM,L=(np.linalg.norm(tp[e]-tp[0])+(np.linalg.norm(tp[-1]-tp[b]) if b is not None else 0))/MM)
idx=list(range(3,22))
def pairs(i): return [meas[f'rib{i:02d}_{s}'] for s in 'LR' if f'rib{i:02d}_{s}' in meas]
def sm(vals,sig=1.5):
    ii=np.array([i for i in idx if vals.get(i) is not None]); out={}
    for i in idx:
        w=np.exp(-0.5*((ii-i)/sig)**2); V=np.array([vals[x] for x in ii]); out[i]=(w[:,None]*V.reshape(len(ii),-1)).sum(0)/w.sum()
    return out
Ld={i:max([m['Ld'] for m in pairs(i)],default=None) for i in idx}
Lv={i:(max([m['Lv'] for m in pairs(i) if m['vch'] is not None],default=None)) for i in idx}
def unitmean(vs): 
    vs=[v/np.linalg.norm(v) for v in vs if v is not None and np.linalg.norm(v)>0]; 
    if not vs: return None
    m=np.mean(vs,0); return m/np.linalg.norm(m)
DT={i:unitmean([m['dch'] for m in pairs(i) if m['L']>=5]) for i in idx}
VT={i:unitmean([m['vch'] for m in pairs(i) if m['vch'] is not None]) for i in idx}
HD={i:np.mean([m['head'] for m in pairs(i)],0) if pairs(i) else None for i in idx}
RAD={i:float(np.median([m['rad'] for m in pairs(i) if m['L']>=5])) if any(m['L']>=5 for m in pairs(i)) else None for i in idx}
sc=lambda D: {i:float(np.ravel(v)[0]) for i,v in D.items()}
LdS=sc(sm(Ld)); DTS=sm(DT); VTS=sm(VT); RADS=sc(sm(RAD)); HDS=sm(HD,0.8)
LvS=sc(sm({i:Lv[i] for i in idx if Lv[i] is not None and Lv[i]>2}))
BOW=0.12
def tube(curve,rad,nseg=10):
    curve=np.asarray(curve); tng=np.gradient(curve,axis=0); tng/=np.linalg.norm(tng,axis=1,keepdims=True)
    ref=np.array([0,0,1.0]); verts=[]; faces=[]
    nprev=None
    for q,(pt,tg) in enumerate(zip(curve,tng)):
        n1=np.cross(tg,ref) if nprev is None else nprev-(nprev@tg)*tg
        if np.linalg.norm(n1)<1e-6: n1=np.cross(tg,[1.0,0,0])
        n1/=np.linalg.norm(n1); n2=np.cross(tg,n1); nprev=n1
        for a in range(nseg): th=2*np.pi*a/nseg; verts.append(pt+rad*(np.cos(th)*n1+np.sin(th)*n2))
    N=len(curve)
    for q in range(N-1):
        for a in range(nseg):
            a2=(a+1)%nseg; faces.append((q*nseg+a,(q+1)*nseg+a,(q+1)*nseg+a2)); faces.append((q*nseg+a,(q+1)*nseg+a2,q*nseg+a2))
    v0=len(verts); verts.append(curve[0]-tng[0]*rad*0.5); v1=len(verts); verts.append(curve[-1]+tng[-1]*rad*0.5)
    for a in range(nseg):
        a2=(a+1)%nseg; faces.append((v0,a2,a)); faces.append((v1,(N-1)*nseg+a,(N-1)*nseg+a2))
    return np.array(verts),np.array(faces)
out=dict(d); carts=[]; logj={}
for i in idx:
    if DTS[i] is None or LdS[i] is None: continue
    for side,sl in ((-1,'L'),(1,'R')):
        n=f'rib{i:02d}_{sl}'
        if n not in meas: continue
        j=meas[n]['j']; o=AP[j]
        H=o+glob(HDS[i]*MM,j,side)
        dch=DTS[i]/np.linalg.norm(DTS[i]); Lc=LdS[i]*MM
        Bk=H+glob(dch,j,side)*Lc
        outw=glob(np.array([0,0,1.0]),j,side); bw=outw-(outw@glob(dch,j,side))*glob(dch,j,side); bw/=np.linalg.norm(bw)
        tt=np.linspace(0,1,max(8,int(Lc/(0.3*MM))))[:,None]
        Cp=(H+Bk)/2+bw*BOW*Lc*2
        dors=(1-tt)**2*H+2*(1-tt)*tt*Cp+tt**2*Bk
        rad=RADS[i]*MM
        latB=((Bk-o)@AR[j])*side
        E=None
        if LvS.get(i) is not None and VTS[i] is not None and (Lv[i] or 0)>2 or (LvS.get(i) is not None and 5<=i<=14):
            vt=VTS[i] if VTS[i] is not None else np.array([-0.5,0.5,0]); h2=np.array([vt[0],vt[1]]); h2/=np.linalg.norm(h2)
            Lvv=LvS[i]*MM; dr=latB-0.3*MM; hl=np.sqrt(max(Lvv**2-dr**2,(0.3*Lvv)**2))
            E=Bk+glob(np.array([h2[0]*hl,h2[1]*hl,-dr]),j,side)
            tv=np.linspace(0,1,max(6,int(Lvv/(0.3*MM))))[:,None]; vent=Bk+(E-Bk)*tv
            curve=np.concatenate([dors,vent[1:]]); kind='bone ventral'
        else:
            curve=dors; kind='dorsal only'
        v,f=tube(curve,rad)
        Mi=np.linalg.inv(P['M'][bn.index(n)])
        out[n+'__v']=m2ct(v@Mi[:3,:3].T+Mi[:3,3]).astype(np.float32); out[n+'__f']=f.astype(np.int32)
        tip=curve[-1]; latT=((tip-o)@AR[j])*side
        if latT>0.6*MM:                                    # 正中に届かない: 腹側の軟骨で正中まで
            vt=None
            for di in (0,1,-1,2,-2,3,-3,4,-4):
                if VTS.get(i+di) is not None and (Lv.get(i+di) or 0)>2: vt=VTS[i+di]; break
            vt=vt if vt is not None else np.array([-0.4,0.9,0.0])
            h2=np.array([vt[0],vt[1]]); h2/=np.linalg.norm(h2)
            dr=latT-0.3*MM; hl=dr*0.8                       # 横に進む分の 0.8 倍を、横から見た向きへ（仮）
            Ec=tip+glob(np.array([h2[0]*hl,h2[1]*hl,-dr]),j,side)
            carts.append((tip,Ec,rad*0.8,n)); kind+=' + cartilage'
        logj[n]=dict(kind=kind,Ld=float(LdS[i]),Lv=(float(LvS[i]) if LvS.get(i) is not None else None),rad=float(RADS[i]),
                     head_mm=HDS[i].round(2).tolist(),dorsal_dir=dch.round(3).tolist())
# 軟骨: もとの肋骨の途切れ（cart__）は肋骨を作り直したので外し、腹側の軟骨に置き換える
if carts:
    A=[];B=[];Rr=[];Bo=[]
    for a,b,r,n in carts:
        Mi=np.linalg.inv(P['M'][bn.index(n)])
        A.append(m2ct(a@Mi[:3,:3].T+Mi[:3,3])); B.append(m2ct(b@Mi[:3,:3].T+Mi[:3,3])); Rr.append(r/k); Bo.append(n)
    out['cart__a']=np.array(A,np.float32); out['cart__b']=np.array(B,np.float32); out['cart__r']=np.array(Rr,np.float32); out['cart__bone']=np.array(Bo)
np.savez_compressed('chameleon_body_ct_ribs3.npz',**out)
json.dump({'ribs':logj,'cartilage':len(carts)},open('ribmodel.json','w'),indent=1,ensure_ascii=False)
pick={}
for n in logj:
    M=P['M'][bn.index(n)]; vr=ct2m(out[n+'__v']); pick[n]=(ct2m(d[n+'__v'])@M[:3,:3].T+M[:3,3], vr@M[:3,:3].T+M[:3,3])
pickle.dump(pick,open('rib_pts.pkl','wb'))
pickle.dump([(a,b,r) for a,b,r,n in carts],open('cart_pts.pkl','wb'))
for n in sorted(logj,key=lambda x:(int(x[3:5]),x[-1])): print(n,logj[n]['kind'],'Ld %.1f'%logj[n]['Ld'],'Lv',logj[n]['Lv'] and round(logj[n]['Lv'],1),'r %.2f'%logj[n]['rad'])
print('cartilage',len(carts))
