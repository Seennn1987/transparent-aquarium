import numpy as np, json
from scipy.ndimage import map_coordinates
src=open('a4_final_volume.py').read()
head=src.split("C=np.load('zyg_clean.npy')")[0]
exec(head)
exec("cxs,cys=np.load('spine_line.npy'); tilt=np.load('tilt_sym.npy'); keep=np.load('tail_keep_v.npy')\noff=np.load('tail_bend_offset_mm.npy'); roll=np.load('neck_roll_deg.npy'); hy=json.load(open('head_yaw.json'))")
exec('HEAD_SCALE=266.0/340.0\n'+src.split('HEAD_SCALE=266.0/340.0')[1].split('# 2026-10-14 A6')[0])
C=np.load('zyg_clean.npy',mmap_mode='r')
