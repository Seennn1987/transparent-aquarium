# 皮膚・筋肉の膜（透明標本で白く濁る薄い膜）の外形を、同じ全身 CT の軟部から作る。
#   軟部 = 濃さ 20 以上（この CT は 1〜19 が 0 にそろえてある。20 以上で体の外形が写る）の密度。半分の解像度（0.208 mm）で扱う
#   外すもの: 標識の円板（130 以上の最大の塊、まわり 0.4 mm）、別の個体の骨（intruder.npy）の方が自分の骨より近い軟部、
#             自分の骨から 5 mm より遠い軟部、1 ボクセルのざらつき（開く）。残りの最大の塊を使う
#   外側の面だけを作る: 外から届かない所（体の中の空洞）は埋めてから面にする
#   出力: soft_mesh.npz（v: CT のボクセル座標（全解像度）、f: 三角形）
import numpy as np, scipy.ndimage as nd
from skimage import measure
V=np.load('ct_ms50726_vol4.npz')['v']; B=np.load('B_h10.npy'); IN=np.load('intruder.npy')
dl,n=nd.label(V>=130); sz=np.bincount(dl.ravel()); sz[0]=0; disc=nd.binary_dilation(dl==sz.argmax(),iterations=4)
# 軟部は JPEG のざらつきで点々に写る（濃さの低い皮膚・筋肉は半分ほどのボクセルが 0）。
# 2×2×2 の中の 20 以上の割合を σ 0.4 mm でぼかし、0.12 以上を軟部とする（外側の薄い皮膚の点々まで含める）
Sd=((V>=20)&~disc).reshape(376,2,350,2,182,2).mean((1,3,5)).astype(np.float32)
S=nd.gaussian_filter(Sd,2.0)>=0.12
ours=((B>0)&~disc).reshape(376,2,350,2,182,2).any((1,3,5)); intr=IN.reshape(376,2,350,2,182,2).any((1,3,5))
d_ours=nd.distance_transform_edt(~ours); d_in=nd.distance_transform_edt(~intr)
keep=S&~(d_in<d_ours)&(d_ours<=24)
keep=nd.binary_opening(keep,np.ones((3,3,3)))
lab,n=nd.label(keep); sz=np.bincount(lab.ravel()); sz[0]=0; keep=lab==sz.argmax()
keep=nd.binary_closing(np.pad(keep,3),iterations=2)[3:-3,3:-3,3:-3]
outside=nd.label(~np.pad(keep,1))[0]; outside=(outside==outside[0,0,0])[1:-1,1:-1,1:-1]
solid=~outside
print('soft voxels (half res)',int(keep.sum()),'solid',int(solid.sum()))
F=nd.gaussian_filter(np.pad(solid,2).astype(np.float32),1.0)
v,f,_,_=measure.marching_cubes(F,0.5)
v=(v-2)*2+0.5                      # 全解像度のボクセル座標
np.savez_compressed('soft_mesh.npz',v=v.astype(np.float32),f=f.astype(np.int32))
np.save('soft_solid_half.npy',solid)
print('verts',len(v),'faces',len(f))
