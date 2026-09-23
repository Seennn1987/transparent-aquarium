import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

import { createTank, createLighting } from './scene/tank.js';
import { createPlaceholderFish } from './fish/createFish.js';

const container = document.getElementById('app');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x030507);

const camera = new THREE.PerspectiveCamera(
  45,
  window.innerWidth / window.innerHeight,
  0.01,
  10
);
camera.position.set(0.5, 0.25, 0.6);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enableDamping = true;

// --- 水槽・照明 ---
const { group: tankGroup, bounds } = createTank();
scene.add(tankGroup);
scene.add(createLighting());

// --- 魚(プレースホルダー): Blender製.glbが用意でき次第、ここをGLTFLoaderに差し替える ---
const fish = createPlaceholderFish({ standardLength: bounds.width * 0.35 });
fish.object3D.position.set(-bounds.width * 0.15, 0, 0);
scene.add(fish.object3D);

// --- ポストプロセス: 骨格の発光をにじませるBloom ---
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.9, // strength
  0.6, // radius
  0.15 // threshold
);
composer.addPass(bloomPass);
composer.addPass(new OutputPass());

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  composer.setSize(window.innerWidth, window.innerHeight);
});

const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  fish.update(t);
  // ゆっくり水槽内を左右に回遊させる簡易パス（本実装ではステアリング行動に発展させる）
  fish.object3D.position.x = Math.sin(t * 0.2) * bounds.width * 0.25;
  fish.object3D.rotation.y = Math.PI / 2 + Math.cos(t * 0.2) * 0.15;

  controls.update();
  composer.render();
}
animate();
