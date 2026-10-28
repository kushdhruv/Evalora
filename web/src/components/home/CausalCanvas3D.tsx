// web/src/components/home/CausalCanvas3D.tsx - 3D Autonomous AI Agent Robots Constellation (Three.js)

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

    // 1. Scene & Camera (Positioned for panoramic widescreen view)
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 24);

    // 2. High-Performance Antialiased WebGL Renderer
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.2;
    container.appendChild(renderer.domElement);

    // 3. Multi-Tone Atmospheric Lighting
    const isDark = theme === 'dark';
    const ambientLight = new THREE.AmbientLight(
      isDark ? 0x1a1e27 : 0xf8fafc,
      isDark ? 1.8 : 2.4
    );
    scene.add(ambientLight);

    // Key directional light (soothing cobalt blue)
    const keyLight = new THREE.DirectionalLight(isDark ? 0x93c5fd : 0x3b82f6, isDark ? 2.5 : 2.0);
    keyLight.position.set(16, 20, 18);
    scene.add(keyLight);

    // Fill light (warm lavender / amethyst)
    const fillLight = new THREE.DirectionalLight(isDark ? 0xc4b5fd : 0x8b5cf6, isDark ? 2.0 : 1.5);
    fillLight.position.set(-18, -10, 14);
    scene.add(fillLight);

    // Rim light (clean emerald / mint)
    const rimLight = new THREE.DirectionalLight(isDark ? 0x6ee7b7 : 0x10b981, isDark ? 1.8 : 1.3);
    rimLight.position.set(0, -18, -12);
    scene.add(rimLight);

    // 4. Procedural Soft Rounded Humanoid AI Agent Bot Builders
    // Base Soft Porcelain / Satin Tech Materials
    const bodyMat = new THREE.MeshPhysicalMaterial({
      color: isDark ? 0x222736 : 0xf1f5f9,
      metalness: 0.1,
      roughness: 0.22,
      clearcoat: 0.75,
      clearcoatRoughness: 0.12,
    });

    const glossyVisorMat = new THREE.MeshPhysicalMaterial({
      color: isDark ? 0x090d16 : 0x0f172a,
      metalness: 0.1,
      roughness: 0.05,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
    });

    const jointMat = new THREE.MeshPhysicalMaterial({
      color: isDark ? 0x161a24 : 0xe2e8f0,
      metalness: 0.3,
      roughness: 0.35,
    });

    // Robot Tracking Interface
    interface RobotEntry {
      group: THREE.Group;
      head?: THREE.Object3D;
      wavingArm?: THREE.Object3D;
      rotatingParts?: THREE.Object3D[];
      floatingParts?: { obj: THREE.Object3D; speed: number; amp: number; offset: number }[];
      basePos: THREE.Vector3;
      bobSpeed: number;
      bobAmp: number;
      phase: number;
    }

    const robots: RobotEntry[] = [];
    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // Shared Helper: Build Soft Rounded Humanoid Base (Head, Visor, Torso, Arms, Legs)
    function buildHumanoidBase(
      accentColor: number,
      headAccessories?: (head: THREE.Group, accMat: THREE.Material, glwMat: THREE.Material) => void,
      bodyAccessories?: (body: THREE.Group, accMat: THREE.Material, glwMat: THREE.Material) => void
    ) {
      const g = new THREE.Group();

      const accentMat = new THREE.MeshBasicMaterial({ color: accentColor });
      const glowMat = new THREE.MeshBasicMaterial({
        color: accentColor,
        transparent: true,
        opacity: isDark ? 0.35 : 0.25,
      });

      // 1. Soft Rounded Torso (Capsule body with gentle curves)
      const torsoGeom = new THREE.CapsuleGeometry(0.72, 0.75, 16, 32);
      const torso = new THREE.Mesh(torsoGeom, bodyMat);
      g.add(torso);

      // Soft Glowing Chest Heart Core (Rounded pill badge)
      const coreGeom = new THREE.CapsuleGeometry(0.12, 0.26, 12, 24);
      coreGeom.rotateZ(Math.PI / 2);
      const core = new THREE.Mesh(coreGeom, accentMat);
      core.position.set(0, 0.15, 0.7);
      g.add(core);

      // Back Jetpack / Memory Battery
      const packGeom = new THREE.CapsuleGeometry(0.32, 0.5, 12, 24);
      const pack = new THREE.Mesh(packGeom, jointMat);
      pack.position.set(0, 0.1, -0.65);
      g.add(pack);

      // 2. Neck Joint
      const neckGeom = new THREE.CylinderGeometry(0.28, 0.32, 0.25, 24);
      const neck = new THREE.Mesh(neckGeom, jointMat);
      neck.position.y = 0.85;
      g.add(neck);

      // 3. Soft Rounded Head Group
      const headGroup = new THREE.Group();
      headGroup.position.y = 1.6;

      // Smooth Rounded Head Helmet (Egg/Capsule)
      const headGeom = new THREE.SphereGeometry(0.78, 32, 32);
      headGeom.scale(1, 1.05, 0.96);
      const head = new THREE.Mesh(headGeom, bodyMat);
      headGroup.add(head);

      // Glossy Curved Face Visor
      const visorGeom = new THREE.CapsuleGeometry(0.38, 0.42, 16, 32);
      visorGeom.rotateZ(Math.PI / 2);
      const visor = new THREE.Mesh(visorGeom, glossyVisorMat);
      visor.position.set(0, 0.05, 0.52);
      visor.scale.set(1.1, 0.78, 0.6);
      headGroup.add(visor);

      // Expressive Glowing Rounded Digital LED Eyes
      [-0.22, 0.22].forEach((xSide) => {
        const eyeGeom = new THREE.CapsuleGeometry(0.065, 0.11, 8, 16);
        const eye = new THREE.Mesh(eyeGeom, accentMat);
        eye.position.set(xSide, 0.07, 0.76);
        eye.rotation.z = xSide > 0 ? -0.08 : 0.08;
        headGroup.add(eye);
      });

      // Cute Rounded Ear Muff Sensors (Left and Right)
      [-0.82, 0.82].forEach((xSide) => {
        const muffGeom = new THREE.CylinderGeometry(0.24, 0.24, 0.14, 24);
        muffGeom.rotateZ(Math.PI / 2);
        const muff = new THREE.Mesh(muffGeom, jointMat);
        muff.position.set(xSide, 0.05, 0);
        headGroup.add(muff);

        // Accent Ring on Ear Muff
        const ringGeom = new THREE.TorusGeometry(0.16, 0.04, 16, 24);
        ringGeom.rotateY(Math.PI / 2);
        const ring = new THREE.Mesh(ringGeom, accentMat);
        ring.position.set(xSide > 0 ? xSide + 0.08 : xSide - 0.08, 0.05, 0);
        headGroup.add(ring);
      });

      if (headAccessories) {
        headAccessories(headGroup, accentMat, glowMat);
      }
      g.add(headGroup);

      // 4. Humanoid Dangler Legs with Rounded Booties
      [-0.34, 0.34].forEach((xSide) => {
        const legGroup = new THREE.Group();
        legGroup.position.set(xSide, -0.75, 0);

        // Soft Capsule Leg
        const legGeom = new THREE.CapsuleGeometry(0.16, 0.46, 12, 24);
        const leg = new THREE.Mesh(legGeom, bodyMat);
        leg.position.y = -0.32;
        legGroup.add(leg);

        // Rounded Bootie / Foot
        const bootGeom = new THREE.CapsuleGeometry(0.18, 0.28, 12, 24);
        bootGeom.rotateX(Math.PI / 2);
        const boot = new THREE.Mesh(bootGeom, jointMat);
        boot.position.set(0, -0.65, 0.1);
        legGroup.add(boot);

        // Glowing Sole Light
        const soleGeom = new THREE.CylinderGeometry(0.12, 0.12, 0.04, 16);
        const sole = new THREE.Mesh(soleGeom, accentMat);
        sole.position.set(0, -0.8, 0.1);
        legGroup.add(sole);

        g.add(legGroup);
      });

      // 5. Default Humanoid Arms & Mitten Hands
      const leftArmGroup = new THREE.Group();
      leftArmGroup.position.set(-0.95, 0.3, 0);

      const leftArmGeom = new THREE.CapsuleGeometry(0.14, 0.52, 12, 24);
      const leftArm = new THREE.Mesh(leftArmGeom, bodyMat);
      leftArm.position.y = -0.32;
      leftArm.rotation.z = -0.15;
      leftArmGroup.add(leftArm);

      const leftHand = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), jointMat);
      leftHand.position.set(0, -0.7, 0);
      leftArmGroup.add(leftHand);

      g.add(leftArmGroup);

      const rightArmGroup = new THREE.Group();
      rightArmGroup.position.set(0.95, 0.3, 0);

      const rightArmGeom = new THREE.CapsuleGeometry(0.14, 0.52, 12, 24);
      const rightArm = new THREE.Mesh(rightArmGeom, bodyMat);
      rightArm.position.y = -0.32;
      rightArm.rotation.z = 0.15;
      rightArmGroup.add(rightArm);

      const rightHand = new THREE.Mesh(new THREE.SphereGeometry(0.18, 16, 16), jointMat);
      rightHand.position.set(0, -0.7, 0);
      rightArmGroup.add(rightHand);

      g.add(rightArmGroup);

      if (bodyAccessories) {
        bodyAccessories(g, accentMat, glowMat);
      }

      return {
        group: g,
        head: headGroup,
        leftArm: leftArmGroup,
        rightArm: rightArmGroup,
        accentMat,
        glowMat,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 1: "ARIA" - THE CHIEF PLANNER (Cyan) - Top Left
    // Soft Humanoid Android with cute antenna orb & friendly waving hand
    // -------------------------------------------------------------------------
    function buildPlannerAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(-12.8, 3.8, 0.8);
      const accent = isDark ? 0x38bdf8 : 0x0284c7;

      const { group, head, rightArm } = buildHumanoidBase(
        accent,
        // Head accessory: Sleek curved soft antenna with glowing pulse orb
        (h, accMat) => {
          const antPole = new THREE.Mesh(
            new THREE.CylinderGeometry(0.04, 0.04, 0.5, 12),
            jointMat
          );
          antPole.position.set(0, 0.95, 0);
          h.add(antPole);

          const antOrb = new THREE.Mesh(
            new THREE.SphereGeometry(0.15, 16, 16),
            accMat
          );
          antOrb.position.set(0, 1.25, 0);
          h.add(antOrb);
        },
        // Body accessory: Floating strategy halo
        (b, _accMat, glwMat) => {
          const halo = new THREE.Mesh(
            new THREE.TorusGeometry(1.35, 0.035, 16, 64),
            glwMat
          );
          halo.rotation.x = Math.PI / 2.6;
          halo.position.y = 1.4;
          b.add(halo);
        }
      );

      group.position.copy(basePos);
      group.rotation.y = 0.35; // Turn gently toward center

      // Pose: Right arm raised up in a friendly wave gesture
      rightArm.position.set(0.9, 0.45, 0.15);
      rightArm.rotation.z = 2.3; // Waving upwards!
      rightArm.rotation.x = 0.25;

      mainGroup.add(group);

      return {
        group,
        head,
        wavingArm: rightArm,
        basePos,
        bobSpeed: 1.1,
        bobAmp: 0.22,
        phase: 0,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 2: "ECHO" - THE MEMORY SENTINEL (Lavender) - Bottom Left
    // Soft Chubby Explorer Avatar cradling a glowing memory pearl with orbital rings
    // -------------------------------------------------------------------------
    function buildMemorySentinelAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(-11.5, -3.8, 1.8);
      const accent = isDark ? 0xc084fc : 0x7c3aed;

      const floatingParts: any[] = [];
      const rotatingParts: THREE.Object3D[] = [];

      const { group, head, leftArm, rightArm } = buildHumanoidBase(
        accent,
        // Head accessory: Cute rounded visor with purple glowing cat/smile curved eyes
        (h, accMat) => {
          // Soft rounded floating crown ring above head
          const crown = new THREE.Mesh(
            new THREE.TorusGeometry(0.95, 0.03, 16, 48),
            accMat
          );
          crown.rotation.x = Math.PI / 2.3;
          crown.position.y = 1.05;
          h.add(crown);
          rotatingParts.push(crown);
        },
        // Body accessory: Dual floating soft orbital rings
        (b, accMat) => {
          const ringGroup = new THREE.Group();
          const ring1 = new THREE.Mesh(
            new THREE.TorusGeometry(1.6, 0.045, 16, 64),
            accMat
          );
          ring1.rotation.x = Math.PI / 3;
          ringGroup.add(ring1);

          const ring2 = new THREE.Mesh(
            new THREE.TorusGeometry(1.7, 0.03, 16, 64),
            bodyMat
          );
          ring2.rotation.y = Math.PI / 2.8;
          ringGroup.add(ring2);

          b.add(ringGroup);
          rotatingParts.push(ringGroup);
        }
      );

      group.position.copy(basePos);
      group.rotation.y = 0.45;

      // Pose: Both arms cradling forward holding a glowing floating memory crystal pearl
      leftArm.position.set(-0.65, 0.0, 0.45);
      leftArm.rotation.x = 0.85;
      leftArm.rotation.z = 0.45;

      rightArm.position.set(0.65, 0.0, 0.45);
      rightArm.rotation.x = 0.85;
      rightArm.rotation.z = -0.45;

      // Floating Memory Pearl hovering between hands
      const pearl = new THREE.Mesh(
        new THREE.SphereGeometry(0.32, 24, 24),
        new THREE.MeshBasicMaterial({ color: isDark ? 0xe9d5ff : 0x6b21a8 })
      );
      pearl.position.set(0, 0.1, 0.95);
      group.add(pearl);
      floatingParts.push({ obj: pearl, speed: 2.2, amp: 0.12, offset: 0 });

      mainGroup.add(group);

      return {
        group,
        head,
        rotatingParts,
        floatingParts,
        basePos,
        bobSpeed: 0.95,
        bobAmp: 0.25,
        phase: 1.2,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 3: "NOVA" - THE GUARDIAN JUDGE (Emerald) - Top Right
    // Regal Soft Humanoid Bot with floating rounded emerald wings & halo
    // -------------------------------------------------------------------------
    function buildJudgeGuardianAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(12.8, 3.6, 0.8);
      const accent = isDark ? 0x34d399 : 0x059669;

      const floatingParts: any[] = [];
      const rotatingParts: THREE.Object3D[] = [];

      const { group, head } = buildHumanoidBase(
        accent,
        // Head accessory: Emerald crest halo
        (h, accMat) => {
          const halo = new THREE.Mesh(
            new THREE.TorusGeometry(1.1, 0.04, 16, 48),
            accMat
          );
          halo.rotation.x = Math.PI / 2.4;
          halo.position.set(0, 0.3, -0.3);
          h.add(halo);
          rotatingParts.push(halo);
        },
        // Body accessory: Floating soft rounded energy wing cushions
        (b, accMat) => {
          [-1.5, 1.5].forEach((xSide, i) => {
            const wingGroup = new THREE.Group();
            wingGroup.position.set(xSide, 0.4, -0.2);

            // Soft curved wing capsule
            const wingGeom = new THREE.CapsuleGeometry(0.22, 1.4, 12, 24);
            const wing = new THREE.Mesh(wingGeom, bodyMat);
            wing.rotation.z = xSide > 0 ? -0.35 : 0.35;
            wingGroup.add(wing);

            // Glowing inner energy capsule
            const innerGeom = new THREE.CapsuleGeometry(0.1, 1.1, 8, 16);
            const inner = new THREE.Mesh(innerGeom, accMat);
            inner.rotation.z = xSide > 0 ? -0.35 : 0.35;
            inner.position.x = xSide > 0 ? -0.08 : 0.08;
            wingGroup.add(inner);

            b.add(wingGroup);
            floatingParts.push({ obj: wingGroup, speed: 1.8, amp: 0.15, offset: i * Math.PI });
          });

          // Floating evaluation shield orb
          const shield = new THREE.Mesh(
            new THREE.TorusGeometry(0.42, 0.05, 16, 32),
            accMat
          );
          shield.position.set(0, 0.2, 0.85);
          b.add(shield);
          floatingParts.push({ obj: shield, speed: 1.5, amp: 0.1, offset: 1.0 });
        }
      );

      group.position.copy(basePos);
      group.rotation.y = -0.4; // Face center

      mainGroup.add(group);

      return {
        group,
        head,
        rotatingParts,
        floatingParts,
        basePos,
        bobSpeed: 1.15,
        bobAmp: 0.26,
        phase: 0.6,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 4: "BYTE" - THE TOOL CRAFTER (Amber / Gold) - Bottom Right
    // Cute engineer bot with round goggle rims & floating interactive data tablet
    // -------------------------------------------------------------------------
    function buildToolOperatorAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(11.5, -4.0, 1.8);
      const accent = isDark ? 0xfbbf24 : 0xd97706;

      const floatingParts: any[] = [];

      const { group, head, leftArm, rightArm } = buildHumanoidBase(
        accent,
        // Head accessory: Rounded dual goggles over forehead
        (h, accMat) => {
          [-0.28, 0.28].forEach((xSide) => {
            const goggleGeom = new THREE.TorusGeometry(0.18, 0.05, 16, 24);
            const goggle = new THREE.Mesh(goggleGeom, jointMat);
            goggle.position.set(xSide, 0.4, 0.58);
            h.add(goggle);

            const lens = new THREE.Mesh(
              new THREE.SphereGeometry(0.14, 16, 16),
              accMat
            );
            lens.position.set(xSide, 0.4, 0.58);
            h.add(lens);
          });
        },
        // Body accessory: Floating holographic tool cube
        (b, accMat) => {
          const toolCube = new THREE.Mesh(
            new THREE.BoxGeometry(0.45, 0.45, 0.45),
            accMat
          );
          toolCube.position.set(-0.2, 0.1, 0.95);
          toolCube.rotation.set(0.4, 0.5, 0.2);
          b.add(toolCube);
          floatingParts.push({ obj: toolCube, speed: 1.7, amp: 0.12, offset: 0.8 });
        }
      );

      group.position.copy(basePos);
      group.rotation.y = -0.45;

      // Pose: Holding hands up interacting with floating tool cube
      leftArm.position.set(-0.7, 0.1, 0.35);
      leftArm.rotation.x = 0.65;
      rightArm.position.set(0.7, 0.1, 0.35);
      rightArm.rotation.x = 0.65;

      mainGroup.add(group);

      return {
        group,
        head,
        floatingParts,
        basePos,
        bobSpeed: 1.05,
        bobAmp: 0.22,
        phase: 2.1,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 5: "KIP" - THE DETECTIVE TRACER (Coral / Ruby) - Lower Mid-Right
    // Cute curious scout bot with bobbing antenna & floating holographic scanner
    // -------------------------------------------------------------------------
    function buildDetectiveAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(7.2, -6.6, -0.8);
      const accent = isDark ? 0xfb7185 : 0xe11d48;

      const floatingParts: any[] = [];

      const { group, head } = buildHumanoidBase(
        accent,
        // Head accessory: Springy cute bent antenna with ruby orb
        (h, accMat) => {
          const antStem = new THREE.Mesh(
            new THREE.CylinderGeometry(0.035, 0.035, 0.6, 8),
            jointMat
          );
          antStem.position.set(0.2, 0.95, 0);
          antStem.rotation.z = -0.3;
          h.add(antStem);

          const antLight = new THREE.Mesh(
            new THREE.SphereGeometry(0.13, 16, 16),
            accMat
          );
          antLight.position.set(0.35, 1.25, 0);
          h.add(antLight);
        },
        // Body accessory: Floating magnifying scan ring in front
        (b, accMat) => {
          const scanRing = new THREE.Mesh(
            new THREE.TorusGeometry(0.38, 0.045, 16, 32),
            accMat
          );
          scanRing.position.set(0.3, 0.3, 0.85);
          scanRing.rotation.y = 0.2;
          b.add(scanRing);
          floatingParts.push({ obj: scanRing, speed: 2.0, amp: 0.1, offset: 1.4 });
        }
      );

      group.position.copy(basePos);
      group.rotation.y = -0.28;

      // Pose: Leaning forward curiously
      head.rotation.z = -0.12;

      mainGroup.add(group);

      return {
        group,
        head,
        floatingParts,
        basePos,
        bobSpeed: 1.35,
        bobAmp: 0.18,
        phase: 3.0,
      };
    }

    // -------------------------------------------------------------------------
    // AVATAR 6: "ZEPHYR" - THE TELEMETRY COURIER (Cobalt / Indigo) - Lower Mid-Left
    // Aerodynamic rounded glider bot with winged ear fins and floating trail
    // -------------------------------------------------------------------------
    function buildCourierAvatar(): RobotEntry {
      const basePos = new THREE.Vector3(-7.2, -6.6, -0.8);
      const accent = isDark ? 0x60a5fa : 0x2563eb;

      const { group, head, leftArm, rightArm } = buildHumanoidBase(
        accent,
        // Head accessory: Sleek rounded ear fins (winged courier headgear)
        (h, accMat) => {
          [-0.85, 0.85].forEach((xSide) => {
            const wingFin = new THREE.Mesh(
              new THREE.CapsuleGeometry(0.08, 0.5, 8, 16),
              accMat
            );
            wingFin.position.set(xSide, 0.35, -0.15);
            wingFin.rotation.x = 0.5;
            wingFin.rotation.z = xSide > 0 ? 0.3 : -0.3;
            h.add(wingFin);
          });
        }
      );

      group.position.copy(basePos);
      group.rotation.y = 0.28;

      // Pose: Streamlined gliding flight posture, arms swept gracefully
      leftArm.rotation.x = -0.45;
      leftArm.rotation.z = -0.35;
      rightArm.rotation.x = -0.45;
      rightArm.rotation.z = 0.35;

      mainGroup.add(group);

      return {
        group,
        head,
        basePos,
        bobSpeed: 1.25,
        bobAmp: 0.17,
        phase: 1.8,
      };
    }

    // Instantiate All 6 Soft Rounded Humanoid Bot Avatars
    robots.push(
      buildPlannerAvatar(),
      buildMemorySentinelAvatar(),
      buildJudgeGuardianAvatar(),
      buildToolOperatorAvatar(),
      buildDetectiveAvatar(),
      buildCourierAvatar()
    );

    // 5. Causal Data Telemetry Splines (Flowing between the 6 Robots)
    const connections: [number, number][] = [
      [0, 1], // Planner -> Memory Sentinel
      [1, 5], // Memory -> Ingest Probe
      [0, 2], // Planner -> Judge Guardian (Top Arch)
      [2, 3], // Judge Guardian -> Tool Operator
      [3, 4], // Tool Operator -> Detective Drone
      [5, 4], // Ingest Probe -> Detective Drone (Bottom Arch)
    ];

    const curves: THREE.CatmullRomCurve3[] = [];

    connections.forEach(([sIdx, eIdx]) => {
      const p1 = robots[sIdx].basePos;
      const p2 = robots[eIdx].basePos;

      const mid = new THREE.Vector3().addVectors(p1, p2).multiplyScalar(0.5);
      if (mid.y > 0) mid.y += 2.5;
      else mid.y -= 2.5;
      mid.z -= 2.0;

      const curve = new THREE.CatmullRomCurve3([p1, mid, p2]);
      curves.push(curve);

      const pts = curve.getPoints(50);
      const lineGeom = new THREE.BufferGeometry().setFromPoints(pts);
      const lineMat = new THREE.LineBasicMaterial({
        color: isDark ? 0x334155 : 0xc7d2fe,
        transparent: true,
        opacity: isDark ? 0.45 : 0.6,
      });

      const line = new THREE.Line(lineGeom, lineMat);
      scene.add(line);
    });

    // 6. Traveling Telemetry Packets
    const packetCount = 18;
    const packetGeom = new THREE.SphereGeometry(0.16, 16, 16);
    const packetMat = new THREE.MeshBasicMaterial({ color: isDark ? 0xffffff : 0x0f172a });

    const packets: { mesh: THREE.Mesh; curveIndex: number; progress: number; speed: number }[] = [];

    for (let i = 0; i < packetCount; i++) {
      const mesh = new THREE.Mesh(packetGeom, packetMat);
      const curveIndex = i % curves.length;
      scene.add(mesh);
      packets.push({
        mesh,
        curveIndex,
        progress: (i / packetCount) % 1,
        speed: 0.003 + Math.random() * 0.002,
      });
    }

    // 7. Ambient Cybernetic Stardust Field
    const starCount = 220;
    const starGeom = new THREE.BufferGeometry();
    const starPos = new Float32Array(starCount * 3);

    for (let i = 0; i < starCount * 3; i += 3) {
      starPos[i] = (Math.random() - 0.5) * 44;
      starPos[i + 1] = (Math.random() - 0.5) * 26;
      starPos[i + 2] = (Math.random() - 0.5) * 16;
    }

    starGeom.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({
      size: 0.08,
      color: isDark ? 0x94a3b8 : 0x64748b,
      transparent: true,
      opacity: isDark ? 0.35 : 0.25,
    });
    const starField = new THREE.Points(starGeom, starMat);
    scene.add(starField);

    // 8. Mouse Parallax & Tracking
    let targetRotX = 0;
    let targetRotY = 0;
    let targetCamX = 0;
    let targetCamY = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const normX = (e.clientX / window.innerWidth) * 2 - 1;
      const normY = -(e.clientY / window.innerHeight) * 2 + 1;

      targetRotY = normX * 0.22;
      targetRotX = -normY * 0.15;
      targetCamX = normX * 1.4;
      targetCamY = normY * 0.9;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // 9. Animation Loop
    let animId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Smooth camera interpolation
      mainGroup.rotation.y += (targetRotY - mainGroup.rotation.y) * 0.04;
      mainGroup.rotation.x += (targetRotX - mainGroup.rotation.x) * 0.04;
      camera.position.x += (targetCamX - camera.position.x) * 0.03;
      camera.position.y += (targetCamY - camera.position.y) * 0.03;

      // Animate Each Robot
      robots.forEach(({ group, head, wavingArm, rotatingParts, floatingParts, basePos, bobSpeed, bobAmp, phase }) => {
        // Organic hover bobbing
        group.position.y = basePos.y + Math.sin(elapsed * bobSpeed + phase) * bobAmp;

        // Head intelligent scanning & curious tilting
        if (head) {
          head.rotation.y = Math.sin(elapsed * 0.7 + phase) * 0.22;
          head.rotation.x = Math.sin(elapsed * 0.5 + phase) * 0.08;
        }

        // Friendly waving arm animation
        if (wavingArm) {
          wavingArm.rotation.z = 2.3 + Math.sin(elapsed * 3.5) * 0.18;
        }

        // Rotating rings, radar dishes, halos
        if (rotatingParts) {
          rotatingParts.forEach((part, idx) => {
            part.rotation.z = elapsed * (0.2 + idx * 0.1);
            part.rotation.y = elapsed * 0.3;
          });
        }

        // Floating floating arms, wings, shoulders
        if (floatingParts) {
          floatingParts.forEach(({ obj, speed, amp, offset }) => {
            obj.position.y = Math.sin(elapsed * speed + offset) * amp;
          });
        }
      });

      // Advance Telemetry Packets along curves
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

      // Starfield subtle drift
      starField.rotation.y = elapsed * 0.015;

      renderer.render(scene, camera);
    };

    animate();

    // 10. Resize Observer
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
      cancelAnimationFrame(animId);
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
