"""肋骨と椎骨だけを、画面なしの Blender で横・前・下から描く（記録 48 の点検。2026-10-21）。

  cd <作業フォルダ> && Blender -b -P blender_look_ribs.py -- <出力の頭> [rib を選ぶ: all か 09,10,11 のような番号]

読むもの: pose_jar.npz、chameleon_body_ct.npz、skin_posed.npz（膜は半透明で重ねる）。展示の姿勢のモデルの座標。
向きは胴（肩–股関節）の軸で決める: 横 = 左右の向きから、前 = 体軸の向きから（頭の側から尾へ見る）、下 = 腹から。
"""
import os
import sys
import numpy as np
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]; pick = argv[1] if len(argv) > 1 else 'all'
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k'])
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz'); rn = [str(s) for s in d['rig__names']]
J = lambda n: posed(n, d['rig__head'][rn.index(n)][None])[0]
sh = (J('fL_upper') + J('fR_upper')) / 2; hp = (J('hL_upper') + J('hR_upper')) / 2
ax = hp - sh; L = np.linalg.norm(ax); ax /= L
lat = J('fL_upper') - J('fR_upper'); lat -= ax * (lat @ ax); lat /= np.linalg.norm(lat); dor = np.cross(ax, lat)
vert = np.concatenate([posed(n, d[n + '__v']) for n in bn if n[0] == 'v' and n[1:].isdigit() and n + '__v' in d.files])
if dor @ (vert.mean(0) - (sh + hp) / 2) < 0: dor = -dor
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def mesh(name, v, f, color):
    me = bpy.data.meshes.new(name); me.from_pydata(np.asarray(v, float).tolist(), [], np.asarray(f).tolist()); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.color = color; return ob
for n in bn:
    if n + '__v' not in d.files: continue
    if n.startswith('rib'):
        if pick != 'all' and n[3:5] not in pick.split(','): continue
        mesh(n, posed(n, d[n + '__v']), d[n + '__f'], (0.75, 0.1, 0.2, 1) if n.endswith('_L') else (0.2, 0.3, 0.8, 1))
    elif n[0] == 'v' and n[1:].isdigit() and int(n[1:]) <= 24:
        mesh(n, posed(n, d[n + '__v']), d[n + '__f'], (0.5, 0.5, 0.5, 1))
S = np.load('skin_posed.npz'); mesh('skin', S['v'], S['f'], (0.6, 0.75, 0.9, 0.25))
sc.render.engine = 'BLENDER_WORKBENCH'; sh_ = sc.display.shading
sh_.light = 'STUDIO'; sh_.color_type = 'OBJECT'; sh_.show_xray = True; sh_.xray_alpha = 0.85; sh_.show_object_outline = False
sc.render.resolution_x = 1400; sc.render.resolution_y = 1000
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.95, 0.95, 0.95)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.type = 'ORTHO'
c = (sh + hp) / 2
for tag, dirv, up, size in (('side', lat, dor, 1.6 * L), ('front', -ax, dor, 0.9 * L), ('below', -dor, -ax, 1.6 * L)):
    cam.data.ortho_scale = size; cam.data.clip_start = 0.001; cam.data.clip_end = 100 * L
    cam.location = Vector(c + dirv * 5 * L)
    import mathutils
    zc = Vector(dirv).normalized(); yc = Vector(up) - zc * Vector(up).dot(zc); yc.normalize(); xc = yc.cross(zc)
    cam.rotation_euler = mathutils.Matrix((xc, yc, zc)).transposed().to_euler()      # カメラは −Z を見る（zc = 対象からカメラへ）
    sc.render.filepath = f'{out}_{tag}.png'; bpy.ops.render.render(write_still=True); print('wrote', sc.render.filepath)
