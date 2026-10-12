import numpy as np, json, sys, scipy.ndimage as nd
B=np.load(sys.argv[1]); c=sys.argv[2]; base={'hA':30,'hB':40}[c]; up,lw=(base+1,base+2) if c=='hA' else (40,41)
J={k:np.array(v,float) for k,v in json.load(open('joints.json')).items()}
H,K,A=J[c+'_hip'],J[c+'_knee'],J[c+'_ankle']
V=np.argwhere(np.isin(B,(up,lw))).astype(float)
pts=[H,K,A]; L=[np.linalg.norm(K-H),np.linalg.norm(A-K)]
# param along polyline: project to nearest segment
def proj(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/(ab@ab),0,1); return t, np.linalg.norm(P-(a+t[:,None]*ab),axis=1)
t1,d1=proj(V,H,K); t2,d2=proj(V,K,A)
s=np.where(d1<=d2,t1*L[0],L[0]+t2*L[1])
for x in range(0,int(L[0]+L[1]),8):
    m=(s>=x)&(s<x+3); Q=V[m]
    if len(Q)<3: print(x,0); continue
    q=(Q-Q.min(0)).astype(int); G=np.zeros(q.max(0)+1,bool); G[tuple(q.T)]=True
    n=nd.label(G,np.ones((3,3,3)))[1]
    w=np.ptp(Q,0); print(x,'n',len(Q),'comps',n,'ext',w.round())
print('L',np.round(L))
