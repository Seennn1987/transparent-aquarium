# 骨を展示の姿勢へ置く（mm）。diag_bundles.py が読む
import numpy as np, scipy.ndimage as nd, json, sys
from scipy.spatial import cKDTree
import scipy.sparse as sp; from scipy.sparse.csgraph import dijkstra
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k'])
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
d=np.load('chameleon_body_ct.npz')
def posed(n): M=Mp[bn.index(n)]; return (ct2m(d[n+'__v'])@M[:3,:3].T+M[:3,3])/k   # mm
