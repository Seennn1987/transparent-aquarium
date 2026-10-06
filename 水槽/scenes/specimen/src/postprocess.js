import * as THREE from "three";
import { createPostprocessing } from "../../shared/postprocessing.js";

// Product-photo finish: the scene is rendered linear, then one pass adds a shallow depth
// of field focused on the specimen, the lens's colour fringes, the room's warm cast, a soft
// vignette, grain, and the display transform.
export const LENS = {
  // blur strength: CoC in px per unit of 1/distance difference. The front jar stays sharp,
  // the first row behind it goes soft, the far rows and the wall melt.
  aperture: { value: 4 },
  maxBlur: { value: 40 },         // px at 1080p
  focus: { value: 9 },            // distance to the specimen, updated every frame
  focusShift: { value: 0 },       // added to that distance: + focuses behind the specimen
  // Depth either side of the focus that stays sharp: the front jar, lid and knob included.
  focusDepth: { value: 0.9 },
  // Bright points (the lit blocks, highlights on the glass) weigh more in the blur, so they
  // spread into round discs as they do through a real lens.
  bokeh: { value: 1 },
  vignette: { value: 0.6 },
  grain: { value: 0.018 },
  // The gallery's lamps lean warm.
  tint: { value: 0.5 },
  aberration: { value: 1 },       // colour fringes at the frame's edge, in px at 1080p
};

const WARM = new THREE.Vector3(1.03, 0.99, 0.94);

const TAPS = { eco: 20, balanced: 48, detail: 80 };
// Brightest a blurred sample may be: a pinpoint highlight met by one tap in a wide blur would
// otherwise flicker as a lone speck.
const SAMPLE_CEILING = 4;

// The wide blur samples a mipmapped copy of the image, each tap from the level whose texels
// are about as far apart as the taps: the gaps between taps are filled, and a small bright
// edge becomes a smooth disc instead of a sprinkle of dots.
function createMipCopy(source) {
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.HalfFloatType,
    generateMipmaps: true,
    minFilter: THREE.LinearMipmapLinearFilter,
    depthBuffer: false,
  });
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(
    new THREE.PlaneGeometry(2, 2),
    new THREE.ShaderMaterial({
      uniforms: { source: { value: source } },
      depthTest: false,
      depthWrite: false,
      vertexShader: `varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}`,
      fragmentShader: `uniform sampler2D source; varying vec2 vUv;
        void main() { gl_FragColor = vec4(min(texture2D(source, vUv).rgb, vec3(${SAMPLE_CEILING.toFixed(1)})), 1.); }`,
    }),
  ));
  return { target, scene };
}

export function createSpecimenPost(camera, quality) {
  const taps = TAPS[quality] ?? TAPS.balanced;
  const post = createPostprocessing(camera, {
    samples: quality === "eco" ? 0 : 4,
    uniforms: {
      beautyMip: { value: null },
      aperture: LENS.aperture,
      maxBlur: LENS.maxBlur,
      focus: LENS.focus,
      focusDepth: LENS.focusDepth,
      bokeh: LENS.bokeh,
      vignette: LENS.vignette,
      grain: LENS.grain,
      tint: LENS.tint,
      aberration: LENS.aberration,
      warm: { value: WARM },
      frame: { value: 0 },
    },
    fragmentShader: `
      uniform sampler2D beauty; uniform sampler2D beautyMip; uniform sampler2D depth; uniform vec2 size; uniform vec2 nearFar;
      uniform float aperture; uniform float maxBlur; uniform float focus; uniform float focusDepth; uniform float bokeh; uniform float vignette;
      uniform float grain; uniform float frame; uniform float tint; uniform float aberration; uniform vec3 warm;
      varying vec2 vUv;
      float distanceAt(vec2 p) {
        float z = texture2D(depth, p).x;
        return nearFar.x * nearFar.y / (nearFar.y - z * (nearFar.y - nearFar.x));
      }
      // Circle of confusion in pixels; the thin-lens term grows with |1/focus - 1/d|, less
      // the band that the front jar's own depth spans, so the whole jar stays sharp.
      float coc(float d) {
        float scale = size.y / 1080.;
        float band = 1. / max(focus - focusDepth, .1) - 1. / focus;
        float blur = max(abs(1. / focus - 1. / d) - band, 0.) * aperture * focus * focus * 2.2;
        return min(blur, maxBlur) * scale;
      }
      float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + frame * 0.618) * 43758.5453); }
      float still(vec2 p) { return fract(sin(dot(p, vec2(41.23, 17.71))) * 24634.6345); }
      float shine(vec3 c) { return 1. + bokeh * 1.5 * smoothstep(1., 4., dot(c, vec3(.3, .59, .11))); }
      void main() {
        float d0 = distanceAt(vUv);
        float c0 = coc(d0);
        vec3 here = texture2D(beauty, vUv).rgb;
        vec3 centre = c0 > 0.5 ? min(here, vec3(${SAMPLE_CEILING.toFixed(1)})) : here;
        float weight = shine(centre);
        vec3 sum = centre * weight;
        if (c0 > 0.5) {
          // The spiral is turned per pixel (fixed in time) so its pattern does not show.
          float turn = still(gl_FragCoord.xy) * 6.2832;
          float lod = max(log2(c0 * ${Math.sqrt(Math.PI / taps).toFixed(4)}) - .5, 0.);
          for (int i = 1; i <= ${taps}; i++) {
            float f = float(i) / float(${taps});
            float a = float(i) * 2.399963 + turn;
            vec2 offset = vec2(cos(a), sin(a)) * sqrt(f) * c0 / size;
            vec2 p = vUv + offset;
            float ds = distanceAt(p);
            vec3 s = textureLod(beautyMip, p, lod).rgb;
            // A nearer sample reaches this pixel only as far as its own blur spreads it: the
            // sharp front jar keeps its edge, a softer jar behind it spills over the wall.
            float reach = sqrt(f) * c0;
            float w = ds < d0 - 0.05 ? smoothstep(reach - 1., reach + 1., coc(ds)) : 1.;
            w *= shine(s);
            sum += s * w;
            weight += w;
          }
        }
        vec3 color = sum / weight;
        // Red lands a little outward of green and blue a little inward, more toward the corners.
        vec2 fringe = (vUv - .5) * 2. * aberration * size.y / 1080. / size;
        color.r += texture2D(beauty, vUv + fringe).r - here.r;
        color.b += texture2D(beauty, vUv - fringe).b - here.b;
        color *= mix(vec3(1.), warm, tint);
        vec2 v = (vUv - .5) * vec2(size.x / size.y, 1.);
        color *= 1. - vignette * smoothstep(.25, 1.1, dot(v, v) * 1.6);
        gl_FragColor = vec4(color, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        gl_FragColor.rgb += (hash(gl_FragCoord.xy) - .5) * grain;
      }`,
  });
  post.post.toneMapped = true;
  const copy = createMipCopy(post.target.texture);
  post.post.uniforms.beautyMip.value = copy.target.texture;
  return {
    ...post,
    mip: copy.target,
    /** Fills the mipmapped copy from the rendered image; call before drawing postScene. */
    prepare(renderer) {
      renderer.setRenderTarget(copy.target);
      renderer.render(copy.scene, post.postCamera);
    },
    setSize(width, height) {
      post.target.setSize(width, height);
      copy.target.setSize(width, height);
      post.post.uniforms.size.value.set(width, height);
    },
    dispose() {
      post.target.dispose();
      post.post.dispose();
      copy.target.dispose();
      copy.scene.children[0].material.dispose();
    },
  };
}
