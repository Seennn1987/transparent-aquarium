set -e
cd "$(dirname "$0")"
cp "$1" B.npy
python3 bonemesh.py
python3 rig_data.py > rig.log
python3 -c "
import numpy as np
b=dict(np.load('bones_raw.npz')); r=np.load('rig.npz')
for k in r.files: b['rig__'+k]=r[k]
b['rig__axis']=((np.load('axis5_s.npy')*2+0.5)*0.104).astype(np.float32); b['rig__dorsal']=np.load('frame_D.npy')
b['rig__J']=np.load('J.npy'); b['rig__axis_step']=np.array(0.1)
import json, os
if os.path.exists('cart_gaps.json'):              # 肋骨の途切れをつなぐ軟骨（cartgaps.py）
    G=json.load(open('cart_gaps.json')); nm=json.load(open('bone_names.json'))
    b['cart__a']=np.array([g['a'] for g in G],np.float32); b['cart__b']=np.array([g['b'] for g in G],np.float32)
    b['cart__r']=np.array([g['radius_mm'] for g in G],np.float32); b['cart__bone']=np.array([nm[str(g['label'])] for g in G])
np.savez_compressed('chameleon_body_ct.npz',**b)
import os
if os.path.exists('soft_rigged.npz'):            # 膜は別のファイル（1 ファイルを 30 MB 未満に保つため）
    z=np.load('soft_rigged.npz'); np.savez_compressed('chameleon_body_soft.npz',**{'soft__'+k:z[k] for k in z.files})"
cp chameleon_body_ct.npz ../ctb/private/; [ -f chameleon_body_soft.npz ] && cp chameleon_body_soft.npz ../ctb/private/; rm -f ../ctb/private/chameleon_body_ct_dec.npz
