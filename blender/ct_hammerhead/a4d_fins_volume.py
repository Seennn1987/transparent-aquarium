# A4: 決定後の胸びれ・肩帯・腹びれの点（u, z, v mm）を、最終の座標の 0.735 mm 格子に置き、なめらかな値の体積にする
import numpy as np
from scipy.ndimage import binary_closing, gaussian_filter
VX=0.735; U0,V0=-180.0,-150.0; NZ,NV,NU=1423,367,489
pe=np.load('pect_posed.npz'); pv=np.load('pelvic_posed.npz')
parts={'pect_L':pe['left'],'pect_R':pe['right'],'girdle':pe['girdle'],'pelv_L':pv['left'],'pelv_R':pv['right']}
for name,P in parts.items():
    iz=np.round(P[:,1]/VX).astype(int); iv=np.round((P[:,2]-V0)/VX).astype(int); iu=np.round((P[:,0]-U0)/VX).astype(int)
    lo=np.array([iz.min(),iv.min(),iu.min()])-4; hi=np.array([iz.max(),iv.max(),iu.max()])+5
    B=np.zeros(hi-lo,bool); B[iz-lo[0],iv-lo[1],iu-lo[2]]=True
    B=binary_closing(B,iterations=1)
    F=gaussian_filter(B.astype(np.float32),0.7)
    np.savez_compressed(f'a4_{name}.npz',field=F,origin=lo)
    print(name,len(P),'box',B.shape,'filled',int(B.sum()))
