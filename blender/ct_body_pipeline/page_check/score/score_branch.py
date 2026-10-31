# 枝の物差し（記録 128）: python score_branch.py <joints json> [-v]
"""枝の上の成体（YouTube Z3xPABzWUDE、0〜12 秒、1.5 秒ごと 9 コマ）を横から読んだ点と、モデルの着いている脚を、
手（足）の前後の位置がいちばん近いコマどうしで比べる（時刻ではなく脚の置き場で合わせる。実物はゆっくりで止まりながら歩くため）。
高さは枝の上の縁から、前後は肩（股）から、どれも ÷ 吻端–股関節 L。合格の幅: 高さ 0.03 L、前後 0.04 L、角度 15°（読みの誤差 ±0.016 L の 2 倍ほど）。
置き場: 実物の手（足）の前後にモデルの着いているコマが 0.05 L 以内に無ければ、その項目を不合格にする"""
import json,sys,numpy as np
RJ='/Users/shoui/transparent-aquarium/画像サンプル収集/エボシカメレオン/収集_2026-10-26/関節の動き/枝_Z3xPABzWUDE_0-12s.json'
R=json.load(open(RJ))['コマ']; rows=json.load(open(sys.argv[1])); L=123.3; V='-v' in sys.argv
HIND_SWING={6.0,7.5,9.0,10.5}
def ang(a,b,c):
    u=np.subtract(a,b,dtype=float);v=np.subtract(c,b,dtype=float);return float(np.degrees(np.arccos(np.clip(u@v/np.linalg.norm(u)/np.linalg.norm(v),-1,1))))
def tilt(top,bot): return float(np.degrees(np.arctan2(top[0]-bot[0],top[1]-bot[1])))
def items(root,mid,dist,end):  # どれも root を原点にせず、高さは枝の上の縁から、前後は root から
    return {'根の高さ':root[1],'中の高さ':mid[1],'先の高さ':dist[1],'中の前後':mid[0]-root[0],'中の角度':ang(root,mid,dist),'下の骨の傾き':tilt(mid,dist),'置き場':end[0]-root[0]}
real=[]
for c in R:
    Lp=np.hypot(c['hp'][0]-c['sn'][0],c['hp'][1]-c['sn'][1])
    P=lambda p,g: np.array([-p[0],g-p[1]],float)/Lp
    real.append(('前',c['t'],items(P(c['sh'],c['bf']),P(c['el'],c['bf']),P(c['wr'],c['bf']),P(c['ha'],c['bf']))))
    if c['t'] not in HIND_SWING: real.append(('後',c['t'],items(P(c['hp'],c['bh']),P(c['kn'],c['bh']),P(c['an'],c['bh']),P(c['ft'],c['bh']))))
mod={'前':[],'後':[]}
for k,lb in [('fL','前'),('hL','後')]:
    for r in rows:
        x=r[k]
        if not x['st']: continue
        g=np.array([0,x['hgt']/L]); mod[lb].append(items(g,g+np.array(x['knee'][:2])/L,g+np.array(x['ankle'][:2])/L,g+np.array(x['grip'][:2])/L))
NM={'前':{'根':'肩','中':'肘','先':'手首','下の骨':'前腕'},'後':{'根':'股','中':'膝','先':'足首','下の骨':'すね'}}
def name(lb,k):
    for a,b in NM[lb].items(): k=k.replace(a,b)
    return f'{lb} '+k.replace('置き場','手の置き場' if lb=='前' else '足の置き場')
res=[];ex=0
for lb,t,it in real:
    best=min(mod[lb],key=lambda m:abs(m['置き場']-it['置き場'])); gap=abs(best['置き場']-it['置き場'])
    for k,v in it.items():
        tol=15 if ('角度' in k or '傾き' in k) else 0.04 if ('前後' in k or '置き場' in k) else 0.03
        mv=best[k]; good=(abs(mv-v)<=tol) and (k=='置き場' or gap<=0.05)
        if k=='置き場': good=gap<=0.05
        ex+=max(0,(gap if k=='置き場' else abs(mv-v))-(0.05 if k=='置き場' else tol))/(0.05 if k=='置き場' else tol)
        res.append((name(lb,k),t,v,mv,good))
grp={}
for r in res: g=grp.setdefault(r[0],[0,0,[],[]]); g[0]+=r[4]; g[1]+=1; g[2].append(r[2]); g[3].append(r[3])
for g,(a,b,rv,mv) in grp.items(): print(f"{g:12s} {a}/{b}  実物 {np.mean(rv):+7.3f}  モデル {np.mean(mv):+7.3f}")
if V:
    for r in res:
        if not r[4]: print(f'× {r[0]} {r[1]:4.1f}秒 実物 {r[2]:+.3f} モデル {r[3]:+.3f}')
n=sum(r[4] for r in res); print(f'超過 {ex:.2f}'); print(f'合格 {n}/{len(res)}（{100*n/len(res):.0f}%）')
