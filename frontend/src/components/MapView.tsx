import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  useMap,
} from "react-leaflet";
import L from "leaflet";
import type { Camera, WatchResponse } from "../types";

const GEOAPIFY_KEY = import.meta.env.VITE_GEOAPIFY_KEY as string | undefined;

// Fix default marker icons (Leaflet + bundlers).
const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

const DIR_OFFSET: Record<string, [number, number]> = {
  north: [0.004, 0],
  south: [-0.004, 0],
  east: [0, 0.005],
  west: [0, -0.005],
  stop: [0, 0],
};

function riskColor(score: number): string {
  if (score >= 0.66) return "#ff4d4f";
  if (score >= 0.33) return "#ffa940";
  return "#52c41a";
}

function Recenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], 15);
  }, [lat, lng, map]);
  return null;
}

export default function MapView({
  cameras,
  selected,
  onSelect,
  result,
}: {
  cameras: Camera[];
  selected: Camera | null;
  onSelect: (c: Camera) => void;
  result: WatchResponse | null;
}) {
  const center: [number, number] = selected
    ? [selected.lat, selected.lng]
    : [40.7549, -73.984];

  const tracker = result?.tracker;
  const risks = result?.risk?.path_risks ?? [];
  const paths = result?.prediction?.paths ?? [];

  return (
    <MapContainer center={center} zoom={13} className="map">
      {GEOAPIFY_KEY ? (
        <TileLayer
          attribution='Powered by <a href="https://www.geoapify.com/">Geoapify</a> | &copy; OpenStreetMap contributors'
          url={`https://maps.geoapify.com/v1/tile/osm-bright/{z}/{x}/{y}.png?apiKey=${GEOAPIFY_KEY}`}
        />
      ) : (
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
      )}
      {selected && <Recenter lat={center[0]} lng={center[1]} />}

      {cameras.map((c) => (
        <Marker
          key={c.id}
          position={[c.lat, c.lng]}
          icon={icon}
          eventHandlers={{ click: () => onSelect(c) }}
        >
          <Popup>{c.name}</Popup>
        </Marker>
      ))}

      {tracker &&
        paths.map((p) => {
          const off = DIR_OFFSET[p.direction] ?? [0, 0];
          const end: [number, number] = [
            tracker.lat + off[0],
            tracker.lng + off[1],
          ];
          const risk =
            risks.find((r) => r.direction === p.direction)?.risk_score ?? 0.3;
          if (p.direction === "stop") return null;
          return (
            <Polyline
              key={p.direction}
              positions={[[tracker.lat, tracker.lng], end]}
              pathOptions={{
                color: riskColor(risk),
                weight: 4 + p.probability * 10,
                opacity: 0.75,
              }}
            >
              <Popup>
                {p.direction}: {Math.round(p.probability * 100)}% · risk{" "}
                {Math.round(risk * 100)}%
              </Popup>
            </Polyline>
          );
        })}
    </MapContainer>
  );
}
