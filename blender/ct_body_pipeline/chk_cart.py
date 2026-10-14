import numpy as np
exec(open('skinbody.py').read().split('def ray_hull')[0])
z=np.load('diag_inside.npz'); I=z['inside']; lo=z['lo']; VOX=float(z['vox'])
x=np.concatenate([apply(Mof(n),rest_cart[n]) for n in rest_cart])
g=((x-lo)/VOX).round().astype(int); ok=(g>=0).all(1)&(g<np.array(I.shape)).all(1)
ins=np.zeros(len(x),bool); ins[ok]=I[tuple(g[ok].T)]
print('cartilage points outside skin: %.2f%%'%(100*(~ins).mean()))
