// dsnsim viewer core: globe, complexes, time engine, links.
// Frame: geocentric J2000 equatorial (ECI). three.js axes: x = ECI x, y = ECI z (north), z = -ECI y.
// Distances use a log radial scale; directions from Earth's centre are true.
import * as THREE from 'three';
import { OrbitControls } from '../vendor/OrbitControls.js';
import { Line2 } from '../vendor/lines/Line2.js';
import { LineGeometry } from '../vendor/lines/LineGeometry.js';
import { LineMaterial } from '../vendor/lines/LineMaterial.js';

const RE_KM = 6378.137;
const LOG_K = 0.85;            // display units per decade of distance
const BACK_S = 86400, FWD_S = 7 * 86400;
const CURVE_N = 32;            // segments per link
const LINK_LIFT = 0.3;         // links leave the antenna vertically, then bend to the target
const OBLIQUITY = 23.4393 * Math.PI / 180;
const COLORS = { track: 0x4fd8ff, uplink: 0xffb347, setup: 0x7aa2ff, busy: 0xf0a030, idle: 0x4a566b };
const REGION_COLORS = { heo: 0x9be7ff, l1l2: 0xb8f5c5, lunar: 0xdddddd, mars: 0xff9a76, helio: 0xffe08a, outer: 0xd0b3ff };
const RINGS = [
  [42164, 'GEO'], [384400, 'Moon'], [1.5e6, 'L1 / L2'], [1.496e8, '1 AU'], [1.496e9, '10 AU'], [1.496e10, '100 AU'],
];
const COMPLEX_LABEL = { GDSCC: 'GOLDSTONE', CDSCC: 'CANBERRA', MDSCC: 'MADRID' };

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);

// ---------------------------------------------------------------- math helpers
const eciToThree = (p, out = new THREE.Vector3()) => out.set(p[0], p[2], -p[1]);
function scaleKm(v) {           // km vector (three axes) -> display units, log radial
  const r = v.length();
  if (r < 1) return v.set(0, 0, 0);
  return v.multiplyScalar((1 + LOG_K * Math.log10(Math.max(r / RE_KM, 1))) / r);
}
const scaleDist = (km) => 1 + LOG_K * Math.log10(km / RE_KM);
function gmst(t) {              // radians, t = unix seconds
  const d = t / 86400 + 2440587.5 - 2451545.0;
  return THREE.MathUtils.degToRad(((280.46061837 + 360.98564736629 * d) % 360 + 360) % 360);
}
function latLonToUnit(latDeg, lonDeg) {   // Earth-fixed unit vector in three axes
  const lat = THREE.MathUtils.degToRad(latDeg), lon = THREE.MathUtils.degToRad(lonDeg);
  return new THREE.Vector3(Math.cos(lat) * Math.cos(lon), Math.sin(lat), -Math.cos(lat) * Math.sin(lon));
}
function interp(track, t, out) {
  const u = (t - track.t0) / track.step, n = track.pos.length;
  if (u < 0 || u > n - 1) return null;
  const i = Math.min(Math.floor(u), n - 2), f = u - i, a = track.pos[i], b = track.pos[i + 1];
  return out.set(a[0] + f * (b[0] - a[0]), a[2] + f * (b[2] - a[2]), -(a[1] + f * (b[1] - a[1])));
}
const pad = (n) => String(n).padStart(2, '0');
function fmtDate(t) { const d = new Date(t * 1000); return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`; }
function fmtTime(t) { const d = new Date(t * 1000); return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`; }
function fmtDoy(t) {
  const d = new Date(t * 1000);
  const doy = Math.floor((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - Date.UTC(d.getUTCFullYear(), 0, 0)) / 864e5);
  return `DOY ${String(doy).padStart(3, '0')}`;
}

