import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, sys
from matplotlib.colors import ListedColormap
z=np.load('organs_lab.npz'); L=z['lab']; names=[str(n) for n in z['names']]
c=np.load('organs_cav.npz'); I=c['inside']; AP=c['AP']; lo=c['lo']; vox=float(c['vox'])
lung=np.load('organs_lung.npy')
cols={'heart':(0.85,0.1,0.1),'kidney_r':(0.5,0.2,0.6),'kidney_l':(0.6,0.3,0.7),'liver_r':(0.55,0.3,0.1),'liver_l':(0.65,0.4,0.15),'gallbladder':(0.2,0.7,0.2),
 'fat_r':(0.95,0.85,0.3),'fat_l':(1,0.9,0.4),'stomach':(0.9,0.6,0.6),'colon':(0.6,0.6,0.9),'intestine':(0.95,0.7,0.8),'contents':(0.2,0.2,0.2)}
def proj(axis):
    # 手前から見て最初の臓器（ax 方向）
    img=np.ones(I.shape[:axis]+I.shape[axis+1:]+(3,))*1.0
    sil=I.max(axis); img[sil]=(0.85,0.9,0.95)
    lg=lung.max(axis); img[lg]=(0.7,0.8,1.0)
    Lm=np.moveaxis(L,axis,0)
    first=np.zeros(Lm.shape[1:],np.int16)
    for s in range(Lm.shape[0]):
        m=(first==0)&(Lm[s]>0); first[m]=Lm[s][m]
    for j,n in enumerate(names,1): img[first==j]=cols[n]
    return img
fig,ax=plt.subplots(1,4,figsize=(26,12),gridspec_kw={'width_ratios':[1,1,0.9,0.9]})
a=proj(1); ax[0].imshow(np.transpose(a,(1,0,2))[::-1]); ax[0].set_title('from the left (camera side)')
# from the right: flip order
Lr=L[:,::-1,:]; Ls=lung[:,::-1,:]
L,lung_b=Lr,Ls; lung=Ls
b=proj(1); ax[1].imshow(np.transpose(b,(1,0,2))[::-1]); ax[1].set_title('from the right')
L=z['lab']; lung=np.load('organs_lung.npy')
A=(AP-lo)/vox
for j,zc in enumerate([0.45,0.7]):
    zi=int(I.shape[2]*zc); img=np.ones(I.shape[:2]+(3,)); img[I[:,:,zi]]=(0.85,0.9,0.95); img[lung[:,:,zi]]=(0.7,0.8,1.0)
    for jj,n in enumerate(names,1): img[L[:,:,zi]==jj]=cols[n]
    ax[2+j].imshow(np.transpose(img,(1,0,2))); ax[2+j].set_title(f'cross-section z={zi}')
from matplotlib.patches import Patch
ax[0].legend(handles=[Patch(color=cols[n],label=n) for n in names]+[Patch(color=(0.7,0.8,1),label='lung/air sac (rest)')],loc='lower right',fontsize=12)
plt.tight_layout(); plt.savefig(sys.argv[1],dpi=45)
