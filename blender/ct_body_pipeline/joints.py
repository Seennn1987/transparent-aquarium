import numpy as np, scipy.ndimage as nd, json
W=np.load('W2.0.npy')
def contact(a,b):
    A=W==a; B=nd.binary_dilation(W==b,iterations=2)
    p=np.argwhere(A&B); return p.mean(0) if len(p) else None
def pts(ids): return np.argwhere(np.isin(W,ids)).astype(float)
def farthest(ids,frm):
    P=pts(ids); d=np.linalg.norm(P-frm,axis=1); k=np.argsort(d)[-max(20,len(d)//200):]; return P[k].mean(0)
def ends(cid):
    P=pts([cid]); c=P.mean(0); u=np.linalg.svd(P-c,full_matrices=False)[2][0]; t=(P-c)@u
    return P[t<np.percentile(t,2)].mean(0), P[t>np.percentile(t,98)].mean(0)
def bend(cid,a,b):
    P=pts([cid]); ab=b-a; t=((P-a)@ab)/(ab@ab); m=(t>0.2)&(t<0.8)
    d=np.linalg.norm(np.cross(P-a,ab),axis=1)/np.linalg.norm(ab)
    k=np.argsort(np.where(m,d,-1))[-30:]; far=P[k].mean(0)
    # the joint is on the medial line between: take point on the bone near far
    return far
J={}
# forelimb A
J['fA_scap0']=contact(63,5); J['fA_shoulder']=contact(63,30); J['fA_elbow']=(contact(30,28)+contact(28,32))/2
J['fA_wrist']=contact(32,56); J['fA_tip']=farthest([66,67,74,79],J['fA_wrist'])
# forelimb B
J['fB_shoulder']=contact(35,80); J['fB_wrist']=(contact(35,58)+contact(35,69))/2
J['fB_elbow']=bend(35,J['fB_shoulder'],J['fB_wrist']); J['fB_scap0']=farthest([80],J['fB_shoulder'])
J['fB_tip']=farthest([69,75,77,89,87],J['fB_wrist'])
# hind A
J['hA_hip0']=contact(11,5); J['hA_hip']=contact(11,1); J['hA_knee']=contact(1,3)
J['hA_tip']=farthest([23,24,25,26,27],J['hA_knee'])
e1,e2=ends(9); J['hA_ankle']=e1 if np.linalg.norm(e1-J['hA_knee'])>np.linalg.norm(e2-J['hA_knee']) else e2
# hind B
f1,f2=ends(50)
P19=pts([19]); 
J['hB_hip']=np.array([75,82,108.])
k1,k2=(f1,f2) if np.linalg.norm(f1-J['hB_hip'])<np.linalg.norm(f2-J['hB_hip']) else (f2,f1)
J['hB_knee']=k1; J['hB_ankle']=k2; J['hB_tip']=farthest([116,118],k2)
J={k:(v*2+1).round(1).tolist() for k,v in J.items()}   # full-res coords
json.dump(J,open('joints.json','w'),indent=1)
for k,v in J.items(): print(k,v)
