import * as THREE from "three";
import { createPostprocessing } from "../../shared/postprocessing.js";

// Product-photo finish: the scene is rendered linear, then one pass adds a shallow depth
// of field focused on the specimen, a soft vignette, dithering, and the display transform.
export const LENS = {
  aperture: { value: 0.9 },       // blur strength: CoC in px per unit of 1/distance difference
  maxBlur: { value: 14 },         // px at 1080p
  focus: { value: 9 },            // distance to the specimen, updated every frame
  vignette: { value: 0.22 },
  grain: { value: 0.012 },
};

const TAPS = { eco: 12, balanced: 28, detail: 48 };

export function createSpecimenPost(camera, quality) {
  const taps = TAPS[quality] ?? TAPS.balanced;
  const post = createPostprocessing(camera, {
    samples: quality === "eco" ? 0 : 4,
    uniforms: {
      aperture: LENS.aperture,
      maxBlur: LENS.maxBlur,
      focus: LENS.focus,
      vignette: LENS.vignette,
      grain: LENS.grain,
      frame: { value: 0 },
    },
    fragmentShader: `
      uniform sampler2D beauty; uniform sampler2D depth; uniform vec2 size; uniform vec2 nearFar;
      uniform float aperture; uniform float maxBlur; uniform float focus; uniform float vignette;
      uniform float grain; uniform float frame;
      varying vec2 vUv;
      float distanceAt(vec2 p) {
        float z = texture2D(depth, p).x;
        return nearFar.x * nearFar.y / (nearFar.y - z * (nearFar.y - nearFar.x));
      }
      // Circle of confusion in pixels; the thin-lens term grows with |1/focus - 1/d|.
      // The first 2 px are the depth of the jar itself: the whole jar stays sharp.
      float coc(float d) {
        float scale = size.y / 1080.;
        float blur = abs(1. / focus - 1. / d) * aperture * focus * focus * 2.2 - 2.;
        return clamp(blur, 0., maxBlur) * scale;
      }
      float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + frame * 0.618) * 43758.5453); }
      void main() {
        float d0 = distanceAt(vUv);
        float c0 = coc(d0);
        vec3 sum = texture2D(beauty, vUv).rgb;
        float weight = 1.;
        if (c0 > 0.5) {
          for (int i = 1; i <= ${taps}; i++) {
            float f = float(i) / float(${taps});
            float a = float(i) * 2.399963;
            vec2 offset = vec2(cos(a), sin(a)) * sqrt(f) * c0 / size;
            vec2 p = vUv + offset;
            float ds = distanceAt(p);
            // A sharp nearer sample (the jar) must not bleed into the blurred background.
            float w = ds < d0 - 0.05 ? smoothstep(0., 1., coc(ds) / max(c0, 1e-3)) : 1.;
            sum += texture2D(beauty, p).rgb * w;
            weight += w;
          }
        }
        vec3 color = sum / weight;
        vec2 v = (vUv - .5) * vec2(size.x / size.y, 1.);
        color *= 1. - vignette * smoothstep(.25, 1.1, dot(v, v) * 1.6);
        gl_FragColor = vec4(color, 1.);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        gl_FragColor.rgb += (hash(gl_FragCoord.xy) - .5) * grain;
      }`,
  });
  post.post.toneMapped = true;
  return post;
}
