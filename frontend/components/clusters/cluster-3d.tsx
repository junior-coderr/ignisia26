"use client";

import { useRef, useState, useMemo, useCallback, useEffect } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Stars } from "@react-three/drei";
import * as THREE from "three";

import type { ClusterGroup } from "@/lib/types";

// ── Band config ─────────────────────────────────────────────────────────────

const BAND_COLORS: Record<string, string> = {
  excellent: "#22c55e",
  good: "#3b82f6",
  average: "#f59e0b",
  poor: "#ef4444",
};

const BAND_LABELS: Record<string, string> = {
  excellent: "Excellent",
  good: "Good",
  average: "Average",
  poor: "Needs Improvement",
};

const BAND_ORDER = ["excellent", "good", "average", "poor"];

function getBandHex(kind?: string): string {
  return BAND_COLORS[kind ?? ""] ?? "#ef4444";
}

// ── Deterministic hash ──────────────────────────────────────────────────────

function hashStr(str: string): number {
  let h = 5381;
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h + str.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

// ── Types ───────────────────────────────────────────────────────────────────

interface SNode {
  id: string;
  name: string;
  roll: string;
  score: number;
  maxMarks: number;
  ratio: number;
  band: string;
  pos: [number, number, number];
  color: string;
  matched: string[];
  missed: string[];
}

// ── Student sphere ──────────────────────────────────────────────────────────

function Sphere({
  node, selected, hovered, onSelect, onHover, onLeave,
}: {
  node: SNode; selected: boolean; hovered: boolean;
  onSelect: () => void; onHover: () => void; onLeave: () => void;
}) {
  const ref = useRef<THREE.Mesh>(null!);
  const base = 0.3 + node.ratio * 0.25;
  const target = selected ? base * 1.6 : hovered ? base * 1.3 : base;
  const offset = useMemo(() => hashStr(node.id) * 0.1, [node.id]);

  useFrame((_, dt) => {
    if (!ref.current) return;
    const s = ref.current.scale.x;
    ref.current.scale.setScalar(s + (target - s) * Math.min(dt * 8, 1));
    ref.current.position.y = node.pos[1] + Math.sin(Date.now() * 0.001 + offset) * 0.06;
  });

  return (
    <mesh
      ref={ref}
      position={new THREE.Vector3(...node.pos)}
      onClick={(e) => { e.stopPropagation(); onSelect(); }}
      onPointerOver={(e) => { e.stopPropagation(); onHover(); document.body.style.cursor = "pointer"; }}
      onPointerOut={() => { onLeave(); document.body.style.cursor = "auto"; }}
    >
      <sphereGeometry args={[1, 32, 32]} />
      <meshStandardMaterial
        color={node.color}
        emissive={new THREE.Color(node.color)}
        emissiveIntensity={selected ? 0.5 : hovered ? 0.3 : 0.1}
        roughness={0.35}
        metalness={0.15}
        transparent
        opacity={selected ? 1 : 0.82}
      />
      {(hovered || selected) && (
        <Html distanceFactor={6} style={{ pointerEvents: "none" }}>
          <div style={{
            background: "rgba(0,0,0,0.88)", color: "#fff", padding: "6px 12px",
            borderRadius: 8, fontSize: 12, fontWeight: 600, whiteSpace: "nowrap",
            border: `2px solid ${node.color}`, transform: "translateY(-30px)",
          }}>
            {node.name}
            <div style={{ fontSize: 10, fontWeight: 400, opacity: 0.75, marginTop: 2 }}>
              {node.roll} · {node.score}/{node.maxMarks}
            </div>
          </div>
        </Html>
      )}
    </mesh>
  );
}

// ── Connection lines ────────────────────────────────────────────────────────

function Lines({ nodes, band }: { nodes: SNode[]; band: string }) {
  const geo = useMemo(() => {
    if (nodes.length < 2) return null;
    const cx = nodes.reduce((s, n) => s + n.pos[0], 0) / nodes.length;
    const cy = nodes.reduce((s, n) => s + n.pos[1], 0) / nodes.length;
    const cz = nodes.reduce((s, n) => s + n.pos[2], 0) / nodes.length;
    const pts: number[] = [];
    nodes.forEach((n) => {
      pts.push(n.pos[0], n.pos[1], n.pos[2], cx, cy, cz);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pts, 3));
    return g;
  }, [nodes]);

  if (!geo) return null;
  return (
    <lineSegments geometry={geo}>
      <lineBasicMaterial color={getBandHex(band)} transparent opacity={0.15} />
    </lineSegments>
  );
}

// ── Band floating label ─────────────────────────────────────────────────────

function BandTag({ pos, label, color, count }: {
  pos: [number, number, number]; label: string; color: string; count: number;
}) {
  return (
    <Html position={new THREE.Vector3(...pos)} center style={{ pointerEvents: "none" }}>
      <div style={{
        color, fontSize: 13, fontWeight: 700, textAlign: "center",
        textShadow: "0 2px 10px rgba(0,0,0,0.8)", opacity: 0.92,
      }}>
        {label}
        <div style={{ fontSize: 10, fontWeight: 400, opacity: 0.65 }}>
          {count} student{count !== 1 ? "s" : ""}
        </div>
      </div>
    </Html>
  );
}

// ── Camera ──────────────────────────────────────────────────────────────────

function Camera() {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(0, 5, 14);
    camera.lookAt(0, 0, 0);
  }, [camera]);
  return null;
}

