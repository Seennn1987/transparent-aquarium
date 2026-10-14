# chameleon_body_soft.npz: 膜（soft__）、内臓の一塊（visc__）、臓器（org_<名前>__）
import numpy as np, os
z=np.load('soft_rigged.npz'); out={'soft__'+k:z[k] for k in z.files}
# 内臓の一塊（visceramesh.py、CT の軟部から）は描かない（2026-10-14）: 臓器（organs.py）に置き換わり、骨から作った膜から 3.8% 出ていた
if os.environ.get('PACK_VISCERA') and os.path.exists('viscera_rigged.npz'):
    v=np.load('viscera_rigged.npz'); out.update({'visc__'+k:v[k] for k in v.files})
if os.path.exists('organs_rigged.npz'):
    o=np.load('organs_rigged.npz'); bones=o['names']
    for n in o['organs']:
        n=str(n)
        for kk in ('v','f','w_idx','w_val'): out[f'org_{n}__{kk}']=o[f'{n}__{kk}']
        out[f'org_{n}__names']=bones
np.savez_compressed('chameleon_body_soft.npz',**out); print('packed',len(out))
