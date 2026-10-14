# 起こした体（derolled4）で、頭の正中線を上から見た外形の鏡映で探す
import numpy as np
from scipy.ndimage import map_coordinates, binary_fill_holes
D=np.load('derolled4.npy',mmap_mode='r'); H=np.asarray(D[0:140])            # z 0..139 mm, (v,u) 1.47mm
top=binary_fill_holes((H>-400).any(1)).astype(float)                         # (z 1mm, u 1.47mm), u 中心 150
np.save('head_top_derolled.npy',top)
def score(cu,ang):
    t=np.tan(np.radians(ang)); zi,ui=np.nonzero(top>0); zm=zi*1.0; um=(ui-150)*1.47
    d=((um-cu)-t*(zm-70))/np.hypot(1,t); n=np.array([1,-t])/np.hypot(1,t)
    ur=um-2*d*n[0]; zr=zm-2*d*n[1]
    return map_coordinates(top,[zr,ur/1.47+150],order=0,cval=0).mean()
best=sorted(((score(c,a),c,a) for c in np.arange(-40,40.1,1.5) for a in np.arange(-25,25.1,1)),reverse=True)
print([(round(s,3),round(c,1),a) for s,c,a in best[:6]])
# 胴の側: 背骨は u=0（z>=140 mm）
