import json, numpy as np, math, sys
m=json.load(open(sys.argv[1]))
def xz(p): return np.array([p[0],p[2]])
# 写真 01 の画素（447px、y は下向き）
PH={'snout':(278,392),'casque':(183,338)}
near_pts={'elbow':(222,266),'wrist':(272,251),'tip':(308,250)}
far_pts={'elbow':(253,281),'wrist':(298,277),'tip':(318,276)}
def ph(p): return np.array([p[0],-p[1]],float)
a0,a1=ph(PH['casque']),ph(PH['snout']); b0,b1=xz(m['casque']),xz(m['snout'])
# similarity: z = s R (p - a0) + b0
va,vb=a1-a0,b1-b0; s=np.linalg.norm(vb)/np.linalg.norm(va); ang=math.atan2(vb[1],vb[0])-math.atan2(va[1],va[0])
R=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]])
T=lambda p: s*R@(ph(p)-a0)+b0
print('scale model/px',round(s,4),'rot deg',round(math.degrees(ang),1))
ys={c:m[c+'_upper'][0][1] for c in ('fR','fL')}
near=min(ys,key=ys.get); far=max(ys,key=ys.get); print('near',near,ys)
res={}
for c,pts in ((near,near_pts),(far,far_pts)):
    gl=np.array(m[c+'_upper'][0])
    chain=[('upper',gl,T(pts['elbow'])),]
    L={b:np.linalg.norm(np.array(m[c+'_'+b][1])-np.array(m[c+'_'+b][0])) for b in ('upper','lower')}
    Lh=np.linalg.norm(np.array(m[c+'_tip'])-np.array(m[c+'_hand'][0]))
    start=xz(gl); 
    for b,tgt,Lb in (('upper',T(pts['elbow']),L['upper']),('lower',T(pts['wrist']),L['lower']),('hand',T(pts['tip']),Lh)):
        v=tgt-start; n=np.linalg.norm(v)
        th=math.degrees(math.atan2(v[1],v[0])); ph_=math.degrees(math.acos(min(1,n/Lb)))
        print(c,b,'in-plane',round(n,3),'len',round(Lb,3),'theta',round(th,1),'phi',round(ph_,1), 'reach' if n<=Lb else 'TOO FAR x%.2f'%(n/Lb))
        res[c+'_'+b]=(round(th,1),round(ph_,1))
        start=start+v*min(1,Lb/n)
    # current model elbow 2D vs target
    print(c,'model glenoid px', None)
json.dump(res,open('fore_fit.json','w'))
# inverse: model glenoid to photo px for reporting
Ti=lambda z: (np.linalg.inv(s*R)@(np.asarray(z)-b0))+a0
for c in (near,far):
    q=Ti(xz(m[c+'_upper'][0])); e=Ti(xz(m[c+'_upper'][1])); print(c,'glenoid in photo px',(round(q[0]),round(-q[1])),'model elbow in photo px',(round(e[0]),round(-e[1])))
