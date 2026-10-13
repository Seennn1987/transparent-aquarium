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
| `Chamaeleo.stl`（リポジトリ外: `画像サンプル収集/エボシカメレオン/`） | 頭骨の 3D 形状をそのまま使う。胴の前半の肋骨の寝る角・断面の幅/深さを、全身 CT の胸郭を戻す参考に測った（2026-10-13） | DigiMorph, *Chamaeleo calyptratus*, Texas Memorial Museum TNHC 62768。スキャン Matthew Colbert（2003-07-11）、画像処理 Jessie Maisano。https://www.digimorph.org/specimens/Chamaeleo_calyptratus/whole/ | 再配布しない。公開・販売の前に利用許可を確認する |
| `Chamaeleo-calyptratus-000050726.zip`（リポジトリ外: `画像サンプル収集/エボシカメレオン/morphosource_media-id-000050726_download-c86f5ae0/`）。JPEG 断面 4287 枚、3059×3791、0.026 mm | 頭以外の全身の骨の形をそのまま使う（2026-10-13〜） | MorphoSource Media 000050726, *Chamaeleo calyptratus calyptratus*, California Academy of Sciences CAS:HERP:135515（oVert）。https://www.morphosource.org/concern/media/000050726 | 権利表示 In Copyright – Non-Commercial Use Permitted。商用利用は不可、3D プリントは制限あり。データとここから作ったメッシュ・骨ラベルは再配布しない（`blender/private/`）。使うときは oVert を引用する。Blackburn et al. 2024, *BioScience* 74:169–186。資金: Christopher V. Anderson / University of South Dakota, NSF DBI-1701665 |

ユーザーが集めた写真（`画像サンプル収集/エボシカメレオン/`、出典なし、一部に販売会社のロゴ）は、形を見比べる参考にだけ使い、リポジトリにも公開物にも入れない。

## 文献（軟骨の場所、2026-10-13）

- Williston, S. W. (1925). *The Osteology of the Reptiles*. Chapter III. Wikisource: https://en.wikisource.org/wiki/The_Osteology_of_the_Reptiles/Chapter_3（パブリックドメイン）
  - トカゲの胸骨は多少石灰化した板で、胸骨の肋骨は軟骨
  - カメレオンには V 字の腹側の肋骨が多く、ふつう軟骨
- Diaz, R. E. Jr. & Trainor, P. A. (2015). Hand/foot splitting and the 're-evolution' of mesopodial skeletal elements during the evolution and radiation of chameleons. *BMC Evolutionary Biology* 15:184. https://pmc.ncbi.nlm.nih.gov/articles/PMC4574539/
  - エボシカメレオンの遠位手根骨 3 は軟骨のまま
- madcham.de（愛好家の解説。論文ではない）: https://www.madcham.de/en/?p=1025
  - ほとんどの肋骨が胸骨か、反対側の肋骨の軟骨につながる

## 文献（体腔・肺・内臓・色素、2026-10-13）

- Klaver, C. J. J. (1977). Comparative lung-morphology in the genus *Chamaeleo* Laurenti, 1768 (Sauria: Chamaeleonidae). *Beaufortia* 25(327):167–199. https://repository.naturalis.nl/pub/505191/BEAU1977025327001.pdf
  - *Chamaeleo* の肺には、腹側縁と尾側縁から盲嚢（diverticula）が出る（p.167）。*C. calyptratus* は 7 本で、うち 2 本は二叉（p.169）
- Klaver, C. J. J. (1973). Lung-anatomy: aid in Chameleon-taxonomy. *Beaufortia* 20(269). https://repository.naturalis.nl/pub/504814/BEAU1973020269001.pdf
- Cassel, N. (2014). The Basics of Reptile Radiology. VIN（獣医向けの講演録）. https://www.vin.com/doc/?id=7054882
  - トカゲの肺は嚢状で、肝臓の背側にあり、体腔の背壁に接する
