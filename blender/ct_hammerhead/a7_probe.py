import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy.ndimage import map_coordinates
src=open(hh_paths.script('a4c_final_volume.py')).read()
head=src.split("C=np.load('zyg_clean.npy')")[0]
exec(head)
exec("cxs,cys=np.load('spine_line.npy'); tilt=np.load('tilt_sym.npy'); keep=np.load('tail_keep_v.npy')\noff=np.load('tail_bend_offset_mm.npy'); roll=np.load('neck_roll_deg.npy'); hy=json.load(open('head_yaw.json'))")
# 頭の幅の行（HEAD_SCALE=...、HH_HEAD_MM で案を作れる）から後ろを使う。前は行の文字そのもの（266.0/340.0）で切っていて、行を変えると止まった（2026-10-15）
import os, re
_m = re.search(r'^HEAD_SCALE=.*$', src, re.M)
exec(src[_m.start():].split('# 2026-10-14 A6')[0])
C=np.load('zyg_clean.npy',mmap_mode='r')
