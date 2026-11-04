"""焼き込みで動いた手足の膜を戻す（記録 143）: restore_limb_skin.py <焼き込む前の glb> <焼き込んだ glb> <出力 glb> [手足の重みの下限 0.9]
胴の形の焼き込み（shape88）は胴を直す段だが、膜の動きを面に沿ってならす段などで、手足だけに付いた膜も 5〜17 mm 動いていた（右すね 中央値 5.7 mm）。
手足の骨（fL_/fR_/hL_/hR_）の重みの和が下限以上の CH_Skin の頂点の位置と法線を、焼き込む前に戻す。付け根（手足と胴の重みが混じる所）は焼き込みのまま"""
import sys,numpy as np
from glbio import GLB,skin_data
pre,bk,dst=sys.argv[1:4]; lim=float(sys.argv[4]) if len(sys.argv)>4 else 0.9
A=GLB(pre); B=GLB(bk); a=skin_data(A); b=skin_data(B)
assert len(a['P'])==len(b['P'])
nm=b['names']; isl=np.array([n[:3] in ('fL_','fR_','hL_','hR_') for n in nm])
lw=(b['W']*isl[b['J'].astype(int)]).sum(1); sel=lw>=lim
P=b['P'].copy(); P[sel]=a['P'][sel]
na=A.acc(a['prim']['attributes']['NORMAL'])[0]; nb=B.acc(b['prim']['attributes']['NORMAL'])[0].copy(); nb[sel]=na[sel]
B.put(b['prim']['attributes']['POSITION'],P); B.put(b['prim']['attributes']['NORMAL'],nb)
mm=1/(1.04/23.1); dv=np.linalg.norm(b['P'][sel]-a['P'][sel],axis=1)*mm
B.save(dst); print(f'戻した頂点 {int(sel.sum())}（焼き込みで動いていた 中央値 {np.median(dv):.2f}・最大 {dv.max():.2f} mm）')
