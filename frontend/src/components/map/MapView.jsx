import 'leaflet/dist/leaflet.css'
import { useEffect } from 'react'
import { Circle, CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'

const STATUS_COLOR = {
  available: '#10b981',
  operational: '#10b981',
  booked: '#f59e0b',
  in_transit: '#3b82f6',
  maintenance: '#94a3b8',
}

// Only render a marker/line when its coordinates are real numbers - guards
// against null/NaN coming back from the API (would otherwise break Leaflet).
const isValid = (lat, lon) => Number.isFinite(lat) && Number.isFinite(lon)

// Fits the map to whatever points we have (CHCs, machines, relocation lines, route).
function FitBounds({ points }) {
  const map = useMap()
  useEffect(() => {
    const valid = (points || []).filter((p) => Array.isArray(p) && isValid(p[0], p[1]))
    if (valid.length === 1) map.setView(valid[0], 12)
    else if (valid.length > 1) map.fitBounds(valid, { padding: [30, 30] })
  }, [points, map])
  return null
}

// Keeps Leaflet's canvas in sync when its container resizes (sidebar toggle,
// window resize, layout shifts). Without this, tiles can render grey/partial.
function ResizeHandler() {
  const map = useMap()
  useEffect(() => {
    const fix = () => map.invalidateSize()
    const container = map.getContainer()
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(fix) : null
    if (ro) ro.observe(container)
    window.addEventListener('resize', fix)
    const t = setTimeout(fix, 200) // settle after first paint
    return () => {
      if (ro) ro.disconnect()
      window.removeEventListener('resize', fix)
      clearTimeout(t)
    }
  }, [map])
  return null
}

export default function MapView({
  chcs = [],
  machines = [],
  shortages = [],
  relocations = [],
  route = null,
  requestsById = {},
  height = 'h-[520px]',
}) {
  const points = [
    ...chcs.map((c) => [c.latitude, c.longitude]),
    ...machines.map((m) => [m.latitude, m.longitude]),
    ...relocations.flatMap((r) => [r.from, r.to]),
    ...((route && route.path) || []),
  ].filter((p) => Array.isArray(p) && isValid(p[0], p[1]))
  const center = points[0] || [26.8, 80.9]

  return (
    <div className={`${height} w-full overflow-hidden rounded-xl border border-slate-200`}>
      <MapContainer center={center} zoom={8} scrollWheelZoom className="h-full w-full">
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />

        {shortages.map((s, i) =>
          isValid(s.latitude, s.longitude) ? (
            <Circle
              key={`sz-${i}`}
              center={[s.latitude, s.longitude]}
              radius={14000}
              pathOptions={{ color: '#ef4444', fillColor: '#ef4444', fillOpacity: 0.12, weight: 1 }}
            >
              <Popup>
                <b>{s.cluster}</b> — {s.machine_type}
                <br />
                {s.risk_level} shortage ({Math.round(s.shortage_probability * 100)}%)
                {(s.expected_requests != null || s.available_supply != null) && (
                  <>
                    <br />
                    demand {s.expected_requests} · available {s.available_supply}
                  </>
                )}
              </Popup>
            </Circle>
          ) : null,
        )}

        {/* Relocation moves in progress: dashed line source CHC -> destination cluster centroid. */}
        {relocations.map((r) =>
          isValid(r.from?.[0], r.from?.[1]) && isValid(r.to?.[0], r.to?.[1]) ? (
            <Polyline
              key={`reloc-${r.id}`}
              positions={[r.from, r.to]}
              pathOptions={{ color: '#3b82f6', weight: 2, dashArray: '8 6', opacity: 0.9 }}
            >
              <Popup>
                <b>Relocation in progress</b>
                <br />
                #{r.machineId} {r.machineType}
                <br />
                {r.fromName} → {r.toCluster}
              </Popup>
            </Polyline>
          ) : null,
        )}

        {chcs.map((c) =>
          isValid(c.latitude, c.longitude) ? (
            <CircleMarker
              key={`chc-${c.id}`}
              center={[c.latitude, c.longitude]}
              radius={7}
              pathOptions={{ color: '#0f766e', fillColor: '#0f766e', fillOpacity: 0.9 }}
            >
              <Popup>
                <b>{c.name}</b>
                <br />
                CHC · {c.location}
              </Popup>
            </CircleMarker>
          ) : null,
        )}

        {machines.map((m) => {
          if (!isValid(m.latitude, m.longitude)) return null
          const color = STATUS_COLOR[m.status] || '#64748b'
          return (
            <CircleMarker
              key={`m-${m.id}`}
              center={[m.latitude, m.longitude]}
              radius={5}
              pathOptions={{ color, fillColor: color, fillOpacity: 0.9 }}
            >
              <Popup>
                #{m.id} {m.machine_type}
                <br />
                {m.chc_name}
                <br />
                status: {m.status}
              </Popup>
            </CircleMarker>
          )
        })}

        {route && route.path && route.path.length > 1 && (
          <Polyline positions={route.path} pathOptions={{ color: '#2563eb', weight: 3 }} />
        )}

        {route &&
          route.stops &&
          route.stops.map((s, i) => {
            if (!isValid(s.latitude, s.longitude)) return null
            const color = s.is_depot ? '#0f766e' : '#2563eb'
            const info = !s.is_depot ? requestsById[s.request_id] : null
            return (
              <CircleMarker
                key={`rs-${i}`}
                center={[s.latitude, s.longitude]}
                radius={s.is_depot ? 7 : 5}
                pathOptions={{ color, fillColor: color, fillOpacity: 1 }}
              >
                <Popup>
                  {s.is_depot ? 'Depot' : `Stop ${s.sequence_number}`}
                  {info ? (
                    <>
                      <br />
                      {info.farmer_name}
                      {info.crop_type ? ` · ${info.crop_type}` : ''}
                    </>
                  ) : null}
                  {!s.is_depot && s.request_id ? (
                    <>
                      <br />
                      Req #{s.request_id}
                    </>
                  ) : null}
                  {s.arrival_clock ? (
                    <>
                      <br />
                      arrive {s.arrival_clock}
                    </>
                  ) : null}
                </Popup>
              </CircleMarker>
            )
          })}

        <FitBounds points={points} />
        <ResizeHandler />
      </MapContainer>
    </div>
  )
}
