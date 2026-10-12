import numpy as np, scipy.ndimage as nd
from PIL import Image, ImageDraw
V=np.load('ct_ms50726_vol4.npz')['v'].astype(np.float32)
C=np.load('axis5_s.npy')*2+0.5; T=np.load('axis5_t.npy')   # full-res voxel coords
# rotation-minimizing frame
N=np.zeros_like(T); a=np.array([0,0,1.0]); n0=a-T[0]*T[0]@a; N[0]=n0/np.linalg.norm(n0)
for i in range(1,len(T)):
    n=N[i-1]-T[i]*(T[i]@N[i-1]); N[i]=n/np.linalg.norm(n)
B=np.cross(T,N)
# dorsal: direction where mask mass at 2-4mm is greatest -> rotate frame per sample by angle
M=np.load('Mc.npy')
ang=np.linspace(0,2*np.pi,24,endpoint=False)
score=np.zeros((len(C),24))
for k,t in enumerate(ang):
    d=np.cos(t)*N+np.sin(t)*B
    for r in (20,28,36):
        p=C+d*r
        score[:,k]+=nd.map_coordinates(M.astype(np.float32),p.T,order=0)
score=nd.uniform_filter1d(score,101,axis=0,mode='nearest')
best=ang[np.argmax(score,axis=1)]
# smooth angle via unit vectors
u=nd.uniform_filter1d(np.stack([np.cos(best),np.sin(best)],1),151,axis=0,mode='nearest'); th=np.arctan2(u[:,1],u[:,0])
Dv=np.cos(th)[:,None]*N+np.sin(th)[:,None]*B; Dv/=np.linalg.norm(Dv,axis=1)[:,None]
Lv=np.cross(T,Dv)
np.save('frame_D.npy',Dv); np.save('frame_L.npy',Lv)
rr=np.arange(-50,51)  # 0.104mm steps -> ±5.2mm
def img(U,W):
    out=np.zeros((len(rr),len(C)),np.float32)
    for w in range(-4,5):
        P=C[None]+U[None]*rr[:,None,None]+W[None]*w
        out=np.maximum(out,nd.map_coordinates(V,P.reshape(-1,3).T,order=1).reshape(len(rr),len(C)))
    return out
sag=img(Dv,Lv); cor=img(Lv,Dv)
np.save('straight_sag.npy',sag)
for nm,I in (('sag',sag),('cor',cor)):
    im=np.clip(I[::-1]*2.2,0,255).astype(np.uint8)
    for k in range(4):
        sl=slice(k*560,(k+1)*560+10)
        p=Image.fromarray(im[:,sl]).resize(((min((k+1)*560+10,im.shape[1])-k*560)*2,202)).convert('RGB'); d=ImageDraw.Draw(p)
        for mm in range(k*56,(k+1)*56+1):
            X=(mm*10-k*560)*2
            d.line([(X,0),(X,8 if mm%5 else 18)],fill=(255,255,0))
            if mm%5==0: d.text((X+2,186),str(mm),fill=(255,255,0))
        p.save(f'str_{nm}_{k}.png')
