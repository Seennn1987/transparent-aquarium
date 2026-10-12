import numpy as np, json, sys
from PIL import Image, ImageDraw
B=np.load(sys.argv[2] if len(sys.argv)>2 else 'B_r8.npy'); J=json.load(open('joints.json'))
c=sys.argv[1]; base={'fA':10,'fB':20,'hA':30,'hB':40}[c]
cols={0:(255,90,90),1:(90,255,90),2:(90,140,255),3:(255,230,0)}
m=(B>=base)&(B<base+4); P=np.argwhere(m); lo=np.maximum(P.min(0)-10,0); hi=P.max(0)+10
sub=B[tuple(slice(a,b) for a,b in zip(lo,hi))]; sub=np.where((sub>=base)&(sub<base+4),sub,0)
ims=[]
for ax,(r,cc) in ((2,(0,1)),(1,(0,2)),(0,(1,2))):
    nz=sub!=0; idx=nz.argmax(ax); lab=np.take_along_axis(sub,np.expand_dims(idx,ax),ax).squeeze(ax)
    dep=np.where(nz.any(ax),idx,0)
    rgb=np.zeros(lab.shape+(3,),np.uint8)
    for k,cl in cols.items():
        mm=lab==base+k; shade=(1-0.6*dep/max(1,sub.shape[ax]))[mm][:,None]; rgb[mm]=(np.array(cl)*shade).astype(np.uint8)
    im=Image.fromarray(rgb).resize((lab.shape[1]*2,lab.shape[0]*2)); d=ImageDraw.Draw(im)
    for k,v in J.items():
        if k.startswith(c):
            p=np.array(v)-lo; y,x=p[r]*2,p[cc]*2; d.ellipse([x-5,y-5,x+5,y+5],outline=(255,255,255),width=2); d.text((x+6,y-6),k[3:],fill=(255,255,255))
    ims.append(im)
W=sum(i.width for i in ims)+20; H=max(i.height for i in ims); out=Image.new('RGB',(W,H),(40,40,40)); x=0
for i in ims: out.paste(i,(x,0)); x+=i.width+10
out.save(f'limb_{c}.png'); print(out.size, lo, hi)
