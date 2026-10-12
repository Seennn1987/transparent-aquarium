import numpy as np
def load():
    d=open('c.stl','rb').read(); n=int.from_bytes(d[80:84],'little')
    a=np.frombuffer(d[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
    T=a['v'].astype(np.float64)
    F=np.load('frame.npy'); e1,e2,nn=F; dd=np.load('sym.npy')[3]
    # 三角形を細かく点にする（0.1 mm 程度）
    pts=[T.mean(1)]
    for (u,v) in ((0.6,0.2),(0.2,0.6),(0.2,0.2)):
        pts.append(T[:,0]*(1-u-v)+T[:,1]*u+T[:,2]*v)
    P=np.concatenate([T.reshape(-1,3)]+pts)
    return np.stack([P@e1,P@e2,P@nn-dd],1)   # (u, w, L) mm。L は左右（対称面から）