// ---------------------------------------------------------------- scene
const canvas = $('scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 2000);
camera.position.set(9, 6.5, 11);
const controls = new OrbitControls(camera, canvas);
controls.enablePan = false;
controls.enableDamping = true;
controls.minDistance = 1.5;
controls.maxDistance = 40;
const resolution = new THREE.Vector2(1, 1);

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  resolution.set(w, h);
}
addEventListener('resize', resize);
resize();

// Stars
{
  const n = 2500, pos = new Float32Array(n * 3), v = new THREE.Vector3();
  for (let i = 0; i < n; i++) { v.randomDirection().multiplyScalar(900); v.toArray(pos, i * 3); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x8fa3c7, size: 1.4, sizeAttenuation: false, transparent: true, opacity: 0.7 })));
}

// Earth with day/night shading
const sunDir = new THREE.Vector3(1, 0, 0);
const texLoader = new THREE.TextureLoader();
const loadTex = (url) => { const t = texLoader.load(url); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t; };
const earthMat = new THREE.ShaderMaterial({
  uniforms: { dayTex: { value: loadTex('img/earth-blue-marble.jpg') }, nightTex: { value: loadTex('img/earth-night.jpg') }, sunDir: { value: sunDir } },
  vertexShader: `
    varying vec2 vUv; varying vec3 vN; varying vec3 vP;
    void main() { vUv = uv; vN = normalize(mat3(modelMatrix) * normal); vec4 wp = modelMatrix * vec4(position, 1.0); vP = wp.xyz;
      gl_Position = projectionMatrix * viewMatrix * wp; }`,
  fragmentShader: `
    uniform sampler2D dayTex; uniform sampler2D nightTex; uniform vec3 sunDir;
    varying vec2 vUv; varying vec3 vN; varying vec3 vP;
    void main() {
      float d = dot(normalize(vN), sunDir);
      float day = smoothstep(-0.12, 0.22, d);
      vec3 dc = texture2D(dayTex, vUv).rgb * (0.25 + 0.95 * max(d, 0.0));
      vec3 nc = texture2D(nightTex, vUv).rgb * 1.3 + texture2D(dayTex, vUv).rgb * 0.11;
      vec3 c = mix(nc, dc, day);
      float rim = pow(1.0 - max(dot(normalize(cameraPosition - vP), normalize(vN)), 0.0), 3.0);
      c += vec3(0.25, 0.5, 1.0) * rim * (0.15 + 0.5 * day);
      gl_FragColor = vec4(c, 1.0);
      #include <colorspace_fragment>
    }`,
});
const earth = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 64), earthMat);
scene.add(earth);
scene.add(new THREE.Mesh(
  new THREE.SphereGeometry(1.045, 64, 48),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    uniforms: { sunDir: { value: sunDir } },
    vertexShader: `varying vec3 vN; varying vec3 vP; void main(){ vN = normalize(mat3(modelMatrix)*normal); vec4 wp = modelMatrix*vec4(position,1.0); vP = wp.xyz; gl_Position = projectionMatrix*viewMatrix*wp; }`,
    fragmentShader: `uniform vec3 sunDir; varying vec3 vN; varying vec3 vP;
      void main(){ float f = pow(max(dot(normalize(vP - cameraPosition), normalize(vN)), 0.0), 2.5);
        float lit = 0.25 + 0.75 * smoothstep(-0.3, 0.4, dot(normalize(vN), sunDir));
        gl_FragColor = vec4(vec3(0.3, 0.6, 1.0) * f * lit * 0.9, 1.0); }`,
  }),
));

