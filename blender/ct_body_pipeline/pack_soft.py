# chameleon_body_soft.npz: 膜（soft__）、内臓の一塊（visc__）、臓器（org_<名前>__）
import numpy as np, os
z=np.load('soft_rigged.npz'); out={'soft__'+k:z[k] for k in z.files}
if os.path.exists('viscera_rigged.npz'):
    v=np.load('viscera_rigged.npz'); out.update({'visc__'+k:v[k] for k in v.files})
if os.path.exists('organs_rigged.npz'):
    o=np.load('organs_rigged.npz'); bones=o['names']
    for n in o['organs']:
        n=str(n)
        for kk in ('v','f','w_idx','w_val'): out[f'org_{n}__{kk}']=o[f'{n}__{kk}']
        out[f'org_{n}__names']=bones
np.savez_compressed('chameleon_body_soft.npz',**out); print('packed',len(out))
