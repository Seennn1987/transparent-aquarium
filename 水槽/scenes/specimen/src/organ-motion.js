import { randomGenerator } from "../../shared/random.js";

// The cleared specimen's organs keep moving as they did in life, which a real specimen never
// could. Rates are those of a resting loliginid squid:
//   breathing   the mantle's ventilation, taken from SQ_Hover so the organs keep time with
//               the bones (animate_squid.py: sin(2π · 0.75 Hz · t)); the funnel opens as it exhales
//   hearts      about 50 beats a minute; the two branchial hearts squeeze first, the systemic
//               heart a moment later. A beat contracts fast and relaxes slowly
//   gut         every few seconds a peristaltic swelling runs from the mouth down the oesophagus
//               and on through the caecum
//   eyes        the pupil opens and narrows over seconds, the lens shifts to focus, and every few
//               seconds each eye flicks to a new direction and holds (saccades)
//   mouth       bursts of bites, the radula rasping behind the beak
//   ink sac     now and then a squeeze
//   chromatophores  each remnant dot expands and shrinks in a fraction of a second, in clouds
//               that pass along the body
export const ORGAN_RATES = Object.freeze({
  breathHz: 0.75,
  heartHz: 50 / 60,
  systemicLag: 0.12,        // of a beat, after the branchial hearts
  gutEvery: 5.5,            // s between peristaltic waves
  gutFrom: -0.25,           // where a wave starts and ends along the body (model x)
  gutTo: 0.95,
  saccadeEvery: [2, 6],     // s
  saccadeDegrees: 4,
  biteEvery: [7, 15],       // s between bursts
  bitesPerBurst: [3, 5],
  biteHz: 1.2,
  inkEvery: [20, 40],       // s between squeezes
  inkSeconds: 1.4,
});

// Strength of each kind of motion (0 stops it), and the speed of all of them.
export const organLook = {
  speed: { value: 1 },
  heart: { value: 1 },
  gut: { value: 1 },
  eye: { value: 1 },
  mouth: { value: 1 },
  funnel: { value: 1 },
  chromatophores: { value: 1 },
};

const DEG = Math.PI / 180;

/** Contraction of a beat, 0 at rest and 1 fully squeezed; `phase` in beats. */
export function heartbeat(phase) {
  const f = phase - Math.floor(phase);
  if (f < 0.12) return smooth(f / 0.12);
  return 1 - smooth(Math.min(1, (f - 0.12) / 0.43));
}

/** The mantle's breathing, as SQ_Hover plays it: positive while it fills, negative as it empties. */
export function breathAt(hoverTime) {
  return Math.sin(2 * Math.PI * ORGAN_RATES.breathHz * hoverTime);
}

function smooth(x) {
  return x * x * (3 - 2 * x);
}

