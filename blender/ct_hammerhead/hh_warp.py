"""シロシュモクザメ: 胴の長さを縮める写像（2026-10-16 案、プロデューサー「胴の幅（第 1 背びれのあたりを一番太く）と後ろ半分の長さの案、
尾の骨（血道弓・尾びれの鰭条・肋骨）の案を両方作って、ブラウザで並べて見せて」）。

体軸（吻端からの長さ z、mm）の [Z0, Z1]（頭の後ろ〜尾びれの前）を SHRINK 倍に縮め、後ろの尾びれはそのまま前へずらす。
  Z0 = 150 mm: 頭の骨だけの区間（b1_rig.py の head、〜126 mm）と、頭から胴へ移る重み（100〜140 mm）より後ろ
  Z1 = 737 mm: 尾びれの前（全長の 0.72。a9_body_shape_check の「尾柄」）
環境変数 HH_BODY_SHRINK（既定 1 = 縮めない）。0.885 で 尾びれの前まで = 全長の 0.70（ICCAT の PCL の式）、1 体の全長は 1024 → 957 mm。
a6a_export_gltf.py（面の頂点）、b1_rig.py（骨の位置）、a5a_shell.py（胴の幅を、縮めた後の全長の割合で決める）が使う。
"""
import os

Z0, Z1, TL0 = 150.0, 737.0, 1024.0
SHRINK = float(os.environ.get("HH_BODY_SHRINK", 1.0))


def warp_mm(z):
    """元の z（mm）→ 縮めた後の z（mm）。numpy の配列もそのまま受ける"""
    import numpy as np
    z = np.asarray(z, dtype=float)
    return np.where(z < Z0, z, np.where(z < Z1, Z0 + (z - Z0) * SHRINK, z - (Z1 - Z0) * (1 - SHRINK)))


def unwarp_mm(zf):
    import numpy as np
    zf = np.asarray(zf, dtype=float); z1f = Z0 + (Z1 - Z0) * SHRINK
    return np.where(zf < Z0, zf, np.where(zf < z1f, Z0 + (zf - Z0) / SHRINK, zf + (Z1 - Z0) * (1 - SHRINK)))


TL = float(warp_mm(TL0))   # 縮めた後の全長（mm）
