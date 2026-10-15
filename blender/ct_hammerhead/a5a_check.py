import hh_paths; hh_paths.cd_work()
import numpy as np
from PIL import Image
F=np.load('a4_skel_field.npy',mmap_mode='r'); S=np.load('a5_S.npy',mmap_mode='r'); NZ,NV,NU=S.shape
side=np.full((NV,NZ,3),255,np.uint8); top=np.full((NU,NZ,3),255,np.uint8); front=np.full((NV,NU,3),255,np.uint8)
bo_s=np.zeros((NV,NZ),bool); bo_t=np.zeros((NU,NZ),bool); bi_s=bo_s.copy(); bi_t=bo_t.copy(); sm=bo_s.copy(); tm=bo_t.copy(); fm=np.zeros((NV,NU),bool)
for k in range(0,NZ,100):
    b=np.asarray(F[k:k+100])>250; s=np.asarray(S[k:k+100]); o=b&~s; i=b&s; n=b.shape[0]
    sm[:,k:k+n]=s.any(2).T; tm[:,k:k+n]=s.any(1).T; fm|=s.any(0)
    bo_s[:,k:k+n]=o.any(2).T; bo_t[:,k:k+n]=o.any(1).T; bi_s[:,k:k+n]=i.any(2).T; bi_t[:,k:k+n]=i.any(1).T
for img,m,bi,bo in ((side,sm,bi_s,bo_s),(top,tm,bi_t,bo_t)):
    img[m]=(210,210,220); img[bi]=(90,90,95); img[bo]=(230,30,30)
front[fm]=(210,210,220)
W=NZ; Hh=NV+NU+20
im=Image.new('RGB',(W+NU+20,max(Hh,NV)),(255,255,255)); im.paste(Image.fromarray(side),(0,0)); im.paste(Image.fromarray(top),(0,NV+20)); im.paste(Image.fromarray(front),(W+20,0))
im.save('a5_check.png'); print(im.size)
