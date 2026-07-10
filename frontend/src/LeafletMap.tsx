import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { VisualizationRiskLink, VisualizationStation } from './api';

type Props = {
  stations: VisualizationStation[];
  links: VisualizationRiskLink[];
  selectedLinkKey: string | null;
  onLinkSelect: (key: string) => void;
};

const levelColor: Record<string, string> = {
  高: '#d92d20',
  中: '#dc6803',
  低: '#078658',
};

export default function LeafletMap({ stations, links, selectedLinkKey, onLinkSelect }: Props) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const instanceRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    const validStations = stations.filter((station) => station.latitude !== null && station.longitude !== null);
    if (!validStations.length) return;

    if (!instanceRef.current) {
      instanceRef.current = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: true,
      });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(instanceRef.current);
    }

    const map = instanceRef.current;
    map.eachLayer((layer) => {
      if (!(layer instanceof L.TileLayer)) {
        layer.remove();
      }
    });

    const stationById = new Map(validStations.map((station) => [station.station_id, station]));
    const bounds: L.LatLngTuple[] = [];

    for (const link of links.slice(0, 100)) {
      const a = stationById.get(link.station_a);
      const b = stationById.get(link.station_b);
      if (!a || !b || a.latitude === null || a.longitude === null || b.latitude === null || b.longitude === null) continue;
      const key = linkKey(link);
      const selected = selectedLinkKey === key;
      L.polyline(
        [
          [a.latitude, a.longitude],
          [b.latitude, b.longitude],
        ],
        {
          color: levelColor[link.severity] ?? '#667085',
          opacity: selected ? 0.95 : link.severity === '高' ? 0.8 : 0.48,
          weight: selected ? 5 : link.severity === '高' ? 3 : 2,
        },
      )
        .bindTooltip(`${link.station_a} - ${link.station_b}｜${link.risk_type}｜${link.score}`)
        .on('click', () => onLinkSelect(key))
        .addTo(map);
    }

    for (const station of validStations) {
      if (station.latitude === null || station.longitude === null) continue;
      const point: L.LatLngTuple = [station.latitude, station.longitude];
      bounds.push(point);
      const connectedToSelection =
        selectedLinkKey !== null &&
        links.some(
          (link) =>
            linkKey(link) === selectedLinkKey && (link.station_a === station.station_id || link.station_b === station.station_id),
        );
      L.circleMarker(point, {
        radius: connectedToSelection ? 10 : station.risk_level === '高' ? 8 : station.risk_level === '中' ? 7 : 6,
        color: connectedToSelection ? '#172033' : '#ffffff',
        weight: connectedToSelection ? 2 : 1,
        fillColor: levelColor[station.risk_level] ?? '#078658',
        fillOpacity: 0.9,
      })
        .bindPopup(
          `<strong>${escapeHtml(station.station_id)}</strong><br/>${escapeHtml(station.name)}<br/>${formatFrequency(
            station.frequency_mhz,
          )}<br/>风险：${escapeHtml(station.risk_level)}`,
        )
        .addTo(map);
    }

    if (bounds.length) {
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 });
      window.setTimeout(() => map.invalidateSize(), 0);
    }
  }, [stations, links, selectedLinkKey, onLinkSelect]);

  useEffect(() => {
    return () => {
      instanceRef.current?.remove();
      instanceRef.current = null;
    };
  }, []);

  return <div className="leaflet-map" ref={mapRef} />;
}

function linkKey(link: VisualizationRiskLink): string {
  return `${link.station_a}-${link.station_b}-${link.risk_type}-${link.frequency_a_mhz ?? '-'}-${link.frequency_b_mhz ?? '-'}`;
}

function formatFrequency(value: number | null): string {
  return value === null ? '- MHz' : `${value.toFixed(6)} MHz`;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
