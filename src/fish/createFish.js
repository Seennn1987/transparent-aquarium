import * as THREE from 'three';

/**
 * Blenderで作った透明標本モデル(.glb)が届くまでの「動作確認用プレースホルダー魚」。
 * Gerres erythrourus の体型比率（体高がSLの約1/2、側扁）をおおまかに反映した
 * 簡易ジオメトリに、背骨に沿ったボーンチェーンを仕込んでSkinnedMeshにしている。
 *
 * 実アセット（Blender製 .glb）に差し替える際は、
 * main.js側で createPlaceholderFish() の呼び出しを
 * GLTFLoaderでの読み込み + AnimationMixer に置き換えるだけで良いように、
 * 戻り値のインターフェース { object3D, update(time) } を揃えてある。
 */

const SEGMENTS_ALONG_BODY = 24; // 長さ方向の分割数（多いほど滑らかに曲がる）
const RADIAL_SEGMENTS = 10;
const BONE_COUNT = 7; // 頭から尾まで7本のボーンチェーン

export function createPlaceholderFish({
  standardLength = 0.22, // 標準体長[m]。まずは小型個体を想定
  bodyDepthRatio = 1 / 2.1, // 体高 = SL * bodyDepthRatio（FishBase記載の 1/1.9〜1/2.3 の中間値）
  color = 0xff33cc, // 骨格の発光色（アリザリンレッド染色を意識したマゼンタ系）
} = {}) {
  const length = standardLength;
  const maxDepth = length * bodyDepthRatio;

  // --- ジオメトリ: 円柱を土台にして、深い(縦長)・薄い(側扁)体型にゆがめる ---
  const geometry = new THREE.CylinderGeometry(
    maxDepth * 0.5,
    maxDepth * 0.5,
    length,
    RADIAL_SEGMENTS,
    SEGMENTS_ALONG_BODY,
    true
  );
  geometry.rotateZ(Math.PI / 2); // 円柱の軸をZ(前後方向)に向ける
  geometry.translate(length / 2, 0, 0); // 原点を頭側の先端に合わせる

  const posAttr = geometry.attributes.position;
  const v = new THREE.Vector3();
  for (let i = 0; i < posAttr.count; i++) {
    v.fromBufferAttribute(posAttr, i);
    const t = THREE.MathUtils.clamp(v.x / length, 0, 1); // 0=頭 1=尾

    // 体高のプロファイル: 頭部から体高最大点(体長の約35%位置)までなだらかに増加し、
    // そこから尾柄にかけて細くなる紡錘形（クロサギ科の「体が深く側扁」を簡易的に表現）
    const depthProfile = Math.sin(Math.PI * Math.pow(t, 0.6)) * (1 - 0.15 * t);
    v.y *= depthProfile;

    // 側扁（体の厚みは薄い）: 厚み方向(z軸=元の円柱のY)を体高の35%程度に圧縮
    v.z *= 0.35 * depthProfile + 0.05;

    posAttr.setXYZ(i, v.x, v.y, v.z);
  }
  geometry.computeVertexNormals();

  // --- ボーン(スケルトン)の作成: 頭から尾まで直線状に配置 ---
  const bones = [];
  let prevBone = null;
  for (let i = 0; i < BONE_COUNT; i++) {
    const bone = new THREE.Bone();
    const segLength = length / (BONE_COUNT - 1);
    bone.position.x = i === 0 ? 0 : segLength;
    if (prevBone) prevBone.add(bone);
    bones.push(bone);
    prevBone = bone;
  }
  const rootBone = bones[0];

  // --- スキンウェイト: 各頂点を、体長方向の位置に応じて隣接する2ボーンに按分 ---
  const skinIndices = [];
  const skinWeights = [];
  for (let i = 0; i < posAttr.count; i++) {
    const x = posAttr.getX(i);
    const t = THREE.MathUtils.clamp(x / length, 0, 0.9999);
    const boneSpace = t * (BONE_COUNT - 1);
    const boneIndex = Math.floor(boneSpace);
    const frac = boneSpace - boneIndex;
    skinIndices.push(boneIndex, Math.min(boneIndex + 1, BONE_COUNT - 1), 0, 0);
    skinWeights.push(1 - frac, frac, 0, 0);
  }
  geometry.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(skinIndices, 4));
  geometry.setAttribute('skinWeight', new THREE.Float32BufferAttribute(skinWeights, 4));

  // --- マテリアル: 透明標本の「外皮=透過」「今回はプレースホルダーなので薄く色付け」---
  const bodyMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xbfe9ff,
    transmission: 0.9,
    thickness: 0.02,
    roughness: 0.08,
    ior: 1.35,
    transparent: true,
    opacity: 0.35,
    side: THREE.DoubleSide,
  });

  const mesh = new THREE.SkinnedMesh(geometry, bodyMaterial);
  const skeleton = new THREE.Skeleton(bones);
  mesh.add(rootBone);
  mesh.bind(skeleton);
  mesh.frustumCulled = false;

  // --- 骨格の可視化用ライン（本番ではBlender製の発光骨格メッシュに置き換える）---
  const skeletonHelperGeom = new THREE.BufferGeometry().setFromPoints(
    bones.map((b) => new THREE.Vector3())
  );
  const skeletonLine = new THREE.Line(
    skeletonHelperGeom,
    new THREE.LineBasicMaterial({ color, linewidth: 2 })
  );

  const group = new THREE.Group();
  group.add(mesh);
  group.add(skeletonLine);

  // --- 遊泳アニメーション: 尾に向かうほど振幅が大きくなる正弦波でうねらせる ---
  function update(time, swimSpeed = 1.6) {
    for (let i = 1; i < bones.length; i++) {
      const t = i / (bones.length - 1);
      const amplitude = THREE.MathUtils.lerp(0.05, 0.55, t); // 頭側は小さく、尾側は大きく
      const phase = t * 3.2; // 波が体を伝わっていくように位置でずらす
      bones[i].rotation.y = amplitude * Math.sin(time * swimSpeed - phase);
    }

    // 骨格ラインの頂点をボーンのワールド座標に追従させる
    const positions = skeletonLine.geometry.attributes.position;
    const worldPos = new THREE.Vector3();
    bones.forEach((b, i) => {
      b.getWorldPosition(worldPos);
      const local = group.worldToLocal(worldPos.clone());
      positions.setXYZ(i, local.x, local.y, local.z);
    });
    positions.needsUpdate = true;
  }

  return { object3D: group, update, bones };
}