// Distance rings in the ecliptic plane
const labelLayer = $('labels');
function makeLabel(cls, text) {
  const el = document.createElement('div');
  el.className = `lbl ${cls}`;
  el.textContent = text;
  el.style.display = 'none';
  labelLayer.appendChild(el);
  return el;
}
const ringLabels = [];
{
  const e1 = new THREE.Vector3(1, 0, 0), e2 = eciToThree([0, Math.cos(OBLIQUITY), Math.sin(OBLIQUITY)]);
  const mat = new THREE.LineBasicMaterial({ color: 0x6f8fc8, transparent: true, opacity: 0.22, depthWrite: false });
  RINGS.forEach(([km, name], k) => {
    const r = scaleDist(km), pts = [];
    for (let i = 0; i <= 180; i++) {
      const a = i / 180 * Math.PI * 2;
      pts.push(e1.clone().multiplyScalar(r * Math.cos(a)).addScaledVector(e2, r * Math.sin(a)));
    }
    scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat));
    const a = -0.9 + k * 0.12;
    ringLabels.push({ el: makeLabel('ring', name), pos: e1.clone().multiplyScalar(r * Math.cos(a)).addScaledVector(e2, r * Math.sin(a)) });
  });
}

// ---------------------------------------------------------------- data
let schedule = null, ephem = null;
let tMin = 0, tMax = 0, generated = 0;
const antennas = new Map();       // dss -> {cfg, marker, label, acts[]}
const complexes = new Map();      // key -> {unit, label, antennas[]}
const craft = new Map();          // key -> {mesh, name, pos, visible, active}
const bodies = new Map();
const links = new Map();          // activity id -> link objects
const dotGeo = new THREE.SphereGeometry(1, 16, 12);

function trackFor(key) {
  let o = ephem.objects[key];
  if (o && o.alias) o = ephem.objects[o.alias];
  return o && o.pos ? o : null;
}

function buildAntennas() {
  if (antennas.size) return;
  const byComplex = {};
  for (const [dss, cfg] of Object.entries(schedule.antennas)) (byComplex[cfg.complex] ??= []).push([+dss, cfg]);
  for (const [key, list] of Object.entries(byComplex)) {
    const c = schedule.complexes[key];
    const unit = latLonToUnit(c.lat, c.lon);
    complexes.set(key, { unit, label: makeLabel('cx', COMPLEX_LABEL[key] || key), antennas: [] });
    // The antennas of a complex are a few km apart; fan them out along an
    // east-west row (70 m first) so each is visible at globe scale.
    list.sort((a, b) => b[1].size_m - a[1].size_m || a[0] - b[0]);
    list.forEach(([dss, cfg], i) => {
      const unitA = latLonToUnit(c.lat, c.lon + (i - (list.length - 1) / 2) * 2.4);
      const marker = new THREE.Mesh(dotGeo, new THREE.MeshBasicMaterial({ color: COLORS.idle }));
      marker.scale.setScalar(cfg.size_m >= 70 ? 0.017 : 0.012);
      marker.position.copy(unitA).multiplyScalar(1.004);
      earth.add(marker);
      const a = { dss, cfg, complex: key, marker, labelDy: i % 2 ? -19 : 7, label: makeLabel('ant', String(dss)), acts: [], world: new THREE.Vector3(), state: 'idle' };
      antennas.set(dss, a);
      complexes.get(key).antennas.push(a);
    });
  }
}

function indexData() {
  generated = Date.parse(schedule.generated) / 1000;
  tMin = generated - BACK_S; tMax = generated + FWD_S;
  buildAntennas();
  for (const a of antennas.values()) a.acts = [];
  for (const act of schedule.activities) {
    const a = antennas.get(act.dss);
    if (!a) continue;
    act.t = [act.start, act.bot, act.eot, act.end].map((s) => Date.parse(s) / 1000);
    act.up = (act.uplink || []).map(([s, e]) => [Date.parse(s) / 1000, Date.parse(e) / 1000]);
    act.hasTraj = act.kind === 'track' && !!trackFor(act.user);
    a.acts.push(act);
    if (act.hasTraj && !craft.has(act.user)) {
      const m = ephem.missions[act.user] || { name: act.user, region: 'helio' };
      const mesh = new THREE.Mesh(dotGeo, new THREE.MeshBasicMaterial({ color: REGION_COLORS[m.region] || 0xffffff }));
      mesh.scale.setScalar(0.022);
      scene.add(mesh);
      craft.set(act.user, { key: act.user, name: m.name, mesh, pos: mesh.position, visible: false, active: false });
    }
  }
  const bodyStyle = { moon: [0.06, 0x9a9a9a], mars: [0.075, 0xc8643c], jupiter: [0.12, 0xc9a877], sun: [0.2, 0xffe9a8] };
  for (const [key, [size, color]] of Object.entries(bodyStyle)) {
    if (bodies.has(key) || !trackFor(key)) continue;
    const mesh = new THREE.Mesh(dotGeo, new THREE.MeshBasicMaterial({ color }));
    mesh.scale.setScalar(size);
    scene.add(mesh);
    bodies.set(key, { key, mesh, label: makeLabel('body', ephem.bodies[key]?.name || key) });
  }
  $('tmin').textContent = `${fmtDate(tMin).slice(5)} ${fmtTime(tMin).slice(0, 5)}`;
  $('tmax').textContent = `${fmtDate(tMax).slice(5)} ${fmtTime(tMax).slice(0, 5)}`;
}

