"""歩き方の時間の物差し（記録 139）: score_gait.py <walk_measure の _joints.json>
実物: Wimberly ら 2021 の床の歩き（エボシ成体の雄、304〜310 秒、4 本の足の着地を 0.1 秒ごとに読んだ。関節の動き.md 第 2 節）。
手前（右）前脚 着く 304.3・309.1、離れる 307.7／手前後脚 着く 306.9、離れる 305.3・310.1／奥（左）前脚 着く 306.5、離れる 305.1・309.7／奥後脚 着く 304.5・309.3、離れる 307.7
項目: 1 歩の秒、脚ごとの着いている割合、右前脚に対する各脚の着く時の遅れ（1 歩の割合）、同時に着いている脚の数の最小。合格の幅: 秒 ±10%、割合 ±0.04、遅れ ±0.05（読みの 0.1 秒 ≒ 0.02）"""
import json,sys,numpy as np
rows=json.load(open(sys.argv[1])); ts=np.array([r['t'] for r in rows]); dt=ts[1]-ts[0]
REAL={'T':4.8,'duty':{'fR':0.71,'hR':0.67,'fL':0.70,'hL':0.67},'lag':{'hL':0.04,'hR':0.54,'fL':0.46},'minDown':2}
def edges(k):
    st=np.array([r[k]['st'] for r in rows]); on=[ts[i] for i in range(1,len(st)) if st[i] and not st[i-1]]; off=[ts[i] for i in range(1,len(st)) if not st[i] and st[i-1]]
    return st,on,off
E={k:edges(k) for k in ['fR','fL','hR','hL']}
on=E['fR'][1]; T=float(np.median(np.diff(on))) if len(on)>1 else None
res=[]
def chk(name,mv,rv,tol): res.append((name,mv,rv,mv is not None and abs(mv-rv)<=tol))
chk('1 歩の秒',T,REAL['T'],0.1*REAL['T'])
for k,lab in [('fR','右前'),('hR','右後'),('fL','左前'),('hL','左後')]:
    st,o,_=E[k]; w=(ts>=o[0])&(ts<o[-1]) if len(o)>1 else None   # 着いてから最後に着くまでの全部の歩だけ
    chk(f'{lab}の着いている割合',float(st[w].mean()) if w is not None else None,REAL['duty'][k],0.04)
if T:
    t0=on[0]
    for k,lab in [('hL','左後'),('hR','右後'),('fL','左前')]:
        o=[x for x in E[k][1] if x>=t0]; lag=((o[0]-t0)/T)%1 if o else None
        chk(f'右前→{lab}の遅れ',lag,REAL['lag'][k],0.05)
down=np.sum([E[k][0] for k in E],axis=0); chk('同時に着いている脚の最小',float(down.min()),REAL['minDown'],0.5)
for n,m,r,g in res: print(f"{'○' if g else '×'} {n:14s} モデル {m if m is None else round(m,3)}  実物 {r}")
n=sum(r[3] for r in res); print(f'合格 {n}/{len(res)}')
