# 枝の物差し（記録 128）: python score_branch.py <joints json> [-v]
"""枝の上の成体（YouTube Z3xPABzWUDE、0〜12 秒、1.5 秒ごと 9 コマ）を横から読んだ点と、モデルの着いている脚を、
手（足）の前後の位置がいちばん近いコマどうしで比べる（時刻ではなく脚の置き場で合わせる。実物はゆっくりで止まりながら歩くため）。
高さは枝の上の縁から、前後は肩（股）から、どれも ÷ 吻端–股関節 L。合格の幅: 高さ 0.03 L、前後 0.04 L、角度 15°（読みの誤差 ±0.016 L の 2 倍ほど）。
置き場: 実物の手（足）の前後にモデルの着いているコマが 0.05 L 以内に無ければ、その項目を不合格にする"""
import json,sys,numpy as np
RJ='/Users/shoui/transparent-aquarium/画像サンプル収集/エボシカメレオン/収集_2026-10-26/関節の動き/枝_Z3xPABzWUDE_0-12s.json'
_RJ=json.load(open(RJ)); R=_RJ['コマ']; R2=_RJ.get('後ろ脚の追加コマ',[]); rows=json.load(open(sys.argv[1])); L=123.3; V='-v' in sys.argv
HIND_SWING={6.0,7.5,9.0,10.5}
def ang(a,b,c):
    u=np.subtract(a,b,dtype=float);v=np.subtract(c,b,dtype=float);return float(np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v),-1,1))))
def tilt(top,bot): return float(np.degrees(np.arctan2(top[0]-bot[0],top[1]-bot[1])))
def items(root,mid,dist,end):  # どれも root を原点にせず、高さは枝の上の縁から、前後は root から
    return {'根の高さ':root[1],'中の高さ':mid[1],'先の高さ':dist[1],'中の前後':mid[0]-root[0],'中の角度':ang(root,mid,dist),'下の骨の傾き':tilt(mid,dist),'置き場':end[0]-root[0]}
real=[]
# 記録 134: 肩・股の関節は胴に隠れて見えない。読んだ点は腕・脚が皮から出る所なので、モデルと同じ「関節」にそろえるため、
# 見えた大腿の向きに、膝から大腿骨の長さ 0.184 L の所へ置き直す。肩は上腕が短く見え（0.08〜0.15 L）向きが定まらないので置き直さず、
# 前脚の前後（肘・手）は股の関節から測る（モデルも股の関節から）
def joint_from(sn,mid,seen,k):
    sn=np.array(sn,float); mid=np.array(mid,float); u=np.array(seen,float)-mid; u/=np.linalg.norm(u); p=np.array(seen,float)
    for _ in range(30): p=mid+u*k*np.linalg.norm(p-sn)
    return p.tolist()
for c in R:
    c['hp']=joint_from(c['sn'],c['kn'],c['hp'],0.184)
for c in R:
    Lp=np.hypot(c['hp'][0]-c['sn'][0],c['hp'][1]-c['sn'][1])
    P=lambda p,g: np.array([-p[0],g-p[1]],float)/Lp
    it=items(P(c['sh'],c['bf']),P(c['el'],c['bf']),P(c['wr'],c['bf']),P(c['ha'],c['bf'])); hpx=-c['hp'][0]/Lp
    it['中の前後']=-c['el'][0]/Lp-hpx; it['置き場']=-c['ha'][0]/Lp-hpx
    real.append(('前',c['t'],it))
    if c['t'] not in HIND_SWING: real.append(('後',c['t'],items(P(c['hp'],c['bh']),P(c['kn'],c['bh']),P(c['an'],c['bh']),P(c['ft'],c['bh']))))
for c in R2:   # 記録 133: 12 秒以後、後ろ脚が着いて間もないコマ
    Lp=np.hypot(c['hp'][0]-c['sn'][0],c['hp'][1]-c['sn'][1])
    P=lambda p,g: np.array([-p[0],g-p[1]],float)/Lp
    real.append(('後',c['t'],items(P(c['hp'],c['bh']),P(c['kn'],c['bh']),P(c['an'],c['bh']),P(c['ft'],c['bh']))))
