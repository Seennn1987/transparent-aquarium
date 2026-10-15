"""シロシュモクザメの CT 処理の置き場を 1 か所で決める。どのスクリプトも、先頭でここから読む。

  WORK  中間ファイル（.npy・.npz・確認の図・数表）。既定は blender/ct_hammerhead/work/
  MESH  PLY の面。既定は blender/ct_hammerhead/mesh/
  DOCS  Blender で描いた確認の図の書き出し先。既定は docs/hammerhead_ct/
  GLB   標本ページの glb。既定は 水槽/scenes/specimen/assets/specimen_hammerhead.glb
  ZIP   全身 CT の元の zip（リポジトリの外）
  REF   写真から読んだ外形など、手で用意した入力（docs/hammerhead_ct/ref/。git に入っている）

作り直しを試すときは、環境変数 HH_WORK・HH_MESH・HH_DOCS・HH_GLB で別のフォルダへ向ける（run_all.sh）。
cd_work() は、カレントフォルダを WORK にする（スクリプトの中のファイル名は WORK からの名前）。
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.environ.get("HH_SCRIPTS", "/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_hammerhead")
ROOT = os.path.dirname(os.path.dirname(HERE))
WORK = os.environ.get("HH_WORK") or os.path.join(HERE, "work")
MESH = os.environ.get("HH_MESH") or os.path.join(HERE, "mesh")
DOCS = os.environ.get("HH_DOCS") or os.path.join(ROOT, "docs", "hammerhead_ct")
GLB = os.environ.get("HH_GLB") or os.path.join(ROOT, "水槽", "scenes", "specimen", "assets", "specimen_hammerhead.glb")
ZIP = os.environ.get("HH_ZIP") or os.path.expanduser(
    "~/transparent-aquarium/シュモクザメ/全身CT/Sphyrna_zygaena_シロシュモクザメ_ZMA.PISC.108725.zip")
REF = os.path.join(ROOT, "docs", "hammerhead_ct", "ref")


def cd_work():
    os.makedirs(WORK, exist_ok=True)
    os.chdir(WORK)


def script(name):
    """同じフォルダのスクリプトのパス（exec(open(...).read()) で一部を流用するとき）"""
    return os.path.join(HERE, name)


def blender_scene(name):
    """Blender で、描く・書き出すための別のシーン（開いている .blend の他のシーンには触れない）。
    blender -b（画面なし、--factory-startup）では、起動したシーンの中身を空にし、名前を変えて使う"""
    import bpy
    sc = bpy.data.scenes.get(name)
    if bpy.context.window is None:
        if sc is None:
            sc = bpy.context.scene
            sc.name = name
            for ob in list(sc.objects):
                bpy.data.objects.remove(ob, do_unlink=True)
        return sc
    if sc is None:
        sc = bpy.data.scenes.new(name)
    bpy.context.window.scene = sc
    return sc


_FONTS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",        # 前の担当の Linux
          "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc"]


def font(size):
    """確認の図の文字（日本語が出るもの）"""
    from PIL import ImageFont
    for p in _FONTS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()
