import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';

// Vertex Shader with Simplex Noise
const vertexShader = `
  uniform float uTime;
  uniform float uDistortion;
  uniform float uSize;
  uniform vec2 uMouse;
  varying float vNoise;

  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x*34.0)+1.0)*x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2  C = vec2(1.0/6.0, 1.0/3.0) ;
    const vec4  D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy) );
    vec3 x0 = v - i + dot(i, C.xxx) ;
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min( g.xyz, l.zxy );
    vec3 i2 = max( g.xyz, l.zxy );
    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
    i = mod289(i);
    vec4 p = permute( permute( permute(
                i.z + vec4(0.0, i1.z, i2.z, 1.0 ))
            + i.y + vec4(0.0, i1.y, i2.y, 1.0 ))
            + i.x + vec4(0.0, i1.x, i2.x, 1.0 ));
    float n_ = 1.0/7.0;
    vec3  ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z *ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_ );
    vec4 x = x_ *ns.x + ns.yyyy;
    vec4 y = y_ *ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4( x.xy, y.xy );
    vec4 b1 = vec4( x.zw, y.zw );
    vec4 s0 = floor(b0)*2.0 + 1.0;
    vec4 s1 = floor(b1)*2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw*sh.xxyy ;
    vec4 a1 = b1.xzyw + s1.xzyw*sh.zzww ;
    vec3 p0 = vec3(a0.xy,h.x);
    vec3 p1 = vec3(a0.zw,h.y);
    vec3 p2 = vec3(a1.xy,h.z);
    vec3 p3 = vec3(a1.zw,h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2, p2), dot(p3,p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot( m*m, vec4( dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3) ) );
  }

  void main() {
    vec3 pos = position;
    float noiseFreq = 0.5;
    float noiseAmp = uDistortion;
    float noise = snoise(vec3(pos.x * noiseFreq + uTime * 0.1, pos.y * noiseFreq, pos.z * noiseFreq));
    vNoise = noise;
    vec3 newPos = pos + (normalize(pos) * noise * noiseAmp);
    float dist = distance(uMouse * 10.0, newPos.xy);
    float interaction = smoothstep(5.0, 0.0, dist);
    newPos += normalize(pos) * interaction * 0.5;
    vec4 mvPosition = modelViewMatrix * vec4(newPos, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    gl_PointSize = uSize * (24.0 / -mvPosition.z) * (1.0 + noise * 0.5);
  }
`;

// Fragment Shader
const fragmentShader = `
  uniform vec3 uColor;
  uniform float uOpacity;
  varying float vNoise;

  void main() {
    vec2 center = gl_PointCoord - vec2(0.5);
    float dist = length(center);
    if (dist > 0.5) discard;
    float alpha = smoothstep(0.5, 0.2, dist) * uOpacity;
    vec3 darkColor = uColor * 0.6;
    vec3 lightColor = uColor * 1.6;
    vec3 finalColor = mix(darkColor, lightColor, vNoise * 0.5 + 0.5);
    gl_FragColor = vec4(finalColor, alpha);
  }
`;

interface ParticleBackgroundProps {
  className?: string;
  opacity?: number;
}