- Melero, A. et al. (2023). Computed tomography of the coelomic cavity in healthy veiled chameleons (*Chamaeleo calyptratus*) and panther chameleons (*Furcifer pardalis*). *Open Veterinary Journal* 13(9):1071–1081. https://www.openveterinaryjournal.com/?mno=113832
  - 本文（PMC10576585、https://pmc.ncbi.nlm.nih.gov/articles/PMC10576585/）を 2026-10-13 に読んだ。体腔の臓器（`blender/ct_body_pipeline/organs.py`）の配置は Results の各節、大きさは Table 1（肝臓・胆嚢・脂肪体・腎臓・精巣、エボシカメレオン 17 頭、102.0 ± 16.8 g）と Table 3（心臓の長軸 1.67 cm・短軸 0.91 cm、VHS 4.61）。動物は撮影前に 48 時間絶食（消化管は空）。胃・腸・結腸・膀胱の大きさは書かれていない
  - 本文は未読。臓器の位置関係は、この論文で確かめる
- Davis, D. D. & Gore, U. R. (1936). Clearing and Staining Skeletons of Small Vertebrates. Field Museum Technique Series 4. https://www.archive.org/download/clearingstaining04davis/clearingstaining04davis_bw.pdf
  - 消化管に未消化物が多いときは内臓を取り除く。`06` に褐色の塊が見えないことの説明の候補（確かめてはいない）
- Griffing, A. H., Gamble, T. & Bauer, A. M. (2020). *BMC Evolutionary Biology* 20:40. https://link.springer.com/article/10.1186/s12862-020-01604-9
  - 昼行性の小型有鱗類の多くは腹膜に色素が多い。*Chamaeleo* の腹膜が黒いかは、Bauer 1997（*Afr. J. Herpetol.* 46:117–123）の本文を読めておらず未確認

## 文献（舌骨、2026-10-13）

- Wainwright, P. C., Kraklau, D. M. & Bennett, A. F. (1991). Kinematics of tongue projection in *Chamaeleo oustaleti*. *J. Exp. Biol.* 159:109–133. https://cob.silverchair.com/jeb/article-pdf/1470645/109.pdf
  - 正中の大きな舌内突起（entoglossal process）の基部に、骨性の角鰓骨が一対関節する。角舌骨は軟骨で小さく、角鰓骨の前にある。舌骨は喉に吊られている

## 文献（呼吸・心拍、2026-10-13。カメレオンの値は見つからず、近いトカゲの値を仮に使う）

- Milsom, W. K. (1984). The interrelationship between pulmonary mechanics and the spontaneous breathing pattern in the Tokay lizard, *Gekko gecko*. *J. Exp. Biol.* 113:203–214. https://cob.silverchair.com/jeb/article-pdf/113/1/203/2424329/jexbio_113_1_203.pdf
  - 24 °C で約 9 ± 2 回/分（Table 1。PDF の抽出で表が崩れていて、列の対応は推定）。体温が上がると、息を止める時間が短くなって呼吸が増える（要旨）
- Al-Ghamdi, M. S. A. D. (2005). Effect of temperature on the heart and ventilation rates in the agamid lizard *Uromastyx microlipes*. *JKAU: Sci.* 17:21–33. https://admission.kau.edu.sa/Files/320/Researches/52172_22479.pdf
  - 30 °C（加温時）で 40.57 ± 5.68 回/分（Table 1A）。体重 350〜1033 g、n = 7。本文と表に不整合あり
- Brainerd, E. L. & Owerkowicz, T. (2006). Functional morphology and evolution of aspiration breathing in tetrapods. *Respir. Physiol. Neurobiol.* 154:73–88. https://www.brown.edu/Departments/EEB/brainerd_lab/pdf/Brainerd_and_Owerkowicz_2006.pdf
  - 有鱗類では肋間筋が肋骨を頭の側・外へ回す（p.75）
- Melero, A. et al. (2023). *Open Vet. J.* 13(9):1071–1081. https://www.openveterinaryjournal.com/?mno=113832
  - 心臓は体腔のいちばん前、肋骨のかごの中。肝臓は心臓の後ろ・肺の腹側で腹壁に接する。肺は体腔の背側の 2/3 以上
- 鎖骨・間鎖骨の有無: 出典は見つからず（未確認）