// ── Build layout ────────────────────────────────────────────────────────────

function layout(clusters: ClusterGroup[]): SNode[] {
  const out: SNode[] = [];
  const regionX: Record<string, number> = { excellent: -5, good: -1.5, average: 2, poor: 5.5 };

  for (const cl of clusters) {
    const band = cl.cluster_kind ?? cl.band_kind ?? "poor";
    const rx = regionX[band] ?? 0;
    const hex = getBandHex(band);
    const students = cl.students ?? [];
    const n = students.length;

    // Compute max_marks from first student
    const first = students[0];
    const maxMarks = first && first.score_ratio > 0
      ? Math.round(first.score / first.score_ratio)
      : 5;

    students.forEach((st, i) => {
      const h = hashStr(st.roll_number || `s${i}`);
      const angle = (i / Math.max(n, 1)) * Math.PI * 2;
      const r = 0.6 + Math.sqrt(i + 1) * 0.35 * (n > 4 ? 1.2 : 0.85);
      const x = rx + Math.cos(angle) * r;
      const z = Math.sin(angle) * r + ((h % 100) / 100 - 0.5) * 0.4;
      const y = ((st.score_ratio ?? 0) - 0.5) * 3 + ((h % 50) / 50 - 0.5) * 0.25;

      out.push({
        id: `${cl.cluster_id}_${st.roll_number}`,
        name: st.name || "Unknown",
        roll: st.roll_number || "?",
        score: st.score ?? 0,
        maxMarks,
        ratio: st.score_ratio ?? 0,
        band,
        pos: [x, y, z],
        color: hex,
        matched: st.matched_concepts ?? [],
        missed: st.missed_concepts ?? [],
      });
    });
  }
  return out;
}

// ── Detail panel ────────────────────────────────────────────────────────────

