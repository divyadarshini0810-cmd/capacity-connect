import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { ContactShadows, Float, Line, MeshDistortMaterial, Sparkles, Stars } from '@react-three/drei'
import { useMemo, useRef } from 'react'
import * as THREE from 'three'

type Props = { progress: number }
type SceneProps = Props & { compact?: boolean }
type Point = [number, number, number]

const cameraStops = [
  new THREE.Vector3(0, 0.15, 7.2),
  new THREE.Vector3(3.8, 1.05, 5.65),
  new THREE.Vector3(-3.45, 0.75, 5.9),
  new THREE.Vector3(1.2, 1.8, 6.55),
  new THREE.Vector3(0, 0.25, 7.4),
]
const targetStops = [
  new THREE.Vector3(0, 0, 0),
  new THREE.Vector3(0, 0.1, 0),
  new THREE.Vector3(-0.55, 0, 0.1),
  new THREE.Vector3(1.15, 0.25, -0.45),
  new THREE.Vector3(0, 0.1, 0),
]

function CameraFlight({ progress }: Props) {
  const { camera, pointer } = useThree()
  const lookAt = useRef(new THREE.Vector3())
  useFrame((_state, delta) => {
    const exact = Math.min(3.999, Math.max(0, progress * 4))
    const from = Math.floor(exact)
    const mix = exact - from
    const next = Math.min(from + 1, cameraStops.length - 1)
    const destination = cameraStops[from].clone().lerp(cameraStops[next], mix)
    destination.x += pointer.x * 0.32
    destination.y += pointer.y * 0.2
    const target = targetStops[from].clone().lerp(targetStops[next], mix)
    const smoothing = 1 - Math.pow(0.001, delta)
    camera.position.lerp(destination, smoothing)
    lookAt.current.lerp(target, smoothing)
    camera.lookAt(lookAt.current)
  })
  return null
}

function Earth({ compact }: { compact: boolean }) {
  const world = useRef<THREE.Group>(null)
  useFrame((_state, delta) => { if (world.current) world.current.rotation.y += delta * 0.035 })
  return <group ref={world}>
    <mesh castShadow receiveShadow>
      <sphereGeometry args={[1.55, compact ? 48 : 96, compact ? 48 : 96]} />
      <MeshDistortMaterial color="#075b83" emissive="#023e7a" emissiveIntensity={1.35} metalness={0.62} roughness={0.3} distort={0.16} speed={0.65} />
    </mesh>
    <mesh scale={1.004}>
      <sphereGeometry args={[1.55, compact ? 32 : 60, compact ? 32 : 60]} />
      <meshBasicMaterial color="#1af0de" wireframe transparent opacity={0.14} />
    </mesh>
    <mesh scale={1.075}>
      <sphereGeometry args={[1.55, compact ? 36 : 72, compact ? 36 : 72]} />
      <meshBasicMaterial color="#58e9ff" transparent opacity={0.06} side={THREE.BackSide} />
    </mesh>
    <mesh rotation={[0.65, 0.35, -0.15]} scale={[1.31, 1.31, 0.3]}>
      <torusGeometry args={[1.55, 0.018, 8, 120]} />
      <meshBasicMaterial color="#6ef4e4" transparent opacity={0.5} />
    </mesh>
    <mesh rotation={[-0.55, -0.55, 0.15]} scale={[1.6, 1.6, 0.28]}>
      <torusGeometry args={[1.55, 0.01, 8, 120]} />
      <meshBasicMaterial color="#a780ff" transparent opacity={0.45} />
    </mesh>
  </group>
}

function OceanParticles({ compact }: { compact: boolean }) {
  const positions = useMemo(() => {
    const count = compact ? 220 : 420
    const values = new Float32Array(count * 3)
    for (let i = 0; i < count; i += 1) {
      const radius = 2.2 + Math.random() * 6.2
      const angle = Math.random() * Math.PI * 2
      values[i * 3] = Math.cos(angle) * radius
      values[i * 3 + 1] = (Math.random() - 0.5) * 5.5
      values[i * 3 + 2] = Math.sin(angle) * radius - 1.2
    }
    return values
  }, [compact])
  return <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial size={0.026} color="#75f6ec" transparent opacity={0.65} sizeAttenuation /></points>
}

function CompetencyNetwork({ compact }: { compact: boolean }) {
  const group = useRef<THREE.Group>(null)
  const points = useMemo<Point[]>(() => Array.from({ length: compact ? 10 : 14 }, (_, index) => {
    const angle = index * 2.399
    const radius = 2.6 + (index % 3) * 0.42
    return [Math.cos(angle) * radius, ((index % 5) - 2) * 0.47, Math.sin(angle) * radius] as Point
  }), [compact])
  useFrame((_state, delta) => { if (group.current) group.current.rotation.y -= delta * 0.022 })
  return <group ref={group}>{points.map((point, index) => <Float key={index} speed={0.8 + (index % 3) * 0.16} floatIntensity={0.42} rotationIntensity={0.2}><group position={point}><mesh castShadow><sphereGeometry args={[0.07 + (index % 4) * 0.018, compact ? 12 : 20, compact ? 12 : 20]} /><meshStandardMaterial color={index % 4 === 0 ? '#7e67ff' : index % 5 === 0 ? '#4fdca1' : '#54f2e2'} emissive={index % 4 === 0 ? '#7e67ff' : '#1ccdc1'} emissiveIntensity={2.5} roughness={0.15} /></mesh><pointLight color={index % 4 === 0 ? '#946eff' : '#4ff3e4'} intensity={1.4} distance={1.5} /></group></Float>)}{points.map((point, index) => <Line key={`line-${index}`} points={[point, points[(index + 3) % points.length]]} color={index % 3 === 0 ? '#896cff' : '#3ee4d7'} transparent opacity={0.25} dashed dashScale={2.5} dashSize={0.08} gapSize={0.12} lineWidth={0.5} />)}</group>
}

