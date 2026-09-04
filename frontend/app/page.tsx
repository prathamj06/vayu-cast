'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { GridPayload, HexagonData } from '@/types';
import { AQIMap } from '@/components/AQIMap';
import { Header } from '@/components/Header';
import { ForecastSlider } from '@/components/ForecastSlider';
import { InspectorDrawer } from '@/components/InspectorDrawer';
import { AQI_CATEGORIES } from '@/lib/aqi-utils';
import { Layers, Loader2, Sparkles, AlertCircle } from 'lucide-react';

export default function VayuDashboard() {
  const [data, setData] = useState<GridPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dashboard Interactive State
  const [currentHour, setCurrentHour] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState<number>(1);
  const [selectedHexagon, setSelectedHexagon] = useState<HexagonData | null>(null);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [language, setLanguage] = useState<'en' | 'hi'>('en');

  // Real-Time Grid Telemetry Fetcher with Zero-Caching
  const fetchTelemetry = useCallback(async (isInitial = false) => {
    try {
      if (isInitial) setLoading(true);
      
      const bustTimestamp = Date.now();
      let res = await fetch(`/api/grid?t=${bustTimestamp}`, {
        cache: 'no-store',
        headers: { 'Cache-Control': 'no-cache, no-store, must-revalidate' }
      });
      
      if (!res.ok) {
        res = await fetch(`/data/delhi_current_grid.json?t=${bustTimestamp}`, {
          cache: 'no-store'
        });
      }

      if (!res.ok) {
        throw new Error('Failed to load Delhi AQI mesh telemetry');
      }

      const jsonData: GridPayload = await res.json();
      setData(jsonData);
      setError(null);
    } catch (err: any) {
      console.error('Telemetry ingestion error:', err);
      if (isInitial) {
        setError(err.message || 'Error loading live air quality data');
      }
    } finally {
      if (isInitial) setLoading(false);
    }
  }, []);

  // Initial Load & Continuous Periodic Synchronization (Every 60s)
  useEffect(() => {
    fetchTelemetry(true);

    const syncInterval = setInterval(() => {
      fetchTelemetry(false);
    }, 60000); // 60-second periodic background polling for live updates

    return () => clearInterval(syncInterval);
  }, [fetchTelemetry]);

  // Handle region-wide municipal zone selection (highlights entire designated territory)
  const handleSelectZone = (zone: string) => {
    const nextZone = zone ? zone : null;
    setSelectedZone(nextZone);
    // Unset single hex isolation so the entire geographic region is highlighted
    setSelectedHexagon(null);
  };

  const handleSelectHexagon = (hex: HexagonData) => {
    setSelectedHexagon(hex);
    // Single-hex selection remains strictly isolated; do not force selectedZone
  };

  if (loading) {
    return (
      <div className="w-full h-screen flex flex-col items-center justify-center bg-[#070a12] text-white gap-4">
        <div className="relative flex items-center justify-center">
          <div className="w-16 h-16 rounded-full border-4 border-cyan-500/20 border-t-cyan-400 animate-spin" />
          <div className="absolute font-black text-xs text-cyan-400">VAYU</div>
        </div>
        <div className="flex flex-col items-center gap-1">
          <h2 className="text-base font-bold text-slate-200">Initializing WebGL Atmospheric Mesh</h2>
          <p className="text-xs text-slate-400">Compiling 72-hour rolling XGBoost inferences across NCT Delhi...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="w-full h-screen flex flex-col items-center justify-center bg-[#070a12] text-white p-6">
        <div className="glass-panel p-6 rounded-2xl max-w-md flex flex-col items-center text-center gap-3 border border-rose-500/30">
          <AlertCircle className="w-10 h-10 text-rose-500" />
          <h2 className="text-lg font-bold">Unable to Load Telemetry Snapshot</h2>
          <p className="text-xs text-slate-400">{error || 'Data is currently unavailable.'}</p>
          <button
            onClick={() => fetchTelemetry(true)}
            className="mt-3 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 rounded-xl text-xs font-bold transition shadow-lg"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <main className="relative w-full h-screen overflow-hidden bg-[#070a12]">
      {/* Top Header Bar with Live/Timeline Dynamic Weather Parameters */}
      <Header
        data={data}
        currentHour={currentHour}
        language={language}
        onLanguageToggle={() => setLanguage((l) => (l === 'en' ? 'hi' : 'en'))}
        selectedZone={selectedZone}
        onSelectZone={handleSelectZone}
      />

      {/* Main Full-Screen WebGL Hexagon Map with Complete Region-Wide Highlighting */}
      <AQIMap
        hexagons={data.hexagons}
        currentHour={currentHour}
        selectedHexagon={selectedHexagon}
        selectedZone={selectedZone}
        onSelectHexagon={handleSelectHexagon}
        language={language}
      />

      {/* Bottom Floating 72h Timeline Slider */}
      <ForecastSlider
        currentHour={currentHour}
        onHourChange={setCurrentHour}
        isPlaying={isPlaying}
        onTogglePlay={() => setIsPlaying((p) => !p)}
        speed={speed}
        onToggleSpeed={() => setSpeed((s) => (s === 1 ? 2 : 1))}
        forecastTimestamps={data.forecast_timestamps}
        language={language}
      />

      {/* Slide-in Inspector Drawer */}
      {selectedHexagon && (
        <InspectorDrawer
          hexagon={selectedHexagon}
          currentHour={currentHour}
          onClose={() => setSelectedHexagon(null)}
          forecastTimestamps={data.forecast_timestamps}
          language={language}
        />
      )}

      {/* Persistent AQI Categorical Legend */}
      <div className="absolute bottom-6 left-6 z-20 hidden lg:block pointer-events-auto">
        <div className="glass-panel p-3 rounded-2xl border border-white/10 shadow-2xl flex flex-col gap-1.5 min-w-[190px]">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            {language === 'en' ? 'CPCB AQI Index' : 'सीपीसीबी सूचकांक'}
          </span>
          <div className="flex flex-col gap-1">
            {AQI_CATEGORIES.map((cat) => (
              <div key={cat.label} className="flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full shadow-sm"
                    style={{ backgroundColor: cat.color }}
                  />
                  <span className="text-slate-300 font-medium">
                    {language === 'en' ? cat.label : cat.label_hi}
                  </span>
                </div>
                <span className="text-slate-400 font-mono text-[10px] tabular-nums">
                  {cat.min}-{cat.max === 999 ? '500+' : cat.max}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
