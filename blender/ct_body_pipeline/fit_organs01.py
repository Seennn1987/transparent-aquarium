# 写真 01 の胴の中の色（A〜D）を、画面の臓器の通り道に当てはめる
import numpy as np, json, math, sys
from PIL import Image
p=np.asarray(Image.open('/mnt/user-data/uploads/transparent-aquarium/transparent-aquarium/docs/references/chameleon/01-user-jar-diaphonized.jpg').convert('RGB')).astype(float)
Aph=-np.log(np.clip(p/224.0,1e-3,1))
# cal01.npz: organcal.py の書き出し。2026-10-15 の版は 1600×1912 で出たので、2×2 の平均で 800×956 に戻してから使った（lm01.json と同じ画素）
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
G={'film':np.array([0.1189,0.0791,0.0495]),'skin':np.array([0,0.0496,0.1000]),'bone':np.array([14.86,31.02,24.89])}   # fit_stain01.py（舌骨の作り直しの後、2026-10-15）
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

# v2（臓器を参考写真の範囲へ広げた後）: 画面の同じ楕円に腸の通り道が来るので、A・B は重なりで解く
#   各色で、excess = a_gut × 腸の通り道 + a_contents × 中身の通り道（どちらも 0 以上、最小二乗）。C は画面の同じ所に臓器が無いので、肝臓は上の t の帯の値のまま
from scipy.optimize import nnls
Mx=np.array([[res[r]['paths']['gut'],res[r]['paths']['contents']] for r in ('A','B')])
ex=np.array([np.maximum(res[r]['excess'],0) for r in ('A','B')])
sol=np.array([nnls(Mx,ex[:,c])[0] for c in range(3)]).T
print('overlap fit  gut',sol[0].round(2),'contents',sol[1].round(2),'residual',(Mx@sol-ex).round(3).tolist())
abs_unit['gut']=sol[0].round(2).tolist(); abs_unit['contents']=sol[1].round(2).tolist()
json.dump({'assign':ASSIGN,'abs_unit':abs_unit,'res':res,'v2':'gut and contents from the overlap of A and B'},open('fit_organs01.json','w'),ensure_ascii=False,indent=1)

# v2b: 写真と画面で胴の曲がりが違い、A・B の楕円は画面の塊の縁にかかる（腸の通り道の中央値が A 0.054・B 0.030 なのに、
#   画面の腸のある画素全体の中央値は 0.131）。そこで場所ではなく割合でそろえる（膜・骨と同じやり方）:
#   写真の塊（A と B の excess の平均）= 画面の腸の通り道の中央値 × a_gut
c2=np.load('web/cal01.npz'); g=sum(np.maximum(c2['org_'+n],0) for n in ('stomach','intestine','colon')); gm=float(np.median(g[g>1e-4]))
exm=np.mean([np.maximum(res[r]['excess'],0) for r in ('A','B')],0)
abs_unit['gut']=(exm/gm).round(2).tolist(); abs_unit['contents']=[0,0,0]
print('gut median path %.4f'%gm,'photo mass excess',exm.round(3),'-> gut',abs_unit['gut'])
json.dump({'assign':ASSIGN,'abs_unit':abs_unit,'res':res,'gut_median_path':gm,'v2':'gut from the share-matched median (A,B mean over the screen gut median path)'},open('fit_organs01.json','w'),ensure_ascii=False,indent=1)
