// web/src/components/home/CausalCanvas3D.tsx - Widescreen 3D Planetary Trajectory Constellation (Three.js)

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
    let width = container.clientWidth || window.innerWidth;
    let height = container.clientHeight || 700;

    // 1. Scene & Camera (FOV 45, Positioned for panoramic widescreen view)
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 24);

    // 2. Antialiased WebGL Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    // 3. Soothing Studio Lighting
    const isDark = theme === 'dark';
    const ambientLight = new THREE.AmbientLight(
      isDark ? 0x1e222b : 0xf8fafc,
      isDark ? 1.6 : 2.2
    );
    scene.add(ambientLight);

    // Key directional light (soft soothing sky blue)
    const keyLight = new THREE.DirectionalLight(isDark ? 0x93c5fd : 0x3b82f6, isDark ? 2.2 : 1.8);
    keyLight.position.set(16, 20, 18);
    scene.add(keyLight);

    // Fill light (warm lavender / amethyst)
    const fillLight = new THREE.DirectionalLight(isDark ? 0xc4b5fd : 0x8b5cf6, isDark ? 1.8 : 1.4);
    fillLight.position.set(-18, -10, 14);
    scene.add(fillLight);

    // Rim light (soft soothing mint / pearl)
    const rimLight = new THREE.DirectionalLight(isDark ? 0x6ee7b7 : 0x10b981, isDark ? 1.5 : 1.2);
    rimLight.position.set(0, -18, -12);
    scene.add(rimLight);

    // 4. Widescreen Dispersed Planetary Nodes (Flanking the central reading zone)
    interface NodeDef {
      id: string;
      label: string;
      position: THREE.Vector3;
      color: number;
      size: number;
      ringRadius?: number;
      hasMoon?: boolean;
      moonDist?: number;
      moonSpeed?: number;
    }

    const nodeDefs: NodeDef[] = [
      // --- LEFT FLANK SYSTEM (Deep Left Periphery) ---
      {
        id: 'node-plan-major',
        label: 'Autonomous Planning Core',
        position: new THREE.Vector3(-13.2, 4.2, 0.5),
        color: isDark ? 0x38bdf8 : 0x0284c7,
        size: 2.1,
        ringRadius: 3.2,
        hasMoon: true,
        moonDist: 3.6,
        moonSpeed: 0.9,
      },
      {
        id: 'node-memory-nexus',
        label: 'Long-Horizon Memory Nexus',
        position: new THREE.Vector3(-12.0, -3.8, 2.2),
        color: isDark ? 0xa78bfa : 0x7c3aed,
        size: 1.85,
        ringRadius: 2.7,
        hasMoon: true,
        moonDist: 3.0,
        moonSpeed: -0.7,
      },
      {
        id: 'node-context-satellite',
        label: 'Context Cache & Staleness Guard',
        position: new THREE.Vector3(-7.5, -6.8, -1.2),
        color: isDark ? 0x2dd4bf : 0x0d9488,
        size: 1.25,
      },

      // --- RIGHT FLANK SYSTEM (Deep Right Periphery) ---
      {
        id: 'node-judge-major',
        label: 'CI Quality Gate & Evaluation Judge',
        position: new THREE.Vector3(13.4, 3.8, 0.8),
        color: isDark ? 0x34d399 : 0x059669,
        size: 2.2,
        ringRadius: 3.3,
        hasMoon: true,
        moonDist: 3.8,
        moonSpeed: 0.8,
      },
      {
        id: 'node-tool-engine',
        label: 'Runtime Tool & SQLite Dispatch',
        position: new THREE.Vector3(11.8, -4.2, 2.0),
        color: isDark ? 0xfbbf24 : 0xd97706,
        size: 1.9,
        ringRadius: 2.8,
        hasMoon: true,
        moonDist: 3.2,
        moonSpeed: -0.85,
      },
      {
        id: 'node-blame-satellite',
        label: 'Causal Reverse-Blame Attractor',
        position: new THREE.Vector3(7.8, -6.8, -1.0),
        color: isDark ? 0xfb7185 : 0xe11d48,
        size: 1.25,
      },

      // --- TOP HORIZON BRIDGE (Framing the upper ceiling) ---
      {
        id: 'node-upper-left',
        label: 'Hierarchical Strategy Planner',
        position: new THREE.Vector3(-5.8, 7.2, -2.5),
        color: isDark ? 0x818cf8 : 0x4f46e5,
        size: 1.35,
      },
      {
        id: 'node-upper-right',
        label: 'Telemetry OTLP Ingest Stream',
        position: new THREE.Vector3(5.8, 7.0, -2.2),
        color: isDark ? 0x38bdf8 : 0x0ea5e9,
        size: 1.3,
      },
    ];

    // Groups
    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    interface MeshEntry {
      mesh: THREE.Mesh;
      ring?: THREE.Mesh;
      ring2?: THREE.Mesh;
      moon?: THREE.Mesh;
      def: NodeDef;
      rotSpeedX: number;
      rotSpeedY: number;
    }

    const meshEntries: MeshEntry[] = [];

    nodeDefs.forEach((def) => {
      // 1. Core Sphere / Crystal (Polished, tactile, high-end material)
      const geom = new THREE.IcosahedronGeometry(def.size, 3);
      const mat = new THREE.MeshPhysicalMaterial({
        color: def.color,
        metalness: isDark ? 0.2 : 0.08,
        roughness: isDark ? 0.22 : 0.35,
        clearcoat: 0.9,
        clearcoatRoughness: 0.12,
        transmission: isDark ? 0.25 : 0.05,
        transparent: true,
        opacity: 0.96,
      });

      const mesh = new THREE.Mesh(geom, mat);
      mesh.position.copy(def.position);
      mainGroup.add(mesh);

      let ring: THREE.Mesh | undefined;
      let ring2: THREE.Mesh | undefined;
      let moon: THREE.Mesh | undefined;

      // 2. Elegant Concentric Orbital Rings for Major Planets
      if (def.ringRadius) {
        const ringGeom = new THREE.TorusGeometry(def.ringRadius, 0.035, 16, 100);
        const ringMat = new THREE.MeshBasicMaterial({
          color: def.color,
          transparent: true,
          opacity: isDark ? 0.45 : 0.3,
        });

        ring = new THREE.Mesh(ringGeom, ringMat);
        ring.position.copy(def.position);
        ring.rotation.x = Math.PI / 3.2;
        ring.rotation.y = Math.PI / 8;
        mainGroup.add(ring);

        // Secondary subtle inner ring
        const ring2Geom = new THREE.TorusGeometry(def.ringRadius * 0.8, 0.02, 16, 80);
        const ring2Mat = new THREE.MeshBasicMaterial({
          color: def.color,
          transparent: true,
          opacity: isDark ? 0.25 : 0.18,
        });
        ring2 = new THREE.Mesh(ring2Geom, ring2Mat);
        ring2.position.copy(def.position);
        ring2.rotation.x = -Math.PI / 3.8;
        mainGroup.add(ring2);
      }

      // 3. Orbiting Satellite Moon
      if (def.hasMoon && def.moonDist) {
        const moonGeom = new THREE.IcosahedronGeometry(def.size * 0.24, 2);
        const moonMat = new THREE.MeshPhysicalMaterial({
          color: isDark ? 0xf8fafc : 0x334155,
          metalness: 0.3,
          roughness: 0.3,
          clearcoat: 0.7,
        });
        moon = new THREE.Mesh(moonGeom, moonMat);
        moon.position.set(def.position.x + def.moonDist, def.position.y, def.position.z);
        mainGroup.add(moon);
      }

      meshEntries.push({
        mesh,
        ring,
        ring2,
        moon,
        def,
        rotSpeedX: 0.1 + Math.random() * 0.15,
        rotSpeedY: 0.15 + Math.random() * 0.2,
      });
    });

    // 5. Widescreen Causal Splines (Sweeping curved connection arcs framing the center)
    const connections: [NodeDef, NodeDef][] = [
      // Left flank links
      [nodeDefs[0], nodeDefs[1]],
      [nodeDefs[1], nodeDefs[2]],
      [nodeDefs[0], nodeDefs[6]],

      // Right flank links
      [nodeDefs[3], nodeDefs[4]],
      [nodeDefs[4], nodeDefs[5]],
      [nodeDefs[3], nodeDefs[7]],

      // Panoramic High-Altitude Sweeping Arcs (Connecting the wings above and below the text)
      [nodeDefs[6], nodeDefs[7]], // Top horizon bridge
      [nodeDefs[2], nodeDefs[5]], // Bottom horizon bridge
      [nodeDefs[0], nodeDefs[3]], // Broad upper celestial arc
      [nodeDefs[1], nodeDefs[4]], // Broad lower celestial arc
    ];

    const curves: THREE.CatmullRomCurve3[] = [];

    connections.forEach(([start, end]) => {
      // Calculate a generous arched midpoint that curves around the central text
      const mid = new THREE.Vector3().addVectors(start.position, end.position).multiplyScalar(0.5);

      // Push midpoint outward away from the center (0,0)
      if (mid.y > 0) mid.y += 2.2;
      else mid.y -= 2.2;
      mid.z -= 1.8;

      const curve = new THREE.CatmullRomCurve3([start.position, mid, end.position]);
      curves.push(curve);

      const points = curve.getPoints(60);
      const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
      const lineMat = new THREE.LineBasicMaterial({
        color: isDark ? 0x334155 : 0xc7d2fe,
        transparent: true,
        opacity: isDark ? 0.45 : 0.55,
        linewidth: 1.5,
      });

      const line = new THREE.Line(lineGeom, lineMat);
      scene.add(line);
    });

    // 6. Traveling Telemetry Packets Along the Wide Arcs
    const packetCount = 18;
    const packetGeom = new THREE.SphereGeometry(0.14, 16, 16);
    const packetMat = new THREE.MeshBasicMaterial({
      color: isDark ? 0xffffff : 0x0f172a,
    });

    const packets: { mesh: THREE.Mesh; curveIndex: number; progress: number; speed: number }[] = [];

    for (let i = 0; i < packetCount; i++) {
      const mesh = new THREE.Mesh(packetGeom, packetMat.clone());
      const curveIndex = i % curves.length;
      scene.add(mesh);
      packets.push({
        mesh,
        curveIndex,
        progress: (i / packetCount) % 1,
        speed: 0.0025 + Math.random() * 0.002,
      });
    }

    // 7. Ambient Field of Stardust Floating Across Widescreen
    const starCount = 280;
    const starGeom = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount * 3; i += 3) {
      starPositions[i] = (Math.random() - 0.5) * 44;
      starPositions[i + 1] = (Math.random() - 0.5) * 26;
      starPositions[i + 2] = (Math.random() - 0.5) * 16;
    }

    starGeom.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({
      size: 0.09,
      color: isDark ? 0x94a3b8 : 0x64748b,
      transparent: true,
      opacity: isDark ? 0.4 : 0.3,
    });
    const starField = new THREE.Points(starGeom, starMat);
    scene.add(starField);

    // 8. Mouse Parallax Pan & Tilt
    let targetRotX = 0;
    let targetRotY = 0;
    let targetCamX = 0;
    let targetCamY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const normX = (e.clientX / window.innerWidth) * 2 - 1;
      const normY = -(e.clientY / window.innerHeight) * 2 + 1;

      targetRotY = normX * 0.28;
      targetRotX = -normY * 0.18;
      targetCamX = normX * 1.5;
      targetCamY = normY * 1.0;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // 9. Animation Loop
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth camera & group parallax interpolation
      mainGroup.rotation.y += (targetRotY - mainGroup.rotation.y) * 0.04;
      mainGroup.rotation.x += (targetRotX - mainGroup.rotation.x) * 0.04;
      camera.position.x += (targetCamX - camera.position.x) * 0.03;
      camera.position.y += (targetCamY - camera.position.y) * 0.03;

      // Planet rotation, breathing, and moon revolutions
      meshEntries.forEach(({ mesh, ring, ring2, moon, def, rotSpeedX, rotSpeedY }) => {
        mesh.rotation.y = elapsed * rotSpeedY;
        mesh.rotation.x = elapsed * rotSpeedX;

        // Subtle vertical floating breath
        mesh.position.y = def.position.y + Math.sin(elapsed * 1.2 + def.position.x) * 0.18;

        if (ring) {
          ring.position.y = mesh.position.y;
          ring.rotation.z = elapsed * 0.15;
        }

        if (ring2) {
          ring2.position.y = mesh.position.y;
          ring2.rotation.z = -elapsed * 0.18;
        }

        if (moon && def.moonDist && def.moonSpeed) {
          const angle = elapsed * def.moonSpeed;
          moon.position.x = mesh.position.x + Math.cos(angle) * def.moonDist;
          moon.position.z = mesh.position.z + Math.sin(angle) * def.moonDist;
          moon.position.y = mesh.position.y + Math.sin(angle * 1.5) * 0.6;
          moon.rotation.y = elapsed * 0.8;
        }
      });

      // Advance energy packets along the sweeping arcs
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

      // Subtle starfield drift
      starField.rotation.y = elapsed * 0.015;

      renderer.render(scene, camera);
    };

    animate();

    // 10. Resize Handling
    const handleResize = () => {
      if (!container) return;
      width = container.clientWidth || window.innerWidth;
      height = container.clientHeight || 700;
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