export const ParticleBackground = ({
  className = '',
  opacity = 0.7,
}: ParticleBackgroundProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const uniformsRef = useRef<{ [key: string]: THREE.IUniform } | null>(null);
  const frameRef = useRef<number>(0);
  const timeRef = useRef<number>(0);
  const mouseRef = useRef({ x: 0, y: 0 });

  // Initialize Three.js scene
  const initScene = useCallback(() => {
    if (!containerRef.current) return;

    // Scene
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xe7e5e4, 0.03);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(
      50,
      window.innerWidth / window.innerHeight,
      0.1,
      100
    );
    camera.position.set(0, 0, 18);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Systems Group - slightly left of center
    const systemsGroup = new THREE.Group();
    systemsGroup.position.set(-1.5, 0.5, 0);
    scene.add(systemsGroup);

    // Particle Geometry - larger size for better visibility
    const geometry = new THREE.IcosahedronGeometry(6.5, 32);

    // Uniforms
    const uniforms = {
      uTime: { value: 0 },
      uDistortion: { value: 0.55 },
      uSize: { value: 2.2 },
      uColor: { value: new THREE.Color('#292524') },
      uOpacity: { value: 0.4 },
      uMouse: { value: new THREE.Vector2(0, 0) },
    };
    uniformsRef.current = uniforms;

    // Shader Material
    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
    });

    // Particles
    const particles = new THREE.Points(geometry, material);
    systemsGroup.add(particles);

    // Orbits
    const lineGroup = new THREE.Group();
    systemsGroup.add(lineGroup);

    const createOrbit = (radius: number, rotation: { x: number; y: number }) => {
      const curve = new THREE.EllipseCurve(0, 0, radius, radius, 0, 2 * Math.PI, false, 0);
      const points = curve.getPoints(128);
      const orbitGeometry = new THREE.BufferGeometry().setFromPoints(
        points.map((p) => new THREE.Vector3(p.x, p.y, 0))
      );
      const orbitMaterial = new THREE.LineBasicMaterial({
        color: 0x78350f,
        transparent: true,
        opacity: 0.08,
      });
      const orbit = new THREE.Line(orbitGeometry, orbitMaterial);
      orbit.rotation.set(rotation.x, rotation.y, 0);
      lineGroup.add(orbit);
    };

    createOrbit(7.8, { x: Math.PI / 2, y: 0 });
    createOrbit(8.4, { x: Math.PI / 3, y: Math.PI / 6 });
    createOrbit(9.2, { x: Math.PI / 1.8, y: Math.PI / 4 });

    // Store references for animation
    return { systemsGroup, lineGroup };
  }, []);

  // Animation loop
  const animate = useCallback(
    (systemsGroup: THREE.Group, lineGroup: THREE.Group) => {
      const loop = () => {
        if (!rendererRef.current || !sceneRef.current || !cameraRef.current || !uniformsRef.current) {
          return;
        }

        timeRef.current += 0.008;
        const time = timeRef.current;

        // Rotate systems
        systemsGroup.rotation.y = time * 0.03;
        lineGroup.rotation.x = Math.sin(time * 0.05) * 0.05;

        // Update uniforms
        uniformsRef.current.uTime.value = time;

        // Smooth mouse interpolation
        uniformsRef.current.uMouse.value.x +=
          (mouseRef.current.x - uniformsRef.current.uMouse.value.x) * 0.05;
        uniformsRef.current.uMouse.value.y +=
          (mouseRef.current.y - uniformsRef.current.uMouse.value.y) * 0.05;

        // Render
        rendererRef.current.render(sceneRef.current, cameraRef.current);

        frameRef.current = requestAnimationFrame(loop);
      };

      loop();
    },
    []
  );

  // Handle mouse movement
  const handleMouseMove = useCallback((e: MouseEvent) => {
    mouseRef.current.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouseRef.current.y = -(e.clientY / window.innerHeight) * 2 + 1;
  }, []);

  // Handle resize
  const handleResize = useCallback(() => {
    if (!cameraRef.current || !rendererRef.current) return;

    cameraRef.current.aspect = window.innerWidth / window.innerHeight;
    cameraRef.current.updateProjectionMatrix();
    rendererRef.current.setSize(window.innerWidth, window.innerHeight);
  }, []);

  // Setup and cleanup
  useEffect(() => {
    const refs = initScene();
    if (!refs) return;

    const { systemsGroup, lineGroup } = refs;

    // Start animation
    animate(systemsGroup, lineGroup);

    // Event listeners
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);

      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }

      if (rendererRef.current && containerRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement);
        rendererRef.current.dispose();
      }
    };
  }, [initScene, animate, handleMouseMove, handleResize]);

  return (
    <>
      {/* Grid Overlay */}
      <div
        className="absolute inset-0 pointer-events-none grid-overlay z-0 mix-blend-multiply opacity-60"
        aria-hidden="true"
      />
      {/* Three.js Canvas Container */}
      <div
        ref={containerRef}
        className={`absolute inset-0 z-0 ${className}`}
        style={{ opacity }}
        aria-hidden="true"
      />
    </>
  );
};

export default ParticleBackground;