function LearningOrbit() {
  const group = useRef<THREE.Group>(null)
  useFrame((_state, delta) => { if (group.current) group.current.rotation.z += delta * 0.07 })
  return <group ref={group} position={[-1.1, -0.15, -0.5]} rotation={[0.7, 0.25, 0]}>
    {[1.92, 2.22, 2.52].map((radius, index) => <mesh key={radius} rotation={[0, index * 0.45, 0]}><torusGeometry args={[radius, 0.013, 8, 100, Math.PI * 1.46]} /><meshBasicMaterial color={index === 1 ? '#8a70ff' : '#4de9dc'} transparent opacity={0.66 - index * 0.1} /></mesh>)}
    {[0, 1.1, 2.2, 3.2].map((angle, index) => <Float key={angle} speed={1.3} floatIntensity={0.24}><mesh position={[Math.cos(angle) * 2.22, Math.sin(angle) * 2.22, 0]}><octahedronGeometry args={[0.09 + index * 0.018, 1]} /><meshStandardMaterial color="#75f6e8" emissive="#36d5c8" emissiveIntensity={2} /></mesh></Float>)}
  </group>
}

function LegacyVault() {
  const vault = useRef<THREE.Group>(null)
  useFrame((_state, delta) => { if (vault.current) vault.current.rotation.y = Math.sin(Date.now() * 0.00022) * 0.14 + delta * 0.02 })
  return <group ref={vault} position={[1.1, 0.2, -1.35]}>{[-0.7, -0.32, 0.05, 0.42, 0.8].map((offset, index) => <Float key={offset} speed={0.72 + index * 0.08} floatIntensity={0.3}><mesh position={[offset, Math.sin(index) * 0.15, 0]} castShadow><boxGeometry args={[0.19, 1.05 + (index % 2) * 0.28, 0.16]} /><meshStandardMaterial color={index === 2 ? '#6e5bf4' : '#0b7892'} emissive={index === 2 ? '#6d53d9' : '#056a88'} emissiveIntensity={1.25} metalness={0.75} roughness={0.24} /></mesh></Float>)}<Line points={[[-1.15, -0.75, 0], [1.2, -0.75, 0]]} color="#4ce9dc" transparent opacity={0.5} lineWidth={0.8} /></group>
}

function AnalyticsConstellation() {
  const chart = useRef<THREE.Group>(null)
  useFrame((_state, delta) => { if (chart.current) chart.current.rotation.y -= delta * 0.025 })
  const bars = [0.72, 1.24, 0.98, 1.7, 1.44, 2.04]
  return <group ref={chart} position={[0, -0.62, -1.3]}>{bars.map((height, index) => <Float key={height} speed={0.8} floatIntensity={0.18}><mesh position={[(index - 2.5) * 0.35, height / 2 - 0.2, 0]} castShadow><boxGeometry args={[0.16, height, 0.16]} /><meshStandardMaterial color={index === 3 ? '#7a68ff' : '#43e7d6'} emissive={index === 3 ? '#5d48c8' : '#14a99d'} emissiveIntensity={1.35} metalness={0.58} roughness={0.3} /></mesh></Float>)}<Line points={bars.map((height, index) => [(index - 2.5) * 0.35, height + 0.1, 0] as Point)} color="#d4c5ff" transparent opacity={0.7} lineWidth={1.2} /></group>
}

function World({ progress, compact }: SceneProps) {
  return <>
    <color attach="background" args={['#020811']} />
    <fog attach="fog" args={['#020811', 6, 17]} />
    <ambientLight intensity={0.34} color="#79c8ff" />
    <directionalLight position={[5, 6, 4]} intensity={2.5} color="#9beff0" castShadow shadow-mapSize-width={1024} shadow-mapSize-height={1024} />
    <pointLight position={[-4, 2, 2]} intensity={16} color="#075fc1" distance={10} />
    <pointLight position={[3, -1, 2]} intensity={10} color="#714dff" distance={8} />
    <Earth compact={Boolean(compact)} /><CompetencyNetwork compact={Boolean(compact)} /><LearningOrbit /><LegacyVault /><AnalyticsConstellation />
    <OceanParticles compact={Boolean(compact)} /><Sparkles count={compact ? 90 : 170} scale={[14, 9, 12]} size={1.4} speed={0.22} color="#7ff6e9" /><Stars radius={22} depth={34} count={compact ? 850 : 2100} factor={2.15} saturation={0.1} fade speed={0.3} />
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.25, 0]} receiveShadow><circleGeometry args={[8.5, 96]} /><meshStandardMaterial color="#031a2b" emissive="#022137" emissiveIntensity={0.6} metalness={0.9} roughness={0.22} /></mesh>
    {!compact && <ContactShadows position={[0, -2.22, 0]} opacity={0.48} scale={10} blur={2.8} far={4.8} color="#0ce6d3" />}
    <CameraFlight progress={progress} />
  </>
}

export function ImmersiveLandingScene({ progress, compact = false }: SceneProps) {
  return <Canvas className="immersive-r3f" shadows={!compact} dpr={compact ? [1, 1.2] : [1, 1.5]} camera={{ position: cameraStops[0].toArray(), fov: 43 }} gl={{ antialias: !compact, alpha: false, powerPreference: 'high-performance' }}><World progress={progress} compact={compact} /></Canvas>
}
