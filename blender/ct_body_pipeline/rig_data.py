import numpy as np, json
J=np.load('J.npy'); C=(np.load('axis5_s.npy')*2+0.5)*0.104; s=np.arange(len(C))*0.1
def at(mm): return C[min(len(C)-1,int(round(mm/0.1)))]
d=np.load('bones_raw.npz'); names=sorted({k.split('__')[0] for k in d.files})
jt={k:np.array(v)*0.104 for k,v in json.load(open('joints.json')).items()}
bones={}
nv=max(int(n[1:]) for n in names if n.startswith('v'))
ROOT=22
SIDE=json.load(open('sides.json'))   # 四肢 A/B → 左右（sides.py）
for k in range(1,nv+1):
    nm=f'v{k:02d}'; a=at(J[k-1]); b=at(J[k]) if k<len(J) else C[-1]
    if k<ROOT: bones[nm]=(b,a,f'v{k+1:02d}')        # pivot posterior
    elif k==ROOT: bones[nm]=(a,b,None)
    else: bones[nm]=(a,b,f'v{k-1:02d}')
hv=d['head__v']; tip=hv[np.argmax(hv[:,0]-hv[:,1])]   # 吻端（CT 画像で左下）
bones['head']=(at(J[0]),tip,'v01')
# 舌骨（角鰓骨の棒など。頭の子）: 骨の根元 = 頭骨に最も近い点、先 = そこから最も遠い点
if 'hyoid__v' in d.files:
    yv=d['hyoid__v']; hc=at(J[0]); r0=yv[np.argmin(np.linalg.norm(yv-hv.mean(0),axis=1))]
    # 親は頸の椎骨（v02）。舌骨は喉の軟部に吊られていて、頭を回しても喉と一緒に残る。頭の子にすると、頭を下へ回したとき棒が胸の外へ振り出した
    bones['hyoid']=(r0,yv[np.argmax(np.linalg.norm(yv-r0,axis=1))],'v02')
def nearest_v(p):
    i=np.argmin(np.linalg.norm(C-p,axis=1)); k=int(np.searchsorted(J,s[i])); return f'v{max(1,min(nv,k)):02d}'
ch={'fA':['fA_scap0','fA_shoulder','fA_elbow','fA_wrist','fA_tip'],'fB':['fB_scap0','fB_shoulder','fB_elbow','fB_wrist','fB_tip'],
 'hA':['hA_hip0','hA_hip','hA_knee','hA_ankle','hA_tip'],'hB':['hB_hip','hB_knee','hB_ankle','hB_tip']}
seg={'fA':['girdle','upper','lower','hand'],'fB':['girdle','upper','lower','hand'],'hA':['girdle','upper','lower','foot'],'hB':['upper','lower','foot']}
for c,ks in ch.items():
    P=[jt[k] for k in ks]; par=nearest_v(P[0])
    for i,sn in enumerate(seg[c]):
        nm=f'{SIDE[c]}_{sn}'; bones[nm]=(P[i],P[i+1],par); par=nm
# 肋骨（左右・椎骨ごと）: 根元 = 中心線の始め、先 = 中心線の終わり（どちらも復元した位置）。親 = その椎骨
import ribrestore
for l,rb in ribrestore.ribs.items():
    nm=f"rib{rb['k']:02d}_{'RL'[(l-160)%2]}"
    if nm+'__v' not in d.files: continue
    tip=ribrestore.restore(rb['track'][-1:],np.array([l]))[0]
    bones[nm]=(rb['h']*0.104,tip*0.104,f"v{rb['k']:02d}")
# 中心線の無い肋骨（短い・途中で止まった）: 根元 = 体軸に最も近いメッシュの点、先 = そこから最も遠い点
for n in names:
    if n.startswith('rib') and n not in bones:
        v=d[n+'__v']; h=v[np.argmin(np.linalg.norm(v[:,None,:]-C[None,::20,:],axis=2).min(1))]
        bones[n]=(h,v[np.argmax(np.linalg.norm(v-h,axis=1))],f"v{int(n[3:5]):02d}")
missing=[n for n in names if n not in bones]; print('meshes without bone',missing)
print('no mesh',[b for b in bones if b not in names])
out={'names':np.array(list(bones)),'head':np.array([bones[b][0] for b in bones]),'tail':np.array([bones[b][1] for b in bones]),
     'parent':np.array([bones[b][2] or '' for b in bones])}
for b,(h,t,p) in bones.items(): print(b,p,np.round(h,1),np.round(t,1))
np.savez('rig.npz',**out)