export function createOrganMotion({ seed = 5021 } = {}) {
  const random = randomGenerator(seed);
  const between = ([a, b]) => a + (b - a) * random();
  const uniforms = {
    uOrganTime: { value: 0 },
    uBreath: { value: 0 },
    uBeatBranchial: { value: 0 },
    uBeatSystemic: { value: 0 },
    uGland: { value: 0 },
    uGutWave: { value: -1 },
    uGut: { value: 0 },
    uPupil: { value: 0 },
    uLens: { value: 0 },
    uEyeTurn: { value: [0, 0, 0, 0] },  // left yaw, pitch, right yaw, pitch (radians)
    uBite: { value: 0 },
    uRadula: { value: 0 },
    uBuccal: { value: 0 },
    uInk: { value: 0 },
    uFunnelOpen: { value: 0 },
    uFunnelSwivel: { value: 0 },
    uChromo: organLook.chromatophores,
  };
  const state = { time: 0 };
  const gaze = [0, 0, 0, 0];
  const gazeTarget = [0, 0, 0, 0];
  const nextSaccade = [between(ORGAN_RATES.saccadeEvery), between(ORGAN_RATES.saccadeEvery)];
  let nextBurst = between(ORGAN_RATES.biteEvery) * 0.5;
  let burstLeft = 0;
  let nextInk = between(ORGAN_RATES.inkEvery) * 0.5;
  let inkAt = -Infinity;

  function update(dt, hoverTime) {
    const step = Math.min(0.1, Math.max(0, dt)) * organLook.speed.value;
    const u = uniforms;
    u.uBreath.value = breathAt(hoverTime);
    if (step === 0) return u;
    state.time += step;
    const t = state.time;
    u.uOrganTime.value = t;

    const beat = t * ORGAN_RATES.heartHz;
    u.uBeatBranchial.value = heartbeat(beat) * organLook.heart.value;
    u.uBeatSystemic.value = heartbeat(beat - ORGAN_RATES.systemicLag) * organLook.heart.value;

    const gut = organLook.gut.value;
    u.uGutWave.value = ORGAN_RATES.gutFrom + (ORGAN_RATES.gutTo - ORGAN_RATES.gutFrom) * ((t / ORGAN_RATES.gutEvery) % 1);
    u.uGut.value = gut;
    u.uGland.value = (0.5 + 0.5 * Math.sin(t * 2 * Math.PI / 11)) * gut;

    const eye = organLook.eye.value;
    u.uPupil.value = (0.7 * Math.sin(t * 0.37) + 0.3 * Math.sin(t * 0.91 + 1.3)) * eye;
    u.uLens.value = Math.sin(t * 0.23 + 1) * eye;
    for (let side = 0; side < 2; side++) {
      nextSaccade[side] -= step;
      if (nextSaccade[side] <= 0) {
        gazeTarget[side * 2] = (random() * 2 - 1) * ORGAN_RATES.saccadeDegrees * DEG;
        gazeTarget[side * 2 + 1] = (random() * 2 - 1) * ORGAN_RATES.saccadeDegrees * 0.5 * DEG;
        nextSaccade[side] = between(ORGAN_RATES.saccadeEvery);
      }
    }
    // A saccade is over in a tenth of a second.
    const snap = 1 - Math.exp(-step / 0.03);
    for (let i = 0; i < 4; i++) {
      gaze[i] += (gazeTarget[i] - gaze[i]) * snap;
      u.uEyeTurn.value[i] = gaze[i] * eye;
    }

    nextBurst -= step;
    if (nextBurst <= 0 && burstLeft <= 0) {
      burstLeft = Math.round(between(ORGAN_RATES.bitesPerBurst)) / ORGAN_RATES.biteHz;
      nextBurst = between(ORGAN_RATES.biteEvery);
    }
    let bite = 0;
    if (burstLeft > 0) {
      burstLeft -= step;
      bite = 0.5 - 0.5 * Math.cos(2 * Math.PI * ORGAN_RATES.biteHz * burstLeft);
    }
    const mouth = organLook.mouth.value;
    u.uBite.value = bite * mouth;
    u.uRadula.value = (burstLeft > 0 ? Math.sin(2 * Math.PI * ORGAN_RATES.biteHz * burstLeft - 1.2) : 0) * mouth;
    u.uBuccal.value = bite * 0.6 * mouth;

    nextInk -= step;
    if (nextInk <= 0) {
      inkAt = t;
      nextInk = between(ORGAN_RATES.inkEvery);
    }
    const since = (t - inkAt) / ORGAN_RATES.inkSeconds;
    u.uInk.value = (since >= 0 && since < 1 ? Math.sin(Math.PI * since) ** 2 : 0) * gut;

    const funnel = organLook.funnel.value;
    u.uFunnelOpen.value = Math.max(0, -u.uBreath.value) * funnel;
    u.uFunnelSwivel.value = (0.7 * Math.sin(t * 0.21) + 0.3 * Math.sin(t * 0.53 + 2)) * funnel;
    return u;
  }

  return { uniforms, state, update };
}
