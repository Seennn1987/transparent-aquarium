# A3 名前のない塊を、起こした座標（derolled2 と同じ変換）で背骨と一緒に描く
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',13)
L=np.load('skel_lab.npy',mmap_mode='r'); cxs,cys=np.load('spine_line.npy'); t=np.load('tilt_sym.npy')
info=json.load(open('comps_info.json'))
def uvz(ids,z0,z1):
    sub=np.asarray(L[z0:z1]); out={}
    for i in ids:
        zz,yy,xx=np.nonzero(sub==i); z=zz+z0
        c=np.cos(np.radians(t[z])); s=np.sin(np.radians(t[z])); dx=xx-cxs[z]; dy=yy-cys[z]
        out[i]=np.stack([(c*dx+s*dy)*0.735,z*0.5,(-s*dx+c*dy)*0.735],1)
    return out
COLS=[(230,60,60),(40,110,220),(30,170,90),(230,150,20),(150,60,200),(0,170,190),(200,0,120),(120,120,0),(255,100,180),(90,60,20),(0,90,160),(180,180,0),(60,200,200),(220,90,0)]
def sheet(ids,zr,fname,title):
    z0,z1=int(zr[0]*2),int(zr[1]*2); P=uvz(ids+[4,0],z0,z1) if False else uvz(ids,z0,z1)
    bg=uvz([4],z0,z1)[4] if 4 in info or True else None
    W=int(zr[1]-zr[0]); views=[]
    for ax_v,lab in ((2,'横から（上が背）'),(0,'背中から')):
        img=np.full((260,W,3),255,np.uint8)
        def put(p,col):
            i=(p[:,1]-zr[0]).astype(int); j=(p[:,ax_v]+130).astype(int); ok=(i>=0)&(i<W)&(j>=0)&(j<260); img[j[ok],i[ok]]=col
        put(bg,(170,170,170))
        for k,i in enumerate(ids): put(P[i],COLS[k%len(COLS)])
        im=Image.fromarray(img).resize((W*3,260*3),Image.NEAREST); d=ImageDraw.Draw(im)
        for k,i in enumerate(ids):
            p=P[i]
            if len(p)==0: continue
            c=p.mean(0); d.text(((c[1]-zr[0])*3+6,(c[ax_v]+130)*3-8),str(i),fill=COLS[k%len(COLS)],font=F)
        d.text((4,4),lab,fill=(0,0,0),font=F)
        for mm in range(int(zr[0])//20*20+20,int(zr[1]),20):
            x=(mm-zr[0])*3; d.line((x,0,x,10),fill=(200,0,0)); d.text((x+2,10),str(mm),fill=(200,0,0),font=F)
        views.append(im)
    S=Image.new('RGB',(views[0].width,sum(v.height for v in views)+40),(255,255,255)); y=0
    for v in views: S.paste(v,(0,y)); y+=v.height+10
    ImageDraw.Draw(S).text((4,S.height-22),title+'（灰=背骨の塊 4。数字は吻端からの mm。背骨のまわりの座標は胴の起こし方のまま）',fill=(60,60,60),font=F)
    S.save(fname)
    return {i:{'n':int(len(P[i])),'u':[round(float(P[i][:,0].min())),round(float(P[i][:,0].max()))],'v':[round(float(P[i][:,2].min())),round(float(P[i][:,2].max()))],'z':[round(float(P[i][:,1].min())),round(float(P[i][:,1].max()))]} for i in ids if len(P[i])}
a=sheet([1,12,197,206,451,458,468,495,712,731,784,827,1341],(0,280),'comps_head.png','頭〜胸の名前のない塊')
b=sheet([2670,2990,3867,4865,4874,4899,4922],(400,800),'comps_trunk.png','胴〜尾の名前のない塊')
json.dump({**{str(k):v for k,v in a.items()},**{str(k):v for k,v in b.items()}},open('comps_unnamed.json','w'),indent=0)
for k,v in {**a,**b}.items(): print(k,v)
