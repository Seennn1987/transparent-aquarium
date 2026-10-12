import numpy as np, scipy.ndimage as nd
from PIL import Image
M=np.load('Mc.npy')
m=M.reshape(M.shape[0]//2,2,M.shape[1]//2,2,M.shape[2]//2,2).mean((1,3,5))>=0.25
np.save('m2.npy',m)
F=nd.binary_fill_holes(nd.binary_closing(m,iterations=1))
D=nd.distance_transform_edt(F).astype(np.float32); np.save('D2.npy',D)
for t in (1.5,2.0,2.5,3.0):
    K=D>=t; Image.fromarray((K.max(axis=2)*255).astype(np.uint8)).save(f'thick_{t}.png'); print(t,K.sum())
