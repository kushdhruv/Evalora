// web/src/components/home/CausalCanvas3D.tsx - Interactive 3D Causal Constellation (Three.js)

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface CausalCanvas3DProps {
  theme: 'dark' | 'light';
  onNodeClick?: (label: string) => void;
}

export function CausalCanvas3D({ theme, onNodeClick }: CausalCanvas3DProps) {
  const mountRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // Dimensions
    let width = container.clientWidth || 800;
    let height = container.clientHeight || 500;

    // 1. Scene & Camera
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 22);

    // 2. Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    // 3. Lighting (Soothing ambient + multi-tone directional)
    const isDark = theme === 'dark';
    const ambientLight = new THREE.AmbientLight(
      isDark ? 0x222730 : 0xf1f3f7,
      isDark ? 1.4 : 2.0
    );
    scene.add(ambientLight);

    // Key light (soft soothing sky)
    const keyLight = new THREE.DirectionalLight(isDark ? 0x93c5fd : 0x60a5fa, 1.8);
    keyLight.position.set(10, 15, 15);
    scene.add(keyLight);

    // Fill light (soft soothing lavender)
    const fillLight = new THREE.DirectionalLight(isDark ? 0xc084fc : 0xa855f7, 1.4);
    fillLight.position.set(-12, -8, 10);
    scene.add(fillLight);

    // Rim light (soft warm pearl / mint)
    const rimLight = new THREE.DirectionalLight(isDark ? 0x6ee7b7 : 0x34d399, 1.2);
    rimLight.position.set(0, -15, -10);
    scene.add(rimLight);

    // 4. Node Definitions (Autonomous Agent Trajectory Topology)
    interface NodeDef {
      id: string;
      label: string;
      type: 'plan' | 'tool' | 'memory' | 'outcome';
      position: THREE.Vector3;
      color: number;
      size: number;
    }

    const nodeDefs: NodeDef[] = [
      {
        id: 'n-plan',
        label: 'Step 1: Planning & Intent Parsing',
        type: 'plan',
        position: new THREE.Vector3(-6.5, 2.5, 0),
        color: isDark ? 0x60a5fa : 0x2563eb,
        size: 0.95,
      },
      {
        id: 'n-mem-1',
        label: 'Step 2: Long-Horizon Context Memory',
        type: 'memory',
        position: new THREE.Vector3(-2.8, -2.2, 1.5),
        color: isDark ? 0xa78bfa : 0x7c3aed,
        size: 0.85,
      },
      {
        id: 'n-tool-1',
        label: 'Step 3: SQLite Customer Query Tool',
        type: 'tool',
        position: new THREE.Vector3(0.5, 3.2, -1.2),
        color: isDark ? 0xfbbf24 : 0xd97706,
        size: 0.9,
      },
      {
        id: 'n-tool-2',
        label: 'Step 4: Billing Dispatch Service',
        type: 'tool',
        position: new THREE.Vector3(4.2, -1.5, 0.8),
        color: isDark ? 0x34d399 : 0x059669,
        size: 0.88,
      },
      {
        id: 'n-outcome',
        label: 'Step 5: Verified Synthesis & Gating',
        type: 'outcome',
        position: new THREE.Vector3(7.2, 2.0, -0.5),
        color: isDark ? 0x38bdf8 : 0x0284c7,
        size: 1.05,
      },
    ];

    // Node Meshes Group
    const nodeGroup = new THREE.Group();
    scene.add(nodeGroup);

    const nodeMeshes: { mesh: THREE.Mesh; halo: THREE.Mesh; def: NodeDef }[] = [];

    nodeDefs.forEach((def) => {
      // Core Node Geometry (Polished crystalline icosahedron)
      const geom = new THREE.IcosahedronGeometry(def.size, 2);
      const mat = new THREE.MeshPhysicalMaterial({
        color: def.color,
        metalness: 0.15,
        roughness: 0.25,
        clearcoat: 0.8,
        clearcoatRoughness: 0.1,
        transmission: isDark ? 0.2 : 0.05,
        transparent: true,
        opacity: 0.95,
      });

      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.copy(def.position);
      nodeGroup.add(mesh);

      // Subtle Outer Halo Ring
      const ringGeom = new THREE.TorusGeometry(def.size * 1.35, 0.025, 16, 64);
      const ringMat = new THREE.MeshBasicMaterial({
        color: def.color,
        transparent: true,
        opacity: isDark ? 0.35 : 0.25,
      });
      const halo = new THREE.Mesh(ringGeom, ringMat);
      halo.position.copy(def.position);
      halo.rotation.x = Math.PI / 3;
      nodeGroup.add(halo);

      nodeMeshes.push({ mesh, halo, def });
    });

    // 5. Causal Curves (Smooth Bézier trajectory connections)
    const curveConnections = [
      [nodeDefs[0], nodeDefs[1]],
      [nodeDefs[0], nodeDefs[2]],
      [nodeDefs[1], nodeDefs[2]],
      [nodeDefs[2], nodeDefs[3]],
      [nodeDefs[3], nodeDefs[4]],
      [nodeDefs[2], nodeDefs[4]],
    ];

    const curves: THREE.CatmullRomCurve3[] = [];
    const curveMeshes: THREE.Line[] = [];

    curveConnections.forEach(([start, end]) => {
      // Compute subtle curved mid-point
      const mid = new THREE.Vector3()
        .addVectors(start.position, end.position)
        .multiplyScalar(0.5);
      mid.y += (Math.random() - 0.5) * 1.5;
      mid.z += (Math.random() - 0.5) * 1.5;

      const curve = new THREE.CatmullRomCurve3([start.position, mid, end.position]);
      curves.push(curve);

      const points = curve.getPoints(50);
      const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: isDark ? 0x475569 : 0xc7d2fe,
        transparent: true,
        opacity: isDark ? 0.5 : 0.65,
        linewidth: 1.5,
      });

      const line = new THREE.Line(lineGeom, lineMat);
      scene.add(line);
      curveMeshes.push(line);
    });

    // 6. Traveling Energy Packets (Telemetry Pulses)
    const packetCount = 12;
    const packetGeom = new THREE.SphereGeometry(0.12, 16, 16);
    const packetMat = new THREE.MeshBasicMaterial({
      color: isDark ? 0xffffff : 0x1e293b,
    });

    const packets: { mesh: THREE.Mesh; curveIndex: number; progress: number; speed: number }[] = [];

    for (let i = 0; i < packetCount; i++) {
      const mesh = new THREE.Mesh(packetGeom, packetMat.clone());
      const curveIndex = i % curves.length;
      scene.add(mesh);
      packets.push({
        mesh,
        curveIndex,
        progress: Math.random(),
        speed: 0.003 + Math.random() * 0.003,
      });
    }

    // 7. Ambient Floating Background Stardust Dust
    const particleCount = 160;
    const particleGeom = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      particlePositions[i] = (Math.random() - 0.5) * 28;
      particlePositions[i + 1] = (Math.random() - 0.5) * 20;
      particlePositions[i + 2] = (Math.random() - 0.5) * 15;
    }

    particleGeom.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.08,
      color: isDark ? 0x94a3b8 : 0x64748b,
      transparent: true,
      opacity: isDark ? 0.35 : 0.25,
    });
    const particleSystem = new THREE.Points(particleGeom, particleMat);
    scene.add(particleSystem);

    // 8. Mouse Interaction & Parallax Tracking
    let targetRotationX = 0;
    let targetRotationY = 0;
    let mouseX = 0;
    let mouseY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const rect = container.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width) * 2 - 1;
      mouseY = -(((e.clientY - rect.top) / height) * 2 - 1);

      targetRotationY = mouseX * 0.35;
      targetRotationX = -mouseY * 0.25;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // 9. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth camera interpolation towards mouse target
      scene.rotation.y += (targetRotationY - scene.rotation.y) * 0.05;
      scene.rotation.x += (targetRotationX - scene.rotation.x) * 0.05;

      // Gentle organic node breathing and rotation
      nodeMeshes.forEach(({ mesh, halo }, idx) => {
        mesh.rotation.y = elapsed * 0.4 + idx;
        mesh.rotation.x = elapsed * 0.2 + idx;
        halo.rotation.z = elapsed * 0.3 + idx;
        mesh.position.y += Math.sin(elapsed * 1.5 + idx * 1.2) * 0.002;
      });

      // Advance telemetry energy packets along Bézier paths
      packets.forEach((p) => {
        p.progress += p.speed;
        if (p.progress >= 1) {
          p.progress = 0;
          p.curveIndex = (p.curveIndex + 1) % curves.length;
        }
        const point = curves[p.curveIndex].getPointAt(p.progress);
        if (point) {
          p.mesh.position.copy(point);
        }
      });

      // Subtle particles drift
      particleSystem.rotation.y = elapsed * 0.03;

      renderer.render(scene, camera);
    };

    animate();

    // 10. Responsive Resize Observer
    const handleResize = () => {
      if (!container) return;
      width = container.clientWidth;
      height = container.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('resize', handleResize);
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [theme]);

  return (
    <div
      ref={mountRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'absolute',
        top: 0,
        left: 0,
        pointerEvents: 'none',
        zIndex: 1,
      }}
    />
  );
}
