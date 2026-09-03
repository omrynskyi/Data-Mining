import { useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import type { ClusterProfile, Customer } from '../types';

interface ClusterVisualizer3DProps {
  customers: Customer[];
  clusters: ClusterProfile[];
}

const WIDTH = 720;
const HEIGHT = 420;
const CAMERA_DISTANCE = 4.2;
const DEFAULT_YAW = 38;
const DEFAULT_PITCH = 22;

interface ProjectedPoint {
  key: number;
  x: number;
  y: number;
  depth: number;
  radius: number;
  color: string;
  label: string;
}

const AXES: Array<{ key: 'x' | 'y' | 'z'; vector: [number, number, number]; label: string; color: string }> = [
  { key: 'x', vector: [1, 0, 0], label: 'Age', color: '#f472b6' },
  { key: 'y', vector: [0, 1, 0], label: 'Income', color: '#38bdf8' },
  { key: 'z', vector: [0, 0, 1], label: 'Spending', color: '#4ade80' },
];

/** Rotates a point around the Y then X axis and applies a weak perspective divide. */
function project(
  point: [number, number, number],
  yawDeg: number,
  pitchDeg: number,
): { x: number; y: number; depth: number; scale: number } {
  const yaw = (yawDeg * Math.PI) / 180;
  const pitch = (pitchDeg * Math.PI) / 180;
  const [px, py, pz] = point;

  const x1 = px * Math.cos(yaw) + pz * Math.sin(yaw);
  const z1 = -px * Math.sin(yaw) + pz * Math.cos(yaw);
  const y2 = py * Math.cos(pitch) - z1 * Math.sin(pitch);
  const z2 = py * Math.sin(pitch) + z1 * Math.cos(pitch);

  const scale = CAMERA_DISTANCE / (CAMERA_DISTANCE + z2);
  return {
    x: WIDTH / 2 + x1 * scale * (WIDTH / 4.6),
    y: HEIGHT / 2 - y2 * scale * (HEIGHT / 3.4),
    depth: z2,
    scale,
  };
}

const normalize = (value: number, min: number, max: number): number =>
  max === min ? 0 : ((value - min) / (max - min)) * 2 - 1;

export default function ClusterVisualizer3D({ customers, clusters }: ClusterVisualizer3DProps) {
  const [yaw, setYaw] = useState(DEFAULT_YAW);
  const [pitch, setPitch] = useState(DEFAULT_PITCH);

  const colorByCluster = useMemo(() => {
    const map = new Map<number, ClusterProfile>();
    clusters.forEach((cluster) => map.set(cluster.cluster_id, cluster));
    return map;
  }, [clusters]);

  const points = useMemo<ProjectedPoint[]>(() => {
    if (customers.length === 0) return [];

    const ages = customers.map((c) => c.age);
    const incomes = customers.map((c) => c.annual_income);
    const scores = customers.map((c) => c.spending_score);
    const bounds = {
      age: [Math.min(...ages), Math.max(...ages)] as const,
      income: [Math.min(...incomes), Math.max(...incomes)] as const,
      score: [Math.min(...scores), Math.max(...scores)] as const,
    };

    return customers
      .map((customer) => {
        const vector: [number, number, number] = [
          normalize(customer.age, bounds.age[0], bounds.age[1]),
          normalize(customer.annual_income, bounds.income[0], bounds.income[1]),
          normalize(customer.spending_score, bounds.score[0], bounds.score[1]),
        ];
        const projected = project(vector, yaw, pitch);
        const cluster = colorByCluster.get(customer.cluster_id);
        return {
          key: customer.customer_id,
          x: projected.x,
          y: projected.y,
          depth: projected.depth,
          radius: 3.2 * projected.scale + 1.2,
          color: cluster?.color ?? '#94a3b8',
          label: `#${customer.customer_id} · ${cluster?.name ?? 'Unassigned'} · age ${customer.age}, $${customer.annual_income}k, score ${customer.spending_score}`,
        };
      })
      .sort((a, b) => b.depth - a.depth);
  }, [colorByCluster, customers, pitch, yaw]);

  const axisLines = AXES.map((axis) => {
    const from = project([-axis.vector[0], -axis.vector[1], -axis.vector[2]], yaw, pitch);
    const to = project(axis.vector, yaw, pitch);
    return { ...axis, from, to };
  });

  return (
    <section className="panel" aria-label="Three dimensional cluster projection">
      <header className="panel-header">
        <div>
          <h2 className="panel-title">Cluster projection — 3D</h2>
          <p className="panel-subtitle">
            Age × Annual income × Spending score, rendered with an SVG perspective projection
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setYaw(DEFAULT_YAW);
            setPitch(DEFAULT_PITCH);
          }}
          className="chip hover:border-surface-600"
        >
          <RotateCcw className="h-3 w-3" aria-hidden="true" />
          Reset view
        </button>
      </header>

      <div className="p-4">
        <svg
          data-testid="cluster-3d-canvas"
          role="img"
          aria-label={`3D projection of ${points.length} customers across ${clusters.length} clusters`}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="h-auto w-full rounded-lg bg-surface-950/60"
        >
          <defs>
            <radialGradient id="depth-fade" cx="50%" cy="50%" r="70%">
              <stop offset="0%" stopColor="#0f172a" stopOpacity="0" />
              <stop offset="100%" stopColor="#020617" stopOpacity="0.55" />
            </radialGradient>
          </defs>

          {axisLines.map((axis) => (
            <g key={axis.key}>
              <line
                x1={axis.from.x}
                y1={axis.from.y}
                x2={axis.to.x}
                y2={axis.to.y}
                stroke={axis.color}
                strokeOpacity={0.4}
                strokeWidth={1}
                strokeDasharray="4 4"
              />
              <text x={axis.to.x + 6} y={axis.to.y} fill={axis.color} fontSize={11} opacity={0.8}>
                {axis.label}
              </text>
            </g>
          ))}

          {points.map((point) => (
            <circle
              key={point.key}
              cx={point.x}
              cy={point.y}
              r={point.radius}
              fill={point.color}
              fillOpacity={0.55 + Math.max(0, 0.35 * (1 - point.depth))}
              stroke={point.color}
              strokeOpacity={0.35}
            >
              <title>{point.label}</title>
            </circle>
          ))}

          <rect width={WIDTH} height={HEIGHT} fill="url(#depth-fade)" pointerEvents="none" />
        </svg>
      </div>

      <footer className="grid gap-4 border-t border-surface-800 px-5 py-4 sm:grid-cols-2">
        <label className="text-xs text-slate-400">
          <span className="mb-1.5 flex justify-between">
            <span>Yaw</span>
            <span className="font-mono text-slate-500">{yaw}°</span>
          </span>
          <input
            type="range"
            min={-180}
            max={180}
            value={yaw}
            onChange={(event) => setYaw(Number(event.target.value))}
            className="w-full accent-sky-400"
            aria-label="Rotate horizontally"
          />
        </label>
        <label className="text-xs text-slate-400">
          <span className="mb-1.5 flex justify-between">
            <span>Pitch</span>
            <span className="font-mono text-slate-500">{pitch}°</span>
          </span>
          <input
            type="range"
            min={-80}
            max={80}
            value={pitch}
            onChange={(event) => setPitch(Number(event.target.value))}
            className="w-full accent-sky-400"
            aria-label="Rotate vertically"
          />
        </label>
      </footer>
    </section>
  );
}
