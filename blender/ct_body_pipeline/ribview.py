import numpy as np, sys
from PIL import Image
B=np.load(sys.argv[1]); out=sys.argv[2]
rng=np.random.default_rng(5); col=rng.integers(70,255,(256,3)).astype(np.uint8); col[:160]=0
ims=[]
for side in (0,1):
    sub=np.where((B>=160)&(B<202)&((B-160)%2==side),B,0)
    nz=sub>0; idx=nz.argmax(2); lab=np.take_along_axis(sub,idx[...,None],2)[...,0]
    rgb=col[lab]; rgb[(lab==0)&((B>=102)&(B<=123)).any(2)]=(60,60,60)
    ims.append(Image.fromarray(rgb).crop((100,0,700,640)))
w=Image.new('RGB',(ims[0].width*2+10,ims[0].height)); w.paste(ims[0],(0,0)); w.paste(ims[1],(ims[0].width+10,0)); w.save(out)
