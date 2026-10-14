# 段階 1 の 2（肋骨の作り直し 2）: 胸郭を、生体の X 線で測った幅と深さの、左右対称の楕円の輪にする（ribmodel.py の後継）
#   2026-10-14 の指摘「上から見たときにお腹の幅がなさすぎる」: CT の個体の胸郭の幅は約 9.5 mm で、生体の X 線の約半分だった
#   （保存標本は横に寝かせると胸が横から押される）。
#   肋骨ごとに: 体軸に直角な面の楕円（半幅 Wh、上 = 肋骨の頭の高さ、下 = 腹の正中の深さ Dv）をたどる線にする。
#     体軸に沿った向き: 背側の部分は CT の背側の弦の「尾へ ÷ 腹へ」の比、折れ角より下は CT の腹側の部分の比（頭の側へ戻る）
#     骨の長さは CT の長さ（下の LB）。骨の先から腹の正中までは軟骨（腹の正中で左右がつながる。madcham.de、Williston 1925）
#   太さ・頭の位置・弦の向きは ribmodel.py と同じ測り方
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
import numpy as np, os, json, pickle, scipy.sparse as sp
from scipy.sparse import csgraph
from scipy.spatial import cKDTree
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; k=float(P['k']); MM=k
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
def m2ct(m): m=np.asarray(m,float)/k; return np.stack([-m[...,2],m[...,0],-m[...,1]],-1)
d=dict(np.load(os.environ.get('RIB_IN','chameleon_body_ct.npz'))); c=np.load('organs_cav.npz'); us=c['us']; AP=c['AP']; AV=c['AV']; AR=c['AR']
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

# ---- 胸郭の形（生体の X 線から。頭骨の長さ 23.1 mm を単位に測った値。数値は目測で仮） ----
#   幅: 背腹方向の X 線 2 枚（veterinaryradiology.net、lbah.com）で、胴のいちばん広い所の幅 ÷ 頭骨の長さ = 0.80、0.82
#     → 体の幅 ≈ 0.81 × 23.1 = 18.7 mm。膜の厚さを両側 1 mm と見て、胸郭の半幅の最大 WMAX = 8.5 mm
#     幅の前後の変わり方（肩 → 股、t = 0 → 1）: 2 枚の X 線の輪郭から WPROF
#   深さ: 横向きの X 線（veterinaryradiology.net）で、骨の肋骨の届く深さ ÷ 頭骨の長さ ≈ 0.83（いまの CT の肋骨とほぼ同じ）、
#     腹の皮膚までは さらに 0.49。X 線に写らない軟骨（腹側の肋骨）は腹の壁まで続くと見て（madcham.de: ほとんどの肋骨は胸骨か
#     反対側の肋骨の軟骨につながる）、胸郭の腹の正中の深さ = (0.83 + 0.49) × 23.1 − 皮膚 1 mm ≈ 29 mm を最大にする（仮）。
#     前後の変わり方は横向きの X 線の腹の線から DPROF（体軸から [mm]）
U0,UHIP=9.5,107.5
WMAX=8.5
WPROF=[(0.0,0.72),(0.3,0.88),(0.6,1.0),(0.8,0.97),(1.0,0.80)]
DPROF=[(0.0,20.0),(0.3,26.5),(0.6,29.0),(0.85,26.0),(1.0,18.0)]
SLOPES=[float(x) for x in os.environ['RIB_SLOPES'].split(',')] if os.environ.get('RIB_SLOPES') else None
CART_TIP=float(os.environ['RIB_CART_TIP']) if os.environ.get('RIB_CART_TIP') else None
DV_OVR=json.load(open(os.environ['DV_JSON'])) if os.environ.get('DV_JSON') else {}
def prof(tab,u):
    t=(u-U0)/(UHIP-U0); x,y=zip(*tab); return float(np.interp(t,x,y))
# 骨の長さ: CT の背側 + 腹側。15〜20 の CT の肋骨は 5〜13 mm と短い（ラベルの切れか、実際に短いかは確かめていない）。
#   乾燥骨格（AMNH）と写真 01 では後ろの肋骨も腹近くまで並ぶので、14 から 21 へなめらかに短くなる長さの方を大きく取る（仮）
LB={i:(LdS[i]+(LvS.get(i,0.0) if (Lv.get(i) or 0)>2 else 0.0)) for i in idx}
for i in range(15,21): LB[i]=max(LB[i],float(np.interp(i,[14,21],[LB[14],LB[21]])))
def tube(curve,rad,nseg=10):
    curve=np.asarray(curve); tng=np.gradient(curve,axis=0); tng/=np.linalg.norm(tng,axis=1,keepdims=True)
    verts=[]; faces=[]; nprev=None
    for pt,tg in zip(curve,tng):
        n1=np.cross(tg,[0,0,1.0]) if nprev is None else nprev-(nprev@tg)*tg
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
def ratio(D,i,default):
    for di in (0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6):
        if D.get(i+di) is not None and abs(D[i+di][1])>0.2: v=D[i+di]; return float(np.clip(v[0]/v[1],-1.2,1.2))   # 腹へ進む成分が小さい弦は使わない
    return default
