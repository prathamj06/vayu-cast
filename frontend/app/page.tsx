'use client';

import React, { useState, useEffect } from 'react';
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

  // Fetch Static Grid Snapshot
  useEffect(() => {
    async function loadGridData() {
      try {
        setLoading(true);
        // 1. Fetch from /api/grid (which resolves the latest single-commit data branch)
        let res = await fetch('/api/grid');
        
        if (!res.ok) {
          // 2. Fallback to bundled public static JSON
          res = await fetch('/data/delhi_current_grid.json');
        }

        if (!res.ok) {
          throw new Error('Failed to load Delhi AQI mesh data');
        }

        const jsonData = await res.json();
        setData(jsonData);
      } catch (err: any) {
        console.error('Error fetching grid snapshot:', err);
        setError(err.message || 'Error loading air quality data');
      } finally {
        setLoading(false);
      }
    }

    loadGridData();
  }, []);

  // When selectedZone changes, select a representative hexagon for that zone
  const handleSelectZone = (zone: string) => {
    setSelectedZone(zone);
    if (!zone) {
      setSelectedHexagon(null);
      return;
    }
    if (data?.hexagons) {
      const match = data.hexagons.find((h) => h.zone_name === zone);
      if (match) {
        setSelectedHexagon(match);
      }
    }
  };

  const handleSelectHexagon = (hex: HexagonData) => {
    setSelectedHexagon(hex);
    setSelectedZone(hex.zone_name);
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
            onClick={() => window.location.reload()}
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
      {/* Top Header Bar */}
      <Header
        data={data}
        language={language}
        onLanguageToggle={() => setLanguage((l) => (l === 'en' ? 'hi' : 'en'))}
        selectedZone={selectedZone}
        onSelectZone={handleSelectZone}
      />

      {/* Main Full-Screen WebGL Hexagon Map */}
      <AQIMap
        hexagons={data.hexagons}
        currentHour={currentHour}
        selectedHexagon={selectedHexagon}
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
      <InspectorDrawer
        hexagon={selectedHexagon}
        currentHour={currentHour}
        onClose={() => setSelectedHexagon(null)}
        language={language}
        forecastTimestamps={data.forecast_timestamps}
      />

      {/* Floating CPCB Color Scale Legend (Bottom Left) */}
      <div className="absolute bottom-6 left-4 z-20 pointer-events-auto hidden md:block">
        <div className="glass-panel p-3 rounded-2xl border border-white/10 shadow-2xl flex flex-col gap-2">
          <div className="flex items-center justify-between text-[10px] font-bold text-slate-300 uppercase tracking-wider border-b border-white/10 pb-1">
            <span>{language === 'en' ? 'AQI Scale (CPCB/EPA)' : 'AQI मानक (सीपीसीबी)'}</span>
            <span className="text-cyan-400">PM2.5</span>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] font-medium text-slate-300">
            {AQI_CATEGORIES.map((cat) => (
              <div key={cat.label} className="flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full shadow-sm"
                  style={{ backgroundColor: cat.color }}
                />
                <span className="tabular-nums font-mono text-[9px] text-slate-400">
                  {cat.min}-{cat.max === 999 ? '300+' : cat.max}:
                </span>
                <span className="font-semibold text-slate-200">
                  {language === 'en' ? cat.label.split(' ')[0] : cat.label_hi.split(' ')[0]}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