function Detail({ node, onClose }: { node: SNode; onClose: () => void }) {
  const pct = Math.round(node.ratio * 100);
  return (
    <div style={{
      position: "absolute", top: 16, right: 16, width: 280,
      background: "rgba(10,10,20,0.92)", backdropFilter: "blur(12px)",
      border: `1px solid ${node.color}44`, borderRadius: 16, padding: 20,
      color: "#fff", fontSize: 13, zIndex: 50,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
        <div>
          <div style={{ fontSize: 16, fontWeight: 700 }}>{node.name}</div>
          <div style={{ fontSize: 11, opacity: 0.6, marginTop: 2 }}>{node.roll}</div>
        </div>
        <button onClick={onClose} style={{
          background: "rgba(255,255,255,0.1)", border: "none", color: "#fff",
          borderRadius: 8, width: 28, height: 28, cursor: "pointer", fontSize: 14,
        }}>✕</button>
      </div>

      <div style={{ marginTop: 14, display: "flex", gap: 12, alignItems: "center" }}>
        <div style={{ fontSize: 28, fontWeight: 800, color: node.color }}>
          {node.score}/{node.maxMarks}
        </div>
        <div>
          <div style={{
            display: "inline-block", background: `${node.color}22`, color: node.color,
            border: `1px solid ${node.color}44`, padding: "2px 10px", borderRadius: 20,
            fontSize: 11, fontWeight: 600,
          }}>{BAND_LABELS[node.band] ?? "Review"}</div>
          <div style={{ fontSize: 11, opacity: 0.5, marginTop: 4 }}>{pct}% score</div>
        </div>
      </div>

      {/* Score bar */}
      <div style={{ marginTop: 12, height: 4, background: "rgba(255,255,255,0.1)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: node.color, borderRadius: 4 }} />
      </div>

      {/* Concepts */}
      {(node.matched.length > 0 || node.missed.length > 0) && (
        <div style={{ marginTop: 14 }}>
          {node.matched.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontSize: 10, opacity: 0.5, marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>Got right</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {node.matched.slice(0, 5).map((c) => (
                  <span key={c} style={{ background: "rgba(34,197,94,0.15)", color: "#22c55e", padding: "2px 8px", borderRadius: 6, fontSize: 10 }}>✓ {c}</span>
                ))}
              </div>
            </div>
          )}
          {node.missed.length > 0 && (
            <div>
              <div style={{ fontSize: 10, opacity: 0.5, marginBottom: 4, textTransform: "uppercase", letterSpacing: 1 }}>Missed</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {node.missed.slice(0, 5).map((c) => (
                  <span key={c} style={{ background: "rgba(239,68,68,0.15)", color: "#ef4444", padding: "2px 8px", borderRadius: 6, fontSize: 10 }}>✗ {c}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Legend ───────────────────────────────────────────────────────────────────

function Legend() {
  return (
    <div style={{
      position: "absolute", bottom: 16, left: 16, display: "flex", gap: 16,
      background: "rgba(10,10,20,0.8)", backdropFilter: "blur(8px)",
      padding: "8px 16px", borderRadius: 12, fontSize: 11, color: "#fff", zIndex: 40,
    }}>
      {BAND_ORDER.map((b) => (
        <div key={b} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: BAND_COLORS[b] }} />
          <span style={{ opacity: 0.8 }}>{BAND_LABELS[b]}</span>
        </div>
      ))}
    </div>
  );
}

// ── Scene content (inside Canvas) ───────────────────────────────────────────

function Scene({
  nodes, bandGroups, bandLabels, selectedId, hoveredId,
  onSelect, onHover, onLeave,
}: {
  nodes: SNode[];
  bandGroups: Record<string, SNode[]>;
  bandLabels: { band: string; pos: [number, number, number]; count: number }[];
  selectedId: string | null;
  hoveredId: string | null;
  onSelect: (id: string) => void;
  onHover: (id: string) => void;
  onLeave: () => void;
}) {
  return (
    <>
      <Camera />
      <ambientLight intensity={0.4} />
      <pointLight position={[10, 10, 10]} intensity={0.8} />
      <pointLight position={[-10, 5, -10]} intensity={0.35} color="#6366f1" />
      <directionalLight position={[0, 8, 4]} intensity={0.45} />

      <Stars radius={30} depth={50} count={600} factor={3} saturation={0.2} fade speed={0.4} />

      {Object.entries(bandGroups).map(([b, g]) => (
        <Lines key={b} nodes={g} band={b} />
      ))}

      {nodes.map((n) => (
        <Sphere
          key={n.id}
          node={n}
          selected={selectedId === n.id}
          hovered={hoveredId === n.id}
          onSelect={() => onSelect(n.id)}
          onHover={() => onHover(n.id)}
          onLeave={onLeave}
        />
      ))}

      {bandLabels.map(({ band, pos, count }) => (
        <BandTag key={band} pos={pos} label={BAND_LABELS[band]} color={BAND_COLORS[band]} count={count} />
      ))}

      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -3.5, 0]}>
        <planeGeometry args={[40, 40]} />
        <meshStandardMaterial color="#0a0a15" transparent opacity={0.3} />
      </mesh>

      <OrbitControls
        enablePan enableZoom enableRotate
        minDistance={5} maxDistance={25}
        autoRotate autoRotateSpeed={0.3}
      />
    </>
  );
}

// ── Main export ─────────────────────────────────────────────────────────────

export default function ClusterVisualization3D({ clusters }: { clusters: ClusterGroup[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const nodes = useMemo(() => layout(clusters), [clusters]);

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedId) ?? null,
    [nodes, selectedId],
  );

  const bandGroups = useMemo(() => {
    const g: Record<string, SNode[]> = {};
    nodes.forEach((n) => { (g[n.band] ??= []).push(n); });
    return g;
  }, [nodes]);

  const bandLabels = useMemo(() => {
    const rX: Record<string, number> = { excellent: -5, good: -1.5, average: 2, poor: 5.5 };
    return BAND_ORDER
      .filter((b) => bandGroups[b]?.length)
      .map((b) => {
        const g = bandGroups[b]!;
        const avgY = g.reduce((s, n) => s + n.pos[1], 0) / g.length;
        return { band: b, pos: [rX[b], avgY + 2.8, 0] as [number, number, number], count: g.length };
      });
  }, [bandGroups]);

  const handleSelect = useCallback((id: string) => {
    setSelectedId((p) => (p === id ? null : id));
  }, []);

  if (nodes.length === 0) {
    return (
      <div style={{ height: 400, display: "flex", alignItems: "center", justifyContent: "center", color: "#888", fontSize: 14 }}>
        No students to visualize. Upload and grade PDFs first.
      </div>
    );
  }

  return (
    <div style={{ position: "relative", width: "100%", height: 540, borderRadius: 20, overflow: "hidden" }}>
      <Canvas
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true }}
        onPointerMissed={() => setSelectedId(null)}
        style={{ background: "linear-gradient(180deg, #080818 0%, #101028 100%)", borderRadius: 20 }}
      >
        <Scene
          nodes={nodes}
          bandGroups={bandGroups}
          bandLabels={bandLabels}
          selectedId={selectedId}
          hoveredId={hoveredId}
          onSelect={handleSelect}
          onHover={setHoveredId}
          onLeave={() => setHoveredId(null)}
        />
      </Canvas>

      <Legend />

      {selectedNode && <Detail node={selectedNode} onClose={() => setSelectedId(null)} />}

      {!selectedId && !hoveredId && (
        <div style={{
          position: "absolute", top: 16, left: "50%", transform: "translateX(-50%)",
          color: "rgba(255,255,255,0.45)", fontSize: 11,
          background: "rgba(0,0,0,0.45)", padding: "4px 14px", borderRadius: 20,
          pointerEvents: "none", zIndex: 30,
        }}>
          Click a sphere to inspect · Drag to orbit · Scroll to zoom
        </div>
      )}
    </div>
  );
}
