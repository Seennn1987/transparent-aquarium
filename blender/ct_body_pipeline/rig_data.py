import numpy as np, json
J=np.load('J.npy'); C=(np.load('axis5_s.npy')*2+0.5)*0.104; s=np.arange(len(C))*0.1
def at(mm): return C[min(len(C)-1,int(round(mm/0.1)))]
d=np.load('bones_raw.npz'); names=sorted({k.split('__')[0] for k in d.files})
jt={k:np.array(v)*0.104 for k,v in json.load(open('joints.json')).items()}
bones={}
nv=max(int(n[1:]) for n in names if n.startswith('v'))
ROOT=22
for k in range(1,nv+1):
    nm=f'v{k:02d}'; a=at(J[k-1]); b=at(J[k]) if k<len(J) else C[-1]
    if k<ROOT: bones[nm]=(b,a,f'v{k+1:02d}')        # pivot posterior
    elif k==ROOT: bones[nm]=(a,b,None)
    else: bones[nm]=(a,b,f'v{k-1:02d}')
hv=d['head__v']; tip=hv[np.argmax(hv[:,0]-hv[:,1])]   # 吻端（CT 画像で左下）
bones['head']=(at(J[0]),tip,'v01')
def nearest_v(p):
    i=np.argmin(np.linalg.norm(C-p,axis=1)); k=int(np.searchsorted(J,s[i])); return f'v{max(1,min(nv,k)):02d}'
ch={'fA':['fA_scap0','fA_shoulder','fA_elbow','fA_wrist','fA_tip'],'fB':['fB_scap0','fB_shoulder','fB_elbow','fB_wrist','fB_tip'],
 'hA':['hA_hip0','hA_hip','hA_knee','hA_ankle','hA_tip'],'hB':['hB_hip','hB_knee','hB_ankle','hB_tip']}
seg={'fA':['girdle','upper','lower','hand'],'fB':['girdle','upper','lower','hand'],'hA':['girdle','upper','lower','foot'],'hB':['upper','lower','foot']}
for c,ks in ch.items():
    P=[jt[k] for k in ks]; par=nearest_v(P[0])
    for i,sn in enumerate(seg[c]):
        nm=f'{c}_{sn}'; bones[nm]=(P[i],P[i+1],par); par=nm
missing=[n for n in names if n not in bones]; print('meshes without bone',missing)
print('no mesh',[b for b in bones if b not in names])
out={'names':np.array(list(bones)),'head':np.array([bones[b][0] for b in bones]),'tail':np.array([bones[b][1] for b in bones]),
     'parent':np.array([bones[b][2] or '' for b in bones])}
for b,(h,t,p) in bones.items(): print(b,p,np.round(h,1),np.round(t,1))
np.savez('rig.npz',**out)
