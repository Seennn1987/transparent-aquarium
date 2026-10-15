import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy import ndimage as ndi
D=np.load('derolled5.npy',mmap_mode='r')
def sym(m,ang):
    r=ndi.rotate(m.astype(np.uint8),ang,reshape=False,order=0).astype(bool)
    uu=np.nonzero(r)[1]; r=np.roll(r,150-int(round(uu.mean())),axis=1)
    return (r&r[:,::-1]).sum()/max((r|r[:,::-1]).sum(),1)
out=[]
for z in range(150,331,5):
    m=ndi.binary_fill_holes(np.asarray(D[z])>-400); A=range(-30,31,2); s=[sym(m,a) for a in A]
    i=int(np.argmax(s)); out.append((z,list(A)[i],round(s[i],3),round(s[15],3)))
print(out); json.dump(out,open('neck_roll2.json','w'))
