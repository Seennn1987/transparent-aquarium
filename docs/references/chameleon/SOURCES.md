# カメレオン参考画像の出典

制作時の比較用。画面や公開物には貼らない。

透かし入りの 01〜04 は、このフォルダに置くだけで、リポジトリには含めない（`.gitignore`）。

## この計画で正にする写真

| ファイル | 用途 | ライセンス | 出典 |
|---|---|---|---|
| `05-lightbox-calyptratus-1.jpg` | 実物の透明標本。背側に近い角度 | CC BY-SA 4.0 | Brianwray26, Wikimedia Commons, File:Lightbox Chameleon-1.jpg。標本は *Chamaeleo calyptratus*、カタログ 66198、イエメン、1951-01-21。写真の中のラベルは「Field Museum of Natural History, Division of Amphibians and Reptiles」と読める（以前の「スミソニアン」は取り下げ。Commons の記載は未確認） |
| `06-lightbox-calyptratus-2.jpg` | 同じ標本の側面。染まりの数値と、かぶとの輪はこちら | CC BY-SA 4.0 | Brianwray26, Wikimedia Commons, File:Lightbox Chameleon-2.jpg。標本は上と同じ |
| `07-erpetologie-chamaeleon-skeleton.jpg` | 全身の骨のつながり、対生の足、巻いた尾。種は *Chamaeleo chamaeleon* で、かぶとの高さはエボシカメレオンに使わない | パブリックドメイン（PD-old） | Bibron, Duméril, Duméril『Erpétologie générale』（1834–1854）。Wikimedia Commons |
| `08-live-calyptratus-male-lateral.jpg` | 生きている雄の横姿。かぶと、トサカ、足の把握 | CC BY-SA 3.0 | Geoff（英語版 Wikipedia から Commons へ）。File:C Calyptratus male.jpg |
| `09-live-calyptratus-head-casque.jpg` | かぶとと眼塔の寄り | CC BY 4.0 | Σ64, Wikimedia Commons, File:Chamaeleo calyptratus 03.jpg |
| `10-plate-1852-calyptratus.jpg` | 図1が *Chamaeleo calyptratus*。図2は別種（*C. balteatus*）なので比率に使わない | 制限なし（Internet Archive Book Images / Flickr Commons） | Duméril『Description des reptiles nouveaux…』（1852）Pl. XXI。Wikimedia Commons |

## ユーザーが貼った写真（低解像・再配布しない）

添付をコピーした。いずれも 1 辺 447px 前後で、色の数値は仮。

| ファイル | 用途 |
|---|---|
| `01-user-jar-diaphonized.jpg` | 瓶の中の姿勢と、骨の赤・軟骨の青・内臓の褐色。透かしは Kaisei Kakou |
| `02-user-skeleton-blue-light.jpg` | 枝をつかむ骨格。照明が青いので染まりの色には使わない |
| `03-user-mood-only.jpg` | 色の雰囲気の絵。骨の形と比率には使わない |
| `04-user-skeleton-black.jpg` | 黒背景の骨格。透かしは Aflo |

## 採らなかったもの

- Commons の `ChameleonSkeletonNHMLondon.jpg` は、展示ラベルがアガマ科のキノボリトカゲ（*Calotes*）を指している。ファイル名がカメレオンでも使わない
- *Brookesia nana* の解剖図は葉カメレオンで、かぶとの比率が違う
- ヒトの舌骨、リクガメの骨格が同じページにある図版は、カメレオンの部分が小さい

## CT データ（骨の形の正。頭骨 2026-10-12〜、全身 2026-10-13〜）

| ファイル | 用途 | 出典 | 扱い |
|---|---|---|---|
| `Chamaeleo.stl`（リポジトリ外: `画像サンプル収集/エボシカメレオン/`） | 頭骨の 3D 形状をそのまま使う | DigiMorph, *Chamaeleo calyptratus*, Texas Memorial Museum TNHC 62768。スキャン Matthew Colbert（2003-07-11）、画像処理 Jessie Maisano。https://www.digimorph.org/specimens/Chamaeleo_calyptratus/whole/ | 再配布しない。公開・販売の前に利用許可を確認する |
| `Chamaeleo-calyptratus-000050726.zip`（リポジトリ外: `画像サンプル収集/エボシカメレオン/morphosource_media-id-000050726_download-c86f5ae0/`）。JPEG 断面 4287 枚、3059×3791、0.026 mm | 頭以外の全身の骨の形をそのまま使う（2026-10-13〜） | MorphoSource Media 000050726, *Chamaeleo calyptratus calyptratus*, California Academy of Sciences CAS:HERP:135515（oVert）。https://www.morphosource.org/concern/media/000050726 | 権利表示 In Copyright – Non-Commercial Use Permitted。商用利用は不可、3D プリントは制限あり。データとここから作ったメッシュ・骨ラベルは再配布しない（`blender/private/`）。使うときは oVert を引用する。Blackburn et al. 2024, *BioScience* 74:169–186。資金: Christopher V. Anderson / University of South Dakota, NSF DBI-1701665 |

ユーザーが集めた写真（`画像サンプル収集/エボシカメレオン/`、出典なし、一部に販売会社のロゴ）は、形を見比べる参考にだけ使い、リポジトリにも公開物にも入れない。
