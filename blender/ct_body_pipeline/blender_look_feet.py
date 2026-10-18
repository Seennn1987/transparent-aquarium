"""後ろ足（骨・膜・爪の鞘）を、画面なしの Blender に読み込んで寄って描く（記録 31、2026-10-18）。書き出しとページの撮影を待たずに、
形を何方向からも数秒で確かめるための道具。見た目の最終確認はページで撮る（CLAUDE.md の決まり）。

  cd <案の作業フォルダ> && /Applications/Blender.app/Contents/MacOS/Blender -b -P blender_look_feet.py -- <出力の頭> [骨=hL_foot,hR_foot]

読むもの（作業フォルダ）: pose_jar.npz、chameleon_body_ct.npz（骨、静止）、skin_posed.npz（膜、展示の姿勢）、
chameleon_body_soft.npz の org_claw（爪の鞘、静止。あれば）。座標は展示の姿勢のモデルの座標（skinbody.py と同じ）。
描くもの: 骨ごとに、足の骨の重心を中心に 4 方向（前・後・上・下、骨の第 1〜3 主成分の向き）。骨は赤、膜は半透明の青、爪の鞘は黄。
開いている Blender（MCP）は使わない（別の標本の会話が使っている）。
"""
import sys
import numpy as np
import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]; BONES = argv[1].split(',') if len(argv) > 1 else ['hL_foot', 'hR_foot']
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k'])
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz'); S = np.load('skin_posed.npz')
try:
    So = np.load('chameleon_body_soft.npz'); has_claw = 'org_claw__v' in So.files
except FileNotFoundError:
    has_claw = False

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def mesh(name, v, f, color):
    me = bpy.data.meshes.new(name); me.from_pydata(v.tolist(), [], f.tolist()); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); ob.color = color; return ob
# 足の骨と下腿の骨
for n in bn:
    if n.startswith(('hL_', 'hR_')) and n + '__v' in d.files:
        mesh('bone_' + n, posed(n, d[n + '__v']), d[n + '__f'], (0.75, 0.1, 0.15, 1))
mesh('skin', S['v'].astype(float), S['f'], (0.2, 0.35, 0.8, 0.35))
if has_claw:
    cv = So['org_claw__v'].astype(float); cn = [str(x) for x in So['org_claw__names']]; wi = So['org_claw__w_idx'][:, 0]
    cp = np.zeros_like(cv)
    for i, n in enumerate(cn): cp[wi == i] = posed(n, cv[wi == i])
    mesh('claw', cp, So['org_claw__f'], (0.95, 0.8, 0.2, 1))
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_xray = True; sh.xray_alpha = 0.6
sh.show_object_outline = True; sh.show_cavity = False
sc.render.resolution_x = 900; sc.render.resolution_y = 900; sc.render.film_transparent = False
sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.88, 0.88, 0.88)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
for n in BONES:
    x = posed(n, d[n + '__v']); c = x.mean(0); U = np.linalg.svd(x - c, full_matrices=False)[2]
    size = np.ptp((x - c) @ U.T, 0).max() * 1.5
    cam.data.ortho_scale = size; cam.data.clip_start = 0.001 * size; cam.data.clip_end = 100 * size
    for tag, dirv in (('a', U[2]), ('b', -U[2]), ('c', U[1]), ('d', -U[1])):
        cam.location = Vector(c + dirv * size * 3)
        cam.rotation_euler = (Vector(c) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = f'{out}_{n}_{tag}.png'; bpy.ops.render.render(write_still=True)
        print('wrote', sc.render.filepath)
