import { useEffect, useRef, useState, type MutableRefObject } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import aquaUrl from '@/assets/satellites/aqua.glb?url';
import suomiUrl from '@/assets/satellites/suomi-npp.glb?url';
import earthUrl from '@/assets/earth-surface.jpg?url';
import fastEarthUrl from '@/assets/earth-fast.jpg?url';
import { SPACECRAFT_LABELS } from '@/lib/opening-copy';
import { advanceGlobeRotation, BLUE_MARBLE_TILES, mercatorLatitude, smoothPhase, surfaceCameraDistance, SURFACE_VIEW, tilePosition } from '@/lib/globe-transition';

/** Presentation geometry only: these are not satellite ephemerides or fire coordinates. */
export default function OrbitalScene({ playing, progress, onSurfaceReady, onGlobeReady }: { playing: boolean; progress: MutableRefObject<number>; onSurfaceReady?: () => void; onGlobeReady?: () => void }) {
  const host = useRef<HTMLDivElement>(null);
  const animate = useRef(playing);
  const surfaceReady = useRef(onSurfaceReady); surfaceReady.current = onSurfaceReady;
  const globeReady = useRef(onGlobeReady); globeReady.current = onGlobeReady;
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => { animate.current = playing; }, [playing]);
  useEffect(() => {
    const element = host.current;
    if (!element) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch { setUnavailable(true); return; }
    const css = getComputedStyle(element);
    const color = (token: string) => {
      // Resolve OKLCH tokens in the browser before passing sRGB to Three.js.
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const context = canvas.getContext('2d');
      if (!context) return new THREE.Color();
      context.fillStyle = css.getPropertyValue(token).trim();
      context.fillRect(0, 0, 1, 1);
      const pixel = context.getImageData(0, 0, 1, 1).data;
      return new THREE.Color().setRGB((pixel[0] ?? 0) / 255, (pixel[1] ?? 0) / 255, (pixel[2] ?? 0) / 255, THREE.SRGBColorSpace);
    };
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    element.appendChild(renderer.domElement);
    const contextLost = (event: Event) => { event.preventDefault(); setUnavailable(true); };
    const contextRestored = () => { surface.needsUpdate = true; setUnavailable(false); };
    renderer.domElement.addEventListener('webglcontextlost', contextLost);
    renderer.domElement.addEventListener('webglcontextrestored', contextRestored);
    renderer.domElement.setAttribute('aria-label', 'Earth with illustrative orbiting satellite models');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(SURFACE_VIEW.fov, 1, 0.01, 80);
    camera.position.set(0, 0.65, 8.4);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.minPolarAngle = 0.5;
    controls.maxPolarAngle = 2.6;
    scene.add(new THREE.AmbientLight(color('--orbital-light'), 2.2));
    const sun = new THREE.DirectionalLight(color('--orbital-light'), 3);
    sun.position.set(-3, 4, 5);
    scene.add(sun);
    const system = new THREE.Group();
    scene.add(system);
    // One geographic mesh becomes a Mercator surface before handing off to Leaflet.
    // UVs never move, so coastlines stay attached throughout the descent.
    const geometry = new THREE.PlaneGeometry(1, 1, 256, 256);
    const positions = geometry.getAttribute('position');
    const uv = geometry.getAttribute('uv');
    const globePositions = new Float32Array(positions.count * 3);
    const mapPositions = new Float32Array(positions.count * 3);
    const latitude0 = SURFACE_VIEW.latitude * Math.PI / 180;
    for (let i = 0; i < positions.count; i++) {
      const longitude = uv.getX(i) * 360 - 180;
      const latitude = Math.max(-89.8, Math.min(89.8, uv.getY(i) * 180 - 90));
      const lat = latitude * Math.PI / 180;
      const lon = (longitude - SURFACE_VIEW.longitude) * Math.PI / 180;
      const r = SURFACE_VIEW.radius;
      globePositions.set([r * Math.cos(lat) * Math.sin(lon), r * (Math.sin(lat) * Math.cos(latitude0) - Math.cos(lat) * Math.cos(lon) * Math.sin(latitude0)), r * (Math.sin(lat) * Math.sin(latitude0) + Math.cos(lat) * Math.cos(lon) * Math.cos(latitude0))], i * 3);
      mapPositions.set([r * lon, r * (mercatorLatitude(Math.max(-85.051129, Math.min(85.051129, latitude))) - mercatorLatitude(SURFACE_VIEW.latitude)), r], i * 3);
      positions.setXYZ(i, globePositions[i * 3] ?? 0, globePositions[i * 3 + 1] ?? 0, globePositions[i * 3 + 2] ?? 0);
    }
    const surface = new THREE.MeshBasicMaterial({ color: color('--orbital-light') });
    geometry.setAttribute('openingDepth', new THREE.Float32BufferAttribute(Array.from({ length: positions.count }, (_, i) => globePositions[i * 3 + 2] ?? 0), 1));
    // WebGL requires a complete sampler even while atlasMix is zero. An empty
    // Texture makes the first frames invalid on some drivers before tiles load.
    const atlasPlaceholder = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    atlasPlaceholder.needsUpdate = true;
    const atlasUniforms = {
      handoffAtlas: { value: atlasPlaceholder as THREE.Texture },
      atlasBounds: { value: new THREE.Vector4(0, 0, 1, 1) },
      atlasMix: { value: 0 },
      idleRotation: { value: 0 },
      rotationMix: { value: 1 },
      hideFarSide: { value: 0 },
    };
    surface.onBeforeCompile = shader => {
      Object.assign(shader.uniforms, atlasUniforms);
      shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\nattribute float openingDepth;\nvarying float sourceDepth;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nsourceDepth = openingDepth;');
      shader.fragmentShader = shader.fragmentShader.replace('#include <common>', `#include <common>
        uniform sampler2D handoffAtlas;
        uniform vec4 atlasBounds;
        uniform float atlasMix;
        uniform float idleRotation;
        uniform float rotationMix;
        uniform float hideFarSide;
        varying float sourceDepth;`);
      // Rotate only the opening imagery, never the geographic morph vertices.
      const mapFragment = THREE.ShaderChunk.map_fragment.replace(
        'vec4 sampledDiffuseColor = texture2D( map, vMapUv );',
        `vec4 sampledDiffuseColor = texture2D(map, vec2(fract(vMapUv.x - idleRotation * rotationMix / 6.28318530718), vMapUv.y));`,
      );
      shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', `${mapFragment}
        #ifdef USE_MAP
          if (hideFarSide > 0.5 && sourceDepth < 0.0) discard;
          float latitude = clamp(vMapUv.y * 3.14159265359 - 1.57079632679, -1.48442223, 1.48442223);
          vec2 worldUv = vec2(vMapUv.x, (1.0 - log(tan(0.78539816339 + latitude * 0.5)) / 3.14159265359) * 0.5);
          vec2 atlasUv = (worldUv - atlasBounds.xy) / atlasBounds.zw;
          float inside = step(0.0, atlasUv.x) * step(atlasUv.x, 1.0) * step(0.0, atlasUv.y) * step(atlasUv.y, 1.0);
          vec4 alignedColor = texture2D(handoffAtlas, vec2(atlasUv.x, 1.0 - atlasUv.y));
          diffuseColor = mix(diffuseColor, alignedColor, atlasMix * inside);
        #endif`);
    };
    const earth = new THREE.Mesh(geometry, surface);
    earth.frustumCulled = false;
    system.add(earth);
    let disposed = false;
    let atlasTexture: THREE.CanvasTexture | undefined;
    let atlasGeneration = 0;
    const loadAlignedImagery = async () => {
      const generation = ++atlasGeneration;
      const center = tilePosition(SURFACE_VIEW.latitude, SURFACE_VIEW.longitude, SURFACE_VIEW.zoom);
      const worldTiles = 2 ** SURFACE_VIEW.zoom;
      const halfX = Math.ceil(element.clientWidth / 512) + 1;
      const halfY = Math.ceil(element.clientHeight / 512) + 1;
      const minX = Math.max(0, Math.floor(center.x) - halfX);
      const minY = Math.max(0, Math.floor(center.y) - halfY);
      const maxX = Math.min(worldTiles - 1, Math.floor(center.x) + halfX);
      const maxY = Math.min(worldTiles - 1, Math.floor(center.y) + halfY);
      const atlas = document.createElement('canvas');
      atlas.width = (maxX - minX + 1) * 256;
      atlas.height = (maxY - minY + 1) * 256;
      const context = atlas.getContext('2d');
      if (!context) return;
      const requests: Promise<void>[] = [];
      for (let y = minY; y <= maxY; y++) for (let x = minX; x <= maxX; x++) requests.push(new Promise((resolve, reject) => {
        const image = new Image();
        image.crossOrigin = 'anonymous';
        image.onload = () => { context.drawImage(image, (x - minX) * 256, (y - minY) * 256); resolve(); };
        image.onerror = reject;
        image.src = BLUE_MARBLE_TILES.replace('{z}', String(SURFACE_VIEW.zoom)).replace('{x}', String(x)).replace('{y}', String(y));
      }));
      try {
        await Promise.all(requests);
        if (disposed || generation !== atlasGeneration) return;
        atlasTexture?.dispose();
        atlasTexture = new THREE.CanvasTexture(atlas);
        atlasTexture.colorSpace = THREE.SRGBColorSpace;
        atlasUniforms.handoffAtlas.value = atlasTexture;
        atlasUniforms.atlasBounds.value.set(minX / worldTiles, minY / worldTiles, (maxX - minX + 1) / worldTiles, (maxY - minY + 1) / worldTiles);
        element.dataset['surfaceReady'] = 'true';
        surfaceReady.current?.();
      } catch { if (!disposed) element.dataset['surfaceError'] = 'Aligned NASA imagery unavailable'; }
    };
    let releaseSpacecraft: (() => void) | undefined;
    const earthLoaded = new Promise<void>(resolve => { releaseSpacecraft = resolve; });
    let detailedTexture: THREE.Texture | undefined;
    const textureLoader = new THREE.TextureLoader();
    const texture = textureLoader.load(fastEarthUrl, loaded => {
      if (disposed) { loaded.dispose(); return; }
      loaded.colorSpace = THREE.SRGBColorSpace;
      surface.map = loaded;
      surface.needsUpdate = true;
      element.dataset['sceneReady'] = 'true';
      globeReady.current?.();
      releaseSpacecraft?.();
      void loadAlignedImagery();
      detailedTexture = textureLoader.load(earthUrl, detailed => {
        if (disposed) { detailed.dispose(); return; }
        detailed.colorSpace = THREE.SRGBColorSpace;
        surface.map = detailed;
        surface.needsUpdate = true;
      });
    }, undefined, () => { if (!disposed) setUnavailable(true); });
    const wireMaterial = new THREE.LineBasicMaterial({ color: color('--orbital-track'), transparent: true, opacity: 0.65 });
    const loader = new GLTFLoader();
    let modelsLoaded = 0;
    const disposeModel = (model: THREE.Object3D) => model.traverse(object => {
      if (!(object instanceof THREE.Mesh)) return;
      object.geometry.dispose();
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach(material => {
        Object.values(material).forEach(value => { if (value instanceof THREE.Texture) value.dispose(); });
        material.dispose();
      });
    });
    const orbiters: { group: THREE.Group; satellite: THREE.Group; label: HTMLDivElement; phase: number; speed: number; radius: number }[] = [];
    for (let i = 0; i < 2; i++) {
      const orbit = new THREE.Group();
      orbit.rotation.set(0.7 + i * 0.8, i * 0.6, 0.45 - i * 1.2);
      system.add(orbit);
      const radius = 2.13 + i * 0.3;
      const path = Array.from({ length: 161 }, (_, j) => new THREE.Vector3(Math.cos(j / 160 * Math.PI * 2) * radius, 0, Math.sin(j / 160 * Math.PI * 2) * radius));
      orbit.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(path), wireMaterial));
      const satellite = new THREE.Group();
      const label = document.createElement('div');
      label.className = 'orbital-spacecraft-name';
      const sensorName = document.createElement('strong');
      sensorName.textContent = SPACECRAFT_LABELS[i]?.sensor ?? '';
      const spacecraftName = document.createElement('small');
      spacecraftName.textContent = SPACECRAFT_LABELS[i]?.spacecraft ?? '';
      label.append(sensorName, spacecraftName);
      label.hidden = true;
      element.appendChild(label);
      const modelUrl = i === 0 ? aquaUrl : suomiUrl;
      void earthLoaded.then(() => {
      if (disposed) return;
      loader.load(modelUrl, gltf => {
        const model = gltf.scene;
        if (disposed) { disposeModel(model); return; }
        const bounds = new THREE.Box3().setFromObject(model);
        const dimensions = bounds.getSize(new THREE.Vector3());
        const center = bounds.getCenter(new THREE.Vector3());
        const size = Math.max(dimensions.x, dimensions.y, dimensions.z);
        if (!size) { disposeModel(model); return; }
        const scale = 0.85 / size;
        model.scale.setScalar(scale);
        model.position.copy(center.multiplyScalar(-scale));
        satellite.add(model);
        modelsLoaded += 1;
        element.dataset['satellitesReady'] = String(modelsLoaded);
      }, undefined, () => {
        if (!disposed) element.dataset['satelliteError'] = 'NASA spacecraft model unavailable';
      });
      });
      orbit.add(satellite);
      orbiters.push({ group: orbit, satellite, label, phase: 0.3 + i * 2.7, speed: 0.18 + i * 0.04, radius });
    }
    let startDistance = 8.4;
    let previousSize = '';
    const resize = () => {
      const width = element.clientWidth;
      const height = element.clientHeight;
      if (!width || !height) return;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      // Preserve the former globe framing without resizing the render surface on scroll.
      const openingInsets = width < 650 ? 307 : 110;
      startDistance = (width < 650 ? 10.8 : 8.4) * height / Math.max(180, height - openingInsets);
      camera.updateProjectionMatrix();
      const size = `${width}:${height}`;
      if (previousSize !== size) { previousSize = size; if (element.dataset['sceneReady'] === 'true') void loadAlignedImagery(); }
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let previousFrame = performance.now();
    let lastMorph = -1;
    let earthRotation = 0;
    const startPosition = new THREE.Vector3(0, 0.65, startDistance);
    let frame = 0;
    let settledAtEnd = false;
    const worldPosition = new THREE.Vector3();
    const projected = new THREE.Vector3();
    const ray = new THREE.Ray();
    const globeBounds = new THREE.Sphere(new THREE.Vector3(), SURFACE_VIEW.radius);
    const intersection = new THREE.Vector3();
    const draw = () => {
      frame = requestAnimationFrame(draw);
      const now = performance.now();
      const delta = Math.min((now - previousFrame) / 1000, 0.05);
      previousFrame = now;
      const running = animate.current && !reduced.matches && !document.hidden;
      const approach = reduced.matches ? 0 : progress.current;
      // Com o mapa em tela cheia o globo fica escondido: um quadro final basta, o resto da GPU fica para o mapa.
      if (approach >= 0.999) { if (settledAtEnd) return; settledAtEnd = true; } else settledAtEnd = false;
      const descent = smoothPhase(approach, 0.02, 0.9);
      const flatten = smoothPhase(approach, 0.35, 0.88);
      earthRotation = advanceGlobeRotation(earthRotation, delta, approach, running);
      atlasUniforms.idleRotation.value = earthRotation;
      atlasUniforms.rotationMix.value = 1 - smoothPhase(approach, 0.02, 0.35);
      atlasUniforms.hideFarSide.value = flatten > 0 && flatten < 1 ? 1 : 0;
      // The globe photo and GIBS atlas have different registration. Crossfading
      // them creates two visible coastlines; use one geographic image at a time.
      atlasUniforms.atlasMix.value = atlasTexture && approach >= 0.35 ? 1 : 0;
      if (flatten !== lastMorph) {
        for (let i = 0; i < positions.count * 3; i++) positions.array[i] = THREE.MathUtils.lerp(globePositions[i] ?? 0, mapPositions[i] ?? 0, flatten);
        positions.needsUpdate = true;
        lastMorph = flatten;
      }
      controls.enabled = approach < 0.02;
      if (controls.enabled) {
        if (progress.current < 0.001) camera.position.setLength(startDistance);
        controls.update();
        startPosition.copy(camera.position);
      } else {
        const endDistance = SURFACE_VIEW.radius + surfaceCameraDistance(element.clientHeight);
        camera.position.set(startPosition.x * (1 - descent), startPosition.y * (1 - descent), Math.exp(THREE.MathUtils.lerp(Math.log(Math.max(startPosition.z, 3)), Math.log(endDistance), descent)));
        camera.lookAt(0, 0, SURFACE_VIEW.radius * descent);
      }
      const width = element.clientWidth;
      const height = element.clientHeight;
      camera.setViewOffset(width, height, width < 650 ? 0 : -width * 0.15 * (1 - descent), -(width < 650 ? 93.5 : 13) * (1 - descent), width, height);
      renderer.domElement.dataset['cameraDistance'] = camera.position.z.toFixed(3);
      renderer.domElement.dataset['surfaceMorph'] = flatten.toFixed(3);
      renderer.domElement.dataset['earthRotation'] = earthRotation.toFixed(4);
      orbiters.forEach(item => {
        item.group.visible = approach < 0.4;
        item.satellite.scale.setScalar(1 - smoothPhase(approach, 0.12, 0.4));
        if (running) item.phase += delta * item.speed;
        item.satellite.position.set(Math.cos(item.phase) * item.radius, 0, Math.sin(item.phase) * item.radius);
        item.satellite.lookAt(0, 0, 0);
      });
      renderer.render(scene, camera);
      orbiters.forEach(item => {
        item.satellite.getWorldPosition(worldPosition);
        projected.copy(worldPosition).project(camera);
        ray.set(camera.position, worldPosition.clone().sub(camera.position).normalize());
        const hit = ray.intersectSphere(globeBounds, intersection);
        const occluded = hit !== null && camera.position.distanceTo(hit) < camera.position.distanceTo(worldPosition) - 0.1;
        item.label.hidden = approach >= 0.35 || !item.satellite.children.length || occluded || Math.abs(projected.x) > 1 || Math.abs(projected.y) > 1 || projected.z > 1;
        if (item.label.hidden) return;
        const x = Math.max(8, Math.min(width - item.label.offsetWidth - 8, (projected.x + 1) * width / 2 - item.label.offsetWidth / 2));
        const y = Math.max(8, Math.min(height - item.label.offsetHeight - 8, (1 - projected.y) * height / 2 + 25));
        item.label.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      });
    };
    draw();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      scene.traverse(object => {
        if (object instanceof THREE.Mesh || object instanceof THREE.Line) object.geometry.dispose();
      });
      orbiters.forEach(item => disposeModel(item.satellite));
      orbiters.forEach(item => item.label.remove());
      [surface, wireMaterial].forEach(material => material.dispose());
      texture.dispose();
      detailedTexture?.dispose();
      atlasTexture?.dispose();
      atlasPlaceholder.dispose();
      renderer.domElement.removeEventListener('webglcontextlost', contextLost);
      renderer.domElement.removeEventListener('webglcontextrestored', contextRestored);
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);
  return <div className="orbital-canvas" ref={host}>{unavailable && <div className="orbital-fallback"><img src={earthUrl} alt="Earth surface" /><span>Interactive globe unavailable on this device</span></div>}</div>;
}