async function loadData() {
  const get = async (f) => { const r = await fetch(`data/${f}?_=${Date.now()}`); if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`); return r.json(); };
  const [s, e] = await Promise.all([get('schedule.json'), get('ephem.json')]);
  schedule = s; ephem = e;
  indexData();
}

// ---------------------------------------------------------------- time engine
const clock = { t: 0, rate: 1, dir: 1, playing: true, live: true };
const wallNow = () => Date.now() / 1000;
function setTime(t) { clock.t = Math.min(tMax, Math.max(tMin, t)); }
function goLive() {
  const w = wallNow();
  if (w < tMin || w > tMax) return;   // data too old to show the present; status line says so
  clock.live = true; clock.rate = 1; clock.dir = 1; clock.playing = true;
  setTime(wallNow());
  syncButtons();
}
function syncButtons() {
  document.querySelectorAll('.rate').forEach((b) => b.classList.toggle('on', +b.dataset.rate === clock.rate));
  $('play').textContent = clock.playing ? '❚❚' : '▶';
  $('rev').classList.toggle('on', clock.dir < 0);
  $('now').classList.toggle('on', clock.live);
}
document.querySelectorAll('.rate').forEach((b) => b.addEventListener('click', () => {
  clock.rate = +b.dataset.rate; clock.live = false; clock.playing = true; syncButtons();
}));
$('play').addEventListener('click', () => { clock.playing = !clock.playing; clock.live = false; syncButtons(); });
$('rev').addEventListener('click', () => { clock.dir = -clock.dir; clock.live = false; clock.playing = true; if (clock.rate === 1) clock.rate = 60; syncButtons(); });
$('now').addEventListener('click', goLive);
const slider = $('slider');
slider.addEventListener('input', () => { clock.live = false; setTime(tMin + (slider.value / 1000) * (tMax - tMin)); syncButtons(); });

// ---------------------------------------------------------------- views
const view = { focus: 'ALL', fly: null };
const tmpV = new THREE.Vector3(), tmpV2 = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0);
function viewTarget(key, out) {
  if (key === 'ALL') {
    out.copy(camera.position).setY(0);
    if (out.lengthSq() < 1e-6) out.set(1, 0, 1);
    return out.normalize().setY(0.5).normalize().multiplyScalar(15);
  }
  // Oblique view: above and east of the complex, so outbound links are visible.
  const u = tmpV2.copy(complexes.get(key).unit).applyAxisAngle(Y, earth.rotation.y);
  const east = new THREE.Vector3().crossVectors(Y, u).normalize();
  return out.copy(u).addScaledVector(east, 0.45).addScaledVector(Y, u.y > 0 ? -0.15 : 0.15).normalize().multiplyScalar(4.3);
}
function setView(key) {
  view.focus = key;
  view.fly = { t0: performance.now(), from: camera.position.clone(), dur: 1800, to: key === 'ALL' ? viewTarget('ALL', new THREE.Vector3()) : null };
  document.querySelectorAll('#views [data-view]').forEach((b) => b.classList.toggle('on', b.dataset.view === key));
}
document.querySelectorAll('#views [data-view]').forEach((b) => b.addEventListener('click', () => setView(b.dataset.view)));
$('fs').addEventListener('click', toggleFs);
function toggleFs() { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen(); }
addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' && e.key !== ' ') return;
  const k = e.key.toLowerCase();
  if (k === ' ') { e.preventDefault(); $('play').click(); }
  else if (k === 'n') goLive();
  else if (k === 'f') toggleFs();
  else if ('1234'.includes(k)) setView(['ALL', 'GDSCC', 'CDSCC', 'MDSCC'][+k - 1]);
});

// ---------------------------------------------------------------- links
const pulseTex = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'), grd = g.createRadialGradient(16, 16, 0, 16, 16, 16);
  grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.4, 'rgba(255,255,255,0.6)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 32, 32);
  return new THREE.CanvasTexture(c);
})();
const N_PULSE = 5;
function makePulses(color) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N_PULSE * 3), 3));
  const p = new THREE.Points(g, new THREE.PointsMaterial({ color, size: 9, sizeAttenuation: false, map: pulseTex, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  p.frustumCulled = false;
  scene.add(p);
  return p;
}
function makeLink(act, ant) {
  const geo = new LineGeometry();
  geo.setPositions(new Float32Array((CURVE_N + 1) * 3));
  const mat = new LineMaterial({ color: COLORS.track, linewidth: 2, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false });
  mat.resolution = resolution;
  const line = new Line2(geo, mat);
  line.frustumCulled = false;
  scene.add(line);
  return { act, ant, line, geo, mat, down: makePulses(COLORS.track), up: makePulses(COLORS.uplink), pts: new Float32Array((CURVE_N + 1) * 3) };
}
function disposeLink(l) {
  for (const o of [l.line, l.down, l.up]) { scene.remove(o); o.geometry.dispose(); o.material.dispose(); }
}
const bz = new THREE.Vector3(), P1 = new THREE.Vector3();
function bezier(A, C, S, u, out) {
  const w = 1 - u;
  return out.set(w * w * A.x + 2 * w * u * C.x + u * u * S.x, w * w * A.y + 2 * w * u * C.y + u * u * S.y, w * w * A.z + 2 * w * u * C.z + u * u * S.z);
}
function updateLink(l, S, phase, state, uplinkOn, dim) {
  const A = l.ant.world;
  P1.copy(A).multiplyScalar(1 + LINK_LIFT);
  for (let i = 0; i <= CURVE_N; i++) bezier(A, P1, S, i / CURVE_N, bz).toArray(l.pts, i * 3);
  // Write segment endpoints in place (avoids reallocating GPU buffers every frame).
  const arr = l.geo.attributes.instanceStart.data.array;
  for (let i = 0; i < CURVE_N; i++) for (let k = 0; k < 6; k++) arr[i * 6 + k] = l.pts[i * 3 + k];
  l.geo.attributes.instanceStart.data.needsUpdate = true;

  const tracking = state === 'track';
  const big = l.ant.cfg.size_m >= 70;
  l.mat.color.setHex(tracking ? COLORS.track : COLORS.setup);
  l.mat.linewidth = tracking ? (big ? 4.2 : 2.4) : 1.2;
  l.mat.opacity = (tracking ? 0.95 : 0.35) * dim;
  l.down.visible = tracking; l.up.visible = tracking && uplinkOn;
  l.down.material.opacity = l.up.material.opacity = dim;
  if (tracking) {
    for (const [pts, sign] of [[l.down, -1], [l.up, 1]]) {
      if (!pts.visible) continue;
      const pa = pts.geometry.attributes.position;
      for (let i = 0; i < N_PULSE; i++) {
        let u = (phase + i / N_PULSE) % 1;
        if (sign < 0) u = 1 - u;
        bezier(A, P1, S, u, bz); pa.setXYZ(i, bz.x, bz.y, bz.z);
      }
      pa.needsUpdate = true;
    }
  }
}

// ---------------------------------------------------------------- per-frame state
function antennaState(a, t) {
  // Returns {state, acts}: track > setup/teardown > busy > idle
  let best = 'idle'; const active = [];
  const rank = { idle: 0, busy: 1, teardown: 2, setup: 2, track: 3 };
  for (const act of a.acts) {
    if (t < act.t[0] || t >= act.t[3]) continue;
    let st = 'busy';
    if (act.kind === 'track') st = t < act.t[1] ? 'setup' : t < act.t[2] ? 'track' : 'teardown';
    act.state = st;
    act.upNow = st === 'track' && act.up.some(([s, e]) => t >= s && t < e);
    active.push(act);
    if (rank[st] > rank[best]) best = st;
  }
  return { state: best, acts: active };
}

function occluded(p) {  // is p hidden behind the Earth from the camera?
  const c = camera.position, dx = p.x - c.x, dy = p.y - c.y, dz = p.z - c.z;
  const u = -(c.x * dx + c.y * dy + c.z * dz) / (dx * dx + dy * dy + dz * dz);
  if (u <= 0 || u >= 1) return false;
  const x = c.x + u * dx, y = c.y + u * dy, z = c.z + u * dz;
  return x * x + y * y + z * z < 0.99;
}
const proj = new THREE.Vector3();
function place(el, p, dx = 0, dy = 0) {
  proj.copy(p).project(camera);
  if (proj.z > 1 || proj.z < -1 || occluded(p)) { el.style.display = 'none'; return null; }
  const x = (proj.x * 0.5 + 0.5) * innerWidth, y = (-proj.y * 0.5 + 0.5) * innerHeight;
  el.style.display = '';
  el.style.transform = `translate(${(x + dx).toFixed(1)}px, ${(y + dy).toFixed(1)}px)`;
  return [x, y];
}

const scLabels = [];   // pooled labels for spacecraft clusters
function updateCraftLabels() {
  const items = [];
  for (const c of craft.values()) {
    if (!c.visible) continue;
    proj.copy(c.pos).project(camera);
    if (proj.z > 1 || proj.z < -1 || occluded(c.pos)) continue;
    items.push({ c, x: (proj.x * 0.5 + 0.5) * innerWidth, y: (-proj.y * 0.5 + 0.5) * innerHeight });
  }
  // Greedy clustering: spacecraft that overlap on screen share one label.
  items.sort((a, b) => (b.c.active - a.c.active) || a.c.key.localeCompare(b.c.key));
  const clusters = [];
  for (const it of items) {
    const cl = clusters.find((k) => Math.abs(k.x - it.x) < 26 && Math.abs(k.y - it.y) < 12);
    if (cl) cl.items.push(it); else clusters.push({ x: it.x, y: it.y, items: [it] });
  }
  clusters.forEach((cl, i) => {
    const el = scLabels[i] ?? (scLabels[i] = makeLabel('sc', ''));
    const act = cl.items.filter((it) => it.c.active).map((it) => it.c.key);
    const rest = cl.items.filter((it) => !it.c.active).map((it) => it.c.key);
    const text = act.length ? act.join(' · ') + (rest.length ? `  +${rest.length}` : '') : (rest.length > 3 ? `${rest.slice(0, 3).join(' · ')} +${rest.length - 3}` : rest.join(' · '));
    if (el.textContent !== text) el.textContent = text;
    el.classList.toggle('active', act.length > 0);
    el.style.display = '';
    el.style.transform = `translate(${(cl.x + 5).toFixed(1)}px, ${(cl.y - 7).toFixed(1)}px)`;
  });
  for (let i = clusters.length; i < scLabels.length; i++) scLabels[i].style.display = 'none';
}

let boardAt = 0;
function updateBoard(states) {
  const now = performance.now();
  if (now - boardAt < 250) return;
  boardAt = now;
  let html = '';
  for (const [key, cx] of complexes) {
    html += `<h3>${COMPLEX_LABEL[key] || key}</h3>`;
    const dimmed = view.focus !== 'ALL' && view.focus !== key ? ' dimmed' : '';
    for (const a of cx.antennas) {
      const { state, acts } = states.get(a.dss);
      const main = acts.filter((x) => x.state === state);
      const who = main.map((x) => (x.kind === 'track' || !['DSN', 'DSS'].includes(x.user) ? x.user : x.activity)).join(' · ');
      const up = main.some((x) => x.upNow);
      const st = { idle: '', busy: 'BUSY', setup: 'SETUP', teardown: 'TEARDOWN', track: up ? 'UP + DOWN' : 'DOWN' }[state];
      html += `<div class="row ${state}${up ? ' up' : ''}${dimmed}"><span class="dot"></span><span class="dss"><b>${a.dss}</b> ${a.cfg.size_m}</span><span class="who" title="${main.map((x) => x.activity).join(', ')}">${who || '—'}</span><span class="st">${st}</span></div>`;
    }
  }
  html += `<div class="legend"><i style="background:#4fd8ff"></i>tracking &nbsp; <i style="background:#ffb347"></i>uplink<br><i style="background:#7aa2ff"></i>setup / teardown &nbsp; <i style="background:#f0a030"></i>busy<br>distance scale is logarithmic</div>`;
  $('board').innerHTML = html;
}

// ---------------------------------------------------------------- main loop
let lastFrame = performance.now(), lastGmst = null, lastReload = performance.now();
const scPos = new THREE.Vector3(), states = new Map();

function frame(nowMs) {
  requestAnimationFrame(frame);
  const dt = Math.min((nowMs - lastFrame) / 1000, 0.25);
  lastFrame = nowMs;

  // Time
  if (clock.live) {
    const w = wallNow();
    if (w > tMax || w < tMin) clock.live = false;
    setTime(w);
  } else if (clock.playing) {
    setTime(clock.t + dt * clock.rate * clock.dir);
    if (clock.t <= tMin || clock.t >= tMax) { clock.playing = false; syncButtons(); }
  }
  const t = clock.t;

  // Earth rotation and Sun
  const th = gmst(t);
  earth.rotation.y = th;
  earth.updateMatrixWorld(true);
  const sun = trackFor('sun');
  if (sun && interp(sun, t, tmpV)) sunDir.copy(tmpV).normalize();

  // Camera: follow the Earth's rotation when a complex is in focus
  if (view.focus !== 'ALL' && lastGmst !== null && !view.fly) {
    let d = th - lastGmst;
    if (d > Math.PI) d -= 2 * Math.PI; else if (d < -Math.PI) d += 2 * Math.PI;
    camera.position.applyAxisAngle(Y, d);
  }
  lastGmst = th;
  if (view.fly) {
    const u = Math.min((nowMs - view.fly.t0) / view.fly.dur, 1), e = u * u * (3 - 2 * u);
    if (view.fly.to) tmpV.copy(view.fly.to); else viewTarget(view.focus, tmpV);
    const r = THREE.MathUtils.lerp(view.fly.from.length(), tmpV.length(), e);
    camera.position.copy(view.fly.from).normalize().lerp(tmpV.normalize(), e).normalize().multiplyScalar(r);
    if (u >= 1) view.fly = null;
  }
  controls.update();

  // Bodies and spacecraft
  for (const b of bodies.values()) {
    const tr = trackFor(b.key);
    b.mesh.visible = !!(tr && interp(tr, t, b.mesh.position));
    if (b.mesh.visible) scaleKm(b.mesh.position);
  }
  for (const c of craft.values()) {
    const tr = trackFor(c.key);
    c.visible = !!(tr && interp(tr, t, c.pos));
    if (c.visible) scaleKm(c.pos);
    c.mesh.visible = c.visible;
    c.active = false;
  }

  // Antennas and links
  const phase = (nowMs / 4000) % 1;
  const wanted = new Set();
  for (const a of antennas.values()) {
    a.marker.getWorldPosition(a.world);
    const s = antennaState(a, t);
    states.set(a.dss, s);
    a.state = s.state;
    a.marker.material.color.setHex({ idle: COLORS.idle, busy: COLORS.busy, setup: COLORS.setup, teardown: COLORS.setup, track: COLORS.track }[s.state]);
    const dim = view.focus === 'ALL' || view.focus === a.complex ? 1 : 0.15;
    for (const act of s.acts) {
      if (!act.hasTraj) continue;
      const c = craft.get(act.user);
      if (!c || !c.visible) continue;
      wanted.add(act.id);
      let l = links.get(act.id);
      if (!l) links.set(act.id, (l = makeLink(act, a)));
      updateLink(l, c.pos, phase, act.state, act.upNow, dim);
      if (act.state === 'track') c.active = true;
    }
  }
  for (const [id, l] of links) if (!wanted.has(id)) { disposeLink(l); links.delete(id); }
  for (const c of craft.values()) {
    // constant apparent size, whatever the zoom
    c.mesh.scale.setScalar((c.active ? 0.0034 : 0.0022) * Math.max(camera.position.distanceTo(c.pos), 1));
  }

  renderer.render(scene, camera);

  // Labels
  const camDist = camera.position.length();
  for (const cx of complexes.values()) {
    tmpV.copy(cx.unit).applyAxisAngle(Y, th).multiplyScalar(1.01);
    place(cx.label, tmpV, 10, -26);
  }
  for (const a of antennas.values()) {
    if (camDist > 7) { a.label.style.display = 'none'; continue; }
    a.label.className = `lbl ant ${a.state === 'track' ? 'track' : a.state === 'busy' ? 'busy' : ''}`;
    place(a.label, a.world, -6, a.labelDy);
  }
  for (const b of bodies.values()) b.mesh.visible ? place(b.label, b.mesh.position, -4, 9) : (b.label.style.display = 'none');
  for (const r of ringLabels) place(r.el, r.pos, 4, 2);
  updateCraftLabels();
  updateBoard(states);

  // HUD
  $('date').textContent = `${fmtDate(t)} · ${fmtDoy(t)}`;
  $('time').textContent = fmtTime(t);
  $('live').classList.toggle('on', clock.live);
  if (document.activeElement !== slider) slider.value = Math.round((t - tMin) / (tMax - tMin) * 1000);
  const w = wallNow(), tick = $('nowtick');
  tick.style.display = w >= tMin && w <= tMax ? '' : 'none';
  tick.style.left = `${(w - tMin) / (tMax - tMin) * 100}%`;
  const age = (w - generated) / 3600;
  $('status').innerHTML = `Schedule and trajectories as of ${fmtDate(generated)} ${fmtTime(generated).slice(0, 5)} UTC`
    + (age > 3 ? ` <span class="warn">— data is ${age < 48 ? age.toFixed(0) + ' h' : (age / 24).toFixed(0) + ' days'} old; run the backend to refresh</span>` : '');

  // Pick up new data from the hourly backend run
  if (nowMs - lastReload > 5 * 60 * 1000) { lastReload = nowMs; loadData().catch(() => {}); }
}

// ---------------------------------------------------------------- start
loadData().then(() => {
  const t0 = params.get('t');
  if (t0) { clock.live = false; setTime(Date.parse(t0) / 1000); if (params.has('rate')) clock.rate = +params.get('rate'); }
  else if (wallNow() >= tMin && wallNow() <= tMax) goLive();
  else { clock.live = false; setTime(generated); }
  if (params.get('view')) setView(params.get('view'));
  syncButtons();
  window.__dsnsim = { clock, view, craft, links, antennas };
  requestAnimationFrame(frame);
}).catch((err) => {
  const el = $('error');
  el.hidden = false;
  el.textContent = `Could not load data.\n\n${err.message}\n\nRun:  python -m dsnsim.build --out site/data\nthen serve the site folder:  python -m http.server -d site 8000`;
});