out=dict(d); carts=[]; logj={}
for i in idx:
    pr=pairs(i)
    if not pr or HDS.get(i) is None: continue
    for side,sl in ((-1,'L'),(1,'R')):
        n=f'rib{i:02d}_{sl}'
        if n not in meas: continue
        j=meas[n]['j']; o=AP[j]; u=float(us[j])
        Wh=WMAX*prof(WPROF,u); Dv=prof(DPROF,u)
        ovr=DV_OVR.get(str(i))
        if ovr is not None: Dv=float(ovr[0] if isinstance(ovr,list) else ovr)   # 生体の X 線の腹の線に合わせた深さ（ribdepth.py）
        hd=HDS[i]; th_t,v_top,r_h=hd[0],max(hd[1],0.5),max(hd[2],0.8)
        if r_h>=Wh*0.95: r_h=Wh*0.5
        bv=(Dv-v_top)/2; vc=(Dv+v_top)/2
        th0=np.arcsin(r_h/Wh)
        th=np.linspace(th0,np.pi,400)
        rr_=Wh*np.sin(th); vv_=vc-bv*np.cos(th)
        vb=min(v_top+LdS[i]*(DTS[i][1] if DTS[i] is not None else 0.9),Dv-1.0)
        rd=ratio(DTS,i,0.4); rv=ratio({x:y for x,y in VTS.items() if (Lv.get(x) or 0)>2},i,-0.5)
        if SLOPES:                                          # 生体の X 線の肋骨の向き（ribdepth.py の説明）
            rd,rv,bf=SLOPES; vb=v_top+bf*(Dv-v_top)
            if isinstance(ovr,list) and len(ovr)>1: rv=float(ovr[1])   # 胸骨より前へ出ないよう、肋骨ごとに腹側の向きを弱める（ribdepth.py）
        tt_=np.where(vv_<=vb, th_t+rd*(vv_-v_top), th_t+rd*(vb-v_top)+rv*(vv_-vb))
        pts=o+tt_[:,None]*MM*T[j]+vv_[:,None]*MM*AV[j]+(side*rr_)[:,None]*MM*AR[j]
        sl_=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]/MM
        Lb=LB[i]
        if CART_TIP is not None: Lb=max(Lb,sl_[-1]-CART_TIP)   # 腹側の肋骨は骨（写真 01 では腹の縁まで赤、X 線にも写る）。軟骨は正中の手前 CART_TIP mm だけ（仮）
        nb=int(np.searchsorted(sl_,Lb))
        bone=pts[:max(nb,2)][::4] if nb>8 else pts[:max(nb,2)]
        rad=RADS[i]*MM
        v,f=tube(bone,rad)
        Mi=np.linalg.inv(P['M'][bn.index(n)])
        out[n+'__v']=m2ct(v@Mi[:3,:3].T+Mi[:3,3]).astype(np.float32); out[n+'__f']=f.astype(np.int32)
        if nb<len(pts)-2:                                   # 骨の先から腹の正中まで軟骨（1.5 mm ごとの棒）
            rest=pts[nb-1:]; sr=sl_[nb-1:]-sl_[nb-1]
            marks=np.arange(0,sr[-1]+1e-9,1.5)
            if marks[-1]<sr[-1]: marks=np.r_[marks,sr[-1]]
            q=np.array([rest[np.searchsorted(sr,m) if np.searchsorted(sr,m)<len(rest) else -1] for m in marks])
            for a_,b_ in zip(q[:-1],q[1:]): carts.append((a_,b_,rad*0.85,n))
        logj[n]=dict(u=u,Wh=Wh,Dv=Dv,path_mm=float(sl_[-1]),bone_mm=float(min(Lb,sl_[-1])),cart_mm=float(max(sl_[-1]-Lb,0)),rad=float(RADS[i]))
# 軟骨: もとの肋骨の途切れ（cart__）は肋骨を作り直したので外し、腹側の軟骨に置き換える
if carts:
    A=[];B=[];Rr=[];Bo=[]
    for a,b,r,n in carts:
        Mi=np.linalg.inv(P['M'][bn.index(n)])
        A.append(m2ct(a@Mi[:3,:3].T+Mi[:3,3])); B.append(m2ct(b@Mi[:3,:3].T+Mi[:3,3])); Rr.append(r/k); Bo.append(n)
    out['cart__a']=np.array(A,np.float32); out['cart__b']=np.array(B,np.float32); out['cart__r']=np.array(Rr,np.float32); out['cart__bone']=np.array(Bo)
np.savez_compressed(os.environ.get('RIB_OUT','chameleon_body_ct_ribs4.npz'),**out)
json.dump({'ribs':logj,'cartilage':len(carts)},open('ribmodel2.json','w'),indent=1,ensure_ascii=False)
pick={}
for n in logj:
    M=P['M'][bn.index(n)]; vr=ct2m(out[n+'__v']); pick[n]=(ct2m(d[n+'__v'])@M[:3,:3].T+M[:3,3], vr@M[:3,:3].T+M[:3,3])
pickle.dump(pick,open('rib_pts.pkl','wb'))
pickle.dump([(a,b,r) for a,b,r,n in carts],open('cart_pts.pkl','wb'))
for n in sorted(logj,key=lambda x:(int(x[3:5]),x[-1])):
    if n.endswith('_L'): g=logj[n]; print(n,'u %.0f W %.1f D %.1f path %.1f bone %.1f cart %.1f'%(g['u'],2*g['Wh'],g['Dv'],g['path_mm'],g['bone_mm'],g['cart_mm']))
print('cartilage',len(carts))
