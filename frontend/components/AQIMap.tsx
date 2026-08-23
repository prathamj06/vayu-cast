'use client';

import React, { useState, useEffect, useRef, useMemo, Component, ErrorInfo, ReactNode } from 'react';
import DeckGL from '@deck.gl/react';
import { H3HexagonLayer } from '@deck.gl/geo-layers';
import maplibregl from 'maplibre-gl';
import { HexagonData } from '@/types';
import { getAQICategory, getAQIRGB } from '@/lib/aqi-utils';
import { AlertCircle, Eye } from 'lucide-react';

// Free, keyless CARTO Dark Matter Basemap Style
const CARTO_DARK_MATTER_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

// Direct 2D Top-Down (Nadir) Geospatial Camera Position centered on NCT Delhi
const INITIAL_VIEW_STATE = {
  latitude: 28.6139,
  longitude: 77.2090,
  zoom: 10.3,
  minZoom: 8,
  maxZoom: 15,
  pitch: 0,    // 0° Pitch: Direct 2D Top-Down Nadir View
  bearing: 0,  // 0° Bearing: True North Orientation
};

interface WebGLErrorBoundaryProps {
  children: ReactNode;
}

interface WebGLErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class WebGLErrorBoundary extends Component<WebGLErrorBoundaryProps, WebGLErrorBoundaryState> {
  constructor(props: WebGLErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): WebGLErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('WebGL Rendering Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full flex items-center justify-center bg-slate-950 text-white p-6">
          <div className="glass-panel p-6 rounded-2xl max-w-md flex flex-col items-center text-center gap-3 border border-rose-500/30">
            <AlertCircle className="w-10 h-10 text-rose-500" />
            <h3 className="text-lg font-bold">WebGL Acceleration Required</h3>
            <p className="text-xs text-slate-400">
              Your browser or graphics driver encountered an issue initializing WebGL 2.0. Please verify hardware acceleration is enabled in browser settings.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-xl text-xs font-bold transition shadow-lg"
            >
              Reload Platform
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

interface AQIMapProps {
  hexagons: HexagonData[];
  currentHour: number;
  selectedHexagon: HexagonData | null;
  selectedZone: string | null;
  onSelectHexagon: (hex: HexagonData) => void;
  language: 'en' | 'hi';
}

const AQIMapInner: React.FC<AQIMapProps> = ({
  hexagons,
  currentHour,
  selectedHexagon,
  selectedZone,
  onSelectHexagon,
  language,
}) => {
  const [viewState, setViewState] = useState(INITIAL_VIEW_STATE);
  const [hoverInfo, setHoverInfo] = useState<{
    x: number;
    y: number;
    object?: HexagonData;
  } | null>(null);

  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

  // Initialize MapLibre GL Basemap
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: CARTO_DARK_MATTER_STYLE,
      center: [INITIAL_VIEW_STATE.longitude, INITIAL_VIEW_STATE.latitude],
      zoom: INITIAL_VIEW_STATE.zoom,
      pitch: INITIAL_VIEW_STATE.pitch,
      bearing: INITIAL_VIEW_STATE.bearing,
      interactive: false, // DeckGL handles user gesture controls
      attributionControl: false,
    });

    mapRef.current = map;