mod={'前':[],'後':[]}
for k,lb in [('fL','前'),('hL','後')]:
    for r in rows:
        x=r[k]
        if not x['st']: continue
        g=np.array([0,x['hgt']/L]); it=items(g,g+np.array(x['knee'][:2])/L,g+np.array(x['ankle'][:2])/L,g+np.array(x['grip'][:2])/L)
        if lb=='前':
            d=(x['upF']-r['hL']['upF'])/L; it['中の前後']+=d; it['置き場']+=d
        mod[lb].append(it)
NM={'前':{'根':'肩','中':'肘','先':'手首','下の骨':'前腕'},'後':{'根':'股','中':'膝','先':'足首','下の骨':'すね'}}
def name(lb,k):
    for a,b in NM[lb].items(): k=k.replace(a,b)
    k=k.replace('置き場','手の置き場' if lb=='前' else '足の置き場')
    if lb=='前' and ('前後' in k or '置き場' in k): k+='（股から）'
    return f'{lb} '+k
res=[];ex=0
for lb,t,it in real:
    best=min(mod[lb],key=lambda m:abs(m['置き場']-it['置き場'])); gap=abs(best['置き場']-it['置き場'])
    for k,v in it.items():
        tol=15 if ('角度' in k or '傾き' in k) else 0.04 if ('前後' in k or '置き場' in k) else 0.03
        mv=best[k]; good=(abs(mv-v)<=tol) and (k=='置き場' or gap<=0.05)
        if k=='置き場': good=gap<=0.05
        ex+=max(0,(gap if k=='置き場' else abs(mv-v))-(0.05 if k=='置き場' else tol))/(0.05 if k=='置き場' else tol)
        res.append((name(lb,k),t,v,mv,good))
# 正面の項目（記録 129）: 前脚が着いている間の 0.1・0.3・0.5 で、上腕の開き 45°（X 線の 3D 骨格、記録 114、ほかの実物と食い違わない）と
# 前腕の内への倒れ 28°（細い枝の上の成体を斜め前から写した YouTube 8pzT_m3hNfc の 55 秒・57.5 秒を目で読んだ。斜めなので ±15°）。
FRONT=[('前 正面 上腕の開き',1,45.0),('前 正面 前腕の内への倒れ',2,28.0)]
DUTY=0.6555; T=95/36.4
st=[r['fL']['st'] for r in rows]; ts=[r['t'] for r in rows]; t0=[ts[i] for i in range(1,len(rows)) if st[i] and not st[i-1]][0]
FR=[]
for r in rows:
    if not r['fL']['st']: continue
    ph=((r['t']-t0)%T)/T/DUTY; kn=np.array(r['fL']['knee']); an=np.array(r['fL']['ankle']); g=an-kn
    FR.append((ph,float(np.degrees(np.arctan2(kn[2],-kn[1]))),float(np.degrees(np.arctan2(-g[2],-g[1])))))
for q in (0.1,0.3,0.5):
    m=min(FR,key=lambda x:abs(x[0]-q))
    for nm,i,rv in FRONT:
        mv=m[i]; good=abs(mv-rv)<=15; ex+=max(0,abs(mv-rv)-15)/15; res.append((nm,q,rv,mv,good))
grp={}
for r in res: g=grp.setdefault(r[0],[0,0,[],[]]); g[0]+=r[4]; g[1]+=1; g[2].append(r[2]); g[3].append(r[3])
for g,(a,b,rv,mv) in grp.items(): print(f"{g:14s} {a}/{b}  実物 {np.mean(rv):+7.3f}  モデル {np.mean(mv):+7.3f}")
if V:
    for r in res:
        if not r[4]: print(f'× {r[0]} {r[1]:4.1f}秒 実物 {r[2]:+.3f} モデル {r[3]:+.3f}')
n=sum(r[4] for r in res); print(f'超過 {ex:.2f}'); print(f'合格 {n}/{len(res)}（{100*n/len(res):.0f}%）')
