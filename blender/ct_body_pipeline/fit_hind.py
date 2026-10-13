# 写真 01 の膝・足首・指先に合わせて、後肢の向き（θ, φ）を解く。
# 頭の 2 点で重ねると胴の曲がりの違いで腰がずれるので、腰のところで重ね直す:
#   倍率は頭で決めた値（同じ個体）、向きは腰の背骨（v20→v26）を 01 の背骨（腰の高さで縦）にそろえ、股関節の中点を 01 の股関節に置く
import json, numpy as np, math, sys
m=json.load(open(sys.argv[1]))
xz=lambda p: np.array([p[0],p[2]],float)
ph=lambda p: np.array([p[0],-p[1]],float)
# 倍率（頭）
a0,a1=ph((183,338)),ph((278,392)); b0,b1=xz(m['casque']),xz(m['snout'])
s=np.linalg.norm(b1-b0)/np.linalg.norm(a1-a0)
# 向き（腰の背骨）
A=m['axial']; sm=xz(A['v26'][0])-xz(A['v20'][0])
sp=ph((114,120))-ph((115,200))                      # 01 の背骨、腰の高さ（股関節より尾側へ）
ang=math.atan2(sm[1],sm[0])-math.atan2(sp[1],sp[0])
R=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]])
HIP=(127,160)                                        # 01 の股関節（手前の大腿の、体に近い端）
hipm=(xz(m['hL_upper'][0])+xz(m['hR_upper'][0]))/2
T=lambda p: s*R@(ph(p)-ph(HIP))+hipm
Ti=lambda z: np.linalg.inv(s*R)@(np.asarray(z)-hipm)+ph(HIP)
print('scale',round(s,4),'rot',round(math.degrees(ang),1))
ys={c:m[c+'_upper'][0][1] for c in ('hL','hR')}; near=min(ys,key=ys.get); far=max(ys,key=ys.get); print('near',near)
PTS={near:{'knee':(188,152),'ankle':(218,129),'tip':(256,118)}, far:{'knee':(170,192),'ankle':(226,181),'tip':(277,178)}}
res={}
for c in (near,far):
    pts=PTS[c]; start=xz(m[c+'_upper'][0])
    q=Ti(start); print(c,'hip in photo',(round(q[0]),round(-q[1])))
    Ls={'upper':np.linalg.norm(np.subtract(*m[c+'_upper'])),'lower':np.linalg.norm(np.subtract(*m[c+'_lower'])),'foot':np.linalg.norm(np.array(m[c+'_tip'])-np.array(m[c+'_foot'][0]))}
    for b,k in (('upper','knee'),('lower','ankle'),('foot','tip')):
        v=T(pts[k])-start; n=np.linalg.norm(v); L=Ls[b]
        th=math.degrees(math.atan2(v[1],v[0])); phi=math.degrees(math.acos(min(1,n/L)))
        print(c,b,'in-plane px',round(n/s,1),'bone px',round(L/s,1),'theta',round(th,1),'phi',round(phi,1),'' if n<=L else 'TOO FAR x%.2f'%(n/L))
        res[c+'_'+b]=(round(th,1),round(phi,1)); start=start+v*min(1,L/n)
json.dump(res,open('hind_fit.json','w')); print(res)
