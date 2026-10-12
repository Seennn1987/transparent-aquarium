import numpy as np, scipy.ndimage as nd
V=np.load('ct_ms50726_vol4.npz')['v']; M=np.load('M.npy')
B=V>=130; l,n=nd.label(B); s=nd.sum(B,l,range(1,n+1)); disc=l==(np.argmax(s)+1)
disc=nd.binary_dilation(disc,iterations=4)
M2=M&~disc
lab,n=nd.label(M2); s=nd.sum(M2,lab,range(1,n+1)); M2=np.isin(lab,np.nonzero(s>=150)[0]+1)
print('removed',(M&~M2).sum())
np.save('Mc.npy',M2)
