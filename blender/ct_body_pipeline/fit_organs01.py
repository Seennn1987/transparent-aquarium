# 色 "01" の臓器の色を写真 01 から当てはめる（chameleon-stain.js STAINS["01"].organs）
#   入力: 写真 01（リポジトリ外ではないが再配布しない）、organcal.py で chameleon.html?stain=01 から書き出した web/cal01.npz
#   （通り道・膜の層・臓器ごとの通り道）と、lm.py の web/lm01.json（画面の関節窩・股関節）
# 写真 01 の胴の中の色（A〜D）を、画面の臓器の通り道に当てはめる
import numpy as np, json, math, sys
from PIL import Image
p=np.asarray(Image.open('/mnt/user-data/uploads/transparent-aquarium/transparent-aquarium/docs/references/chameleon/01-user-jar-diaphonized.jpg').convert('RGB')).astype(float)
Aph=-np.log(np.clip(p/224.0,1e-3,1))
cal=np.load('web/cal01.npz'); paths=np.maximum(cal['paths'],0); film=np.maximum(cal['film'][...,0],0)
org={k[4:]:np.maximum(cal[k],0) for k in cal.files if k.startswith('org_')}
lm=json.load(open('web/lm01.json'))
# 写真 → 画面（肩の関節窩と股関節の 2 点）
ph_g,ph_h=np.array([243.,305.]),np.array([127.,160.])
sc_g=(np.array(lm['fL_upper'])+np.array(lm['fR_upper']))/2; sc_h=(np.array(lm['hL_upper'])+np.array(lm['hR_upper']))/2
a=ph_h-ph_g; b=sc_h-sc_g; s=np.linalg.norm(b)/np.linalg.norm(a); ang=math.atan2(b[1],b[0])-math.atan2(a[1],a[0])
R=np.array([[math.cos(ang),-math.sin(ang)],[math.sin(ang),math.cos(ang)]])
T=lambda q: s*R@(np.asarray(q,float)-ph_g)+sc_g
print('photo->screen scale',round(s,3),'rot',round(math.degrees(ang),1))
# "01" の膜・膜の層・骨（chameleon-stain.js STAINS["01"]）
G={'film':np.array([0.1145,0.0728,0.0389]),'skin':np.array([0,0.109,0.230]),'bone':np.array([15.07,30.54,23.64])}
t0=0.042; F=t0*(1-np.exp(-paths[...,0]/t0))
base=film[...,None]*G['film']+paths[...,2][...,None]*G['skin']+F[...,None]*G['bone']
H,W=film.shape
yy,xx=np.mgrid[0:H,0:W]
REG={'A':((118,168,148,212),'濃い灰色の塊'),'B':((126,214,170,262),'褐色のまだら'),'C':((148,256,200,300),'褐色のまだら'),'D':((143,178,170,203),'黄緑')}
CLASS={'liver':['liver_r','liver_l'],'heart':['heart'],'gallbladder':['gallbladder'],'fat':['fat_r','fat_l'],'kidney':['kidney_r','kidney_l'],'gut':['stomach','intestine','colon'],'contents':['contents']}
cp={c:sum(org[n] for n in ns) for c,ns in CLASS.items()}
res={}
for r,((x0,y0,x1,y1),desc) in REG.items():
    cx,cy,rx,ry=(x0+x1)/2,(y0+y1)/2,(x1-x0)/2,(y1-y0)/2
    pm=((np.mgrid[0:447,0:447][1]-cx)/rx)**2+((np.mgrid[0:447,0:447][0]-cy)/ry)**2<=1
    Ap=np.median(Aph[pm],0)
    # 画面の同じ楕円（変換で写す）
    c_s=T((cx,cy)); rxs,rys=rx*s,ry*s
    # 楕円は回転も写す
    dx=xx-c_s[0]; dy=yy-c_s[1]; ex=(R.T@np.stack([dx.ravel(),dy.ravel()]))  # 写真の向きへ戻す
    sm=((ex[0]/rxs)**2+(ex[1]/rys)**2<=1).reshape(H,W)&(paths[...,2]>1e-4)
    meds={c:float(np.median(cp[c][sm])) for c in CLASS}
    Ab=np.median(base[sm],0)
    res[r]={'photo':Ap.round(3).tolist(),'base':Ab.round(3).tolist(),'excess':(Ap-Ab).round(3).tolist(),'paths':{c:round(v,4) for c,v in meds.items()},'n':int(sm.sum()),'desc':desc}
    print(r,desc,'photo',Ap.round(3),'base',Ab.round(3),'excess',(Ap-Ab).round(3),'n',sm.sum())
    print('   organ paths (median, model units):',{c:round(v,4) for c,v in meds.items() if v>0})
json.dump(res,open('fit_organs01.json','w'),ensure_ascii=False,indent=1)

# 体軸に沿った位置（肩 → 股関節を 0 → 1）でそろえる: 写真の斑は背側寄りで、画面の臓器（論文の配置で腹側）と重ならないため
def tpos(q,g,h): q=np.asarray(q,float); d=h-g; return ((q-g)@d)/(d@d)
tt=((np.stack([xx,yy],-1)-sc_g)@(sc_h-sc_g))/((sc_h-sc_g)@(sc_h-sc_g))
ASSIGN={'C':'liver','B':'contents','A':'contents'}
abs_unit={}; per={}
for r,cls in ASSIGN.items():
    (x0,y0,x1,y1),_=REG[r]; t=tpos(((x0+x1)/2,(y0+y1)/2),ph_g,ph_h)
    band=(np.abs(tt-t)<0.06)&(cp[cls]>1e-4)
    L=float(np.median(cp[cls][band]))
    ex=np.maximum(np.array(res[r]['excess']),0)
    per.setdefault(cls,[]).append(ex/L)
    print(r,'t %.2f'%t,'->',cls,'median path %.4f'%L,'n',int(band.sum()),'excess',ex.round(3),'absorbance per unit',(ex/L).round(2))
for cls,v in per.items(): abs_unit[cls]=np.mean(v,0).round(2).tolist()
print('abs_unit',abs_unit)
json.dump({'assign':ASSIGN,'abs_unit':abs_unit,'res':res},open('fit_organs01.json','w'),ensure_ascii=False,indent=1)
