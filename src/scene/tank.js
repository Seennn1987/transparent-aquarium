import * as THREE from 'three';

/**
 * 簡易な水槽ジオメトリ。ガラス面(BackSideのボックス)+底面+環境光を用意する。
 * 本格的な水面表現(屈折・波)は後段で差し替える前提の最小構成。
 */
export function createTank({ width = 0.6, height = 0.4, depth = 0.35 } = {}) {
  const group = new THREE.Group();

  const glassMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xaee6ff,
    transmission: 0.95,
    roughness: 0.05,
    thickness: 0.01,
    ior: 1.45,
    transparent: true,
    opacity: 0.15,
    side: THREE.BackSide,
  });
  const glassBox = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), glassMaterial);
  group.add(glassBox);

  const floorMaterial = new THREE.MeshStandardMaterial({ color: 0x142027, roughness: 0.9 });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(width, depth), floorMaterial);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -height / 2 + 0.001;
  group.add(floor);

  return { group, bounds: { width, height, depth } };
}

export function createLighting() {
  const group = new THREE.Group();

  const key = new THREE.DirectionalLight(0xffffff, 1.2);
  key.position.set(0.5, 1.0, 0.6);
  group.add(key);

  const fill = new THREE.DirectionalLight(0x88ccff, 0.4);
  fill.position.set(-0.6, 0.3, -0.4);
  group.add(fill);

  const ambient = new THREE.AmbientLight(0xffffff, 0.35);
  group.add(ambient);

  return group;
}