    return () => {
      map.remove();
    };
  }, []);

  // Synchronize MapLibre camera with DeckGL view state
  const handleViewStateChange = ({ viewState: nextViewState }: any) => {
    setViewState(nextViewState);
    if (mapRef.current) {
      mapRef.current.jumpTo({
        center: [nextViewState.longitude, nextViewState.latitude],
        zoom: nextViewState.zoom,
        pitch: nextViewState.pitch,
        bearing: nextViewState.bearing,
      });
    }
  };

  // Fly to region centroid when a specific municipal zone is selected
  useEffect(() => {
    if (!selectedZone) {
      setViewState((prev) => ({
        ...prev,
        latitude: INITIAL_VIEW_STATE.latitude,
        longitude: INITIAL_VIEW_STATE.longitude,
        zoom: INITIAL_VIEW_STATE.zoom,
      }));
      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [INITIAL_VIEW_STATE.longitude, INITIAL_VIEW_STATE.latitude],
          zoom: INITIAL_VIEW_STATE.zoom,
          duration: 700,
        });
      }
      return;
    }

    const zoneHexes = hexagons.filter((h) => h.zone_name.toLowerCase() === selectedZone.toLowerCase());
    if (zoneHexes.length > 0) {
      const avgLat = zoneHexes.reduce((acc, h) => acc + h.centroid[0], 0) / zoneHexes.length;
      const avgLon = zoneHexes.reduce((acc, h) => acc + h.centroid[1], 0) / zoneHexes.length;

      setViewState((prev) => ({
        ...prev,
        latitude: avgLat,
        longitude: avgLon,
        zoom: 11.4,
      }));

      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [avgLon, avgLat],
          zoom: 11.4,
          duration: 700,
        });
      }
    }
  }, [selectedZone, hexagons]);

  // Construct Deck.gl H3 Hexagon Layer with Complete Region-Wide Highlighting
  const layers = useMemo(() => {
    return [
      new H3HexagonLayer<HexagonData>({
        id: 'h3-delhi-aqi-layer',
        data: hexagons,
        pickable: true,
        stroked: true,
        filled: true,
        extruded: false,
        getHexagon: (d) => d.hex_id,
        // Dynamic region fill styling:
        // - Single selected hex: brightest (alpha = 160)
        // - Constituent hexes of selectedZone: elevated (alpha = 115)
        // - Unselected zones when a zone is active: dimmed (alpha = 30)
        // - Normal state: translucent (alpha = 65)
        getFillColor: (d) => {
          const aqiVal = d.forecast_72h?.[currentHour] ?? d.aqi;
          const isHexSelected = selectedHexagon?.hex_id === d.hex_id;
          const isZoneSelected = selectedZone && d.zone_name.toLowerCase() === selectedZone.toLowerCase();

          if (isHexSelected) return getAQIRGB(aqiVal, 160);
          if (isZoneSelected) return getAQIRGB(aqiVal, 115);
          if (selectedZone && !isZoneSelected) return getAQIRGB(aqiVal, 28);
          return getAQIRGB(aqiVal, 65);
        },
        // Precise regional boundary stroke:
        // - Selected hex: Pure white solid border
        // - Selected zone constituent hexes: Glowing cyan border
        // - Others: subtle grid edge
        getLineColor: (d) => {
          if (selectedHexagon?.hex_id === d.hex_id) {
            return [255, 255, 255, 255]; // Pure white highlight on single hex selection
          }
          if (selectedZone && d.zone_name.toLowerCase() === selectedZone.toLowerCase()) {
            return [56, 189, 248, 220];  // Vibrant cyan boundary for entire selected region
          }
          return [255, 255, 255, 20];     // Subtle grid boundary
        },
        getLineWidth: (d) => {
          if (selectedHexagon?.hex_id === d.hex_id) return 2.8;
          if (selectedZone && d.zone_name.toLowerCase() === selectedZone.toLowerCase()) return 1.6;
          return 0.7;
        },
        lineWidthUnits: 'pixels',
        lineWidthMinPixels: 0.5,
        updateTriggers: {
          getFillColor: [currentHour, selectedHexagon?.hex_id, selectedZone],
          getLineColor: [selectedHexagon?.hex_id, selectedZone],
          getLineWidth: [selectedHexagon?.hex_id, selectedZone],
        },
        onHover: (info) => {
          if (info.object) {
            setHoverInfo({
              x: info.x,
              y: info.y,
              object: info.object,
            });
          } else {
            setHoverInfo(null);
          }
        },
        onClick: (info) => {
          if (info.object) {
            onSelectHexagon(info.object);
          }
        },
      }),
    ];
  }, [hexagons, currentHour, selectedHexagon, selectedZone, onSelectHexagon]);

  return (
    <div className="relative w-full h-full select-none overflow-hidden bg-[#070a12]">
      {/* MapLibre GL Basemap Canvas */}
      <div ref={mapContainerRef} className="absolute inset-0 w-full h-full z-0" />

      {/* Deck.gl WebGL Overlay */}
      <div className="absolute inset-0 z-10">
        <DeckGL
          viewState={viewState}
          onViewStateChange={handleViewStateChange}
          controller={{ doubleClickZoom: false, dragRotate: false }}
          layers={layers}
          getCursor={({ isHovering }) => (isHovering ? 'pointer' : 'default')}
        />
      </div>

      {/* Interactive Hexagon Hover Tooltip */}
      {hoverInfo?.object && (
        <div
          className="absolute z-30 pointer-events-none glass-panel px-3.5 py-2.5 rounded-xl border border-white/20 shadow-2xl transition-transform"
          style={{
            left: hoverInfo.x + 12,
            top: hoverInfo.y + 12,
            transform: 'translate3d(0, 0, 0)',
          }}
        >
          {(() => {
            const hex = hoverInfo.object;
            const aqiVal = hex.forecast_72h?.[currentHour] ?? hex.aqi;
            const cat = getAQICategory(aqiVal);
            return (
              <div className="flex flex-col gap-1 min-w-[170px]">
                <div className="flex items-center justify-between border-b border-white/10 pb-1">
                  <span className="font-bold text-xs text-white tracking-tight">
                    {hex.zone_name}
                  </span>
                  <span className="text-[10px] text-cyan-400 font-mono">
                    +{currentHour}h
                  </span>
                </div>
                <div className="flex items-baseline justify-between pt-0.5">
                  <span
                    className="text-2xl font-black tabular-nums tracking-tighter"
                    style={{ color: cat.color }}
                  >
                    {aqiVal}
                  </span>
                  <span
                    className="text-[11px] font-bold"
                    style={{ color: cat.color }}
                  >
                    {language === 'en' ? cat.label : cat.label_hi}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono flex items-center justify-between pt-0.5 border-t border-white/5">
                  <span>{hex.centroid[0].toFixed(3)}°, {hex.centroid[1].toFixed(3)}°</span>
                  <span className="text-cyan-300 font-sans flex items-center gap-0.5">
                    <Eye className="w-2.5 h-2.5" /> Click
                  </span>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};

export const AQIMap: React.FC<AQIMapProps> = (props) => {
  return (
    <WebGLErrorBoundary>
      <AQIMapInner {...props} />
    </WebGLErrorBoundary>
  );
};
