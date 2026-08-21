'use client';

import React, { useEffect, useRef } from 'react';
import { Play, Pause, RotateCcw, ChevronLeft, ChevronRight, FastForward, Clock } from 'lucide-react';
import { formatTimeOffset } from '@/lib/aqi-utils';

interface ForecastSliderProps {
  currentHour: number;
  onHourChange: (hour: number) => void;
  isPlaying: boolean;
  onTogglePlay: () => void;
  speed: number;
  onToggleSpeed: () => void;
  forecastTimestamps?: string[];
  language: 'en' | 'hi';
}

export const ForecastSlider: React.FC<ForecastSliderProps> = ({
  currentHour,
  onHourChange,
  isPlaying,
  onTogglePlay,
  speed,
  onToggleSpeed,
  forecastTimestamps = [],
  language,
}) => {
  const maxHours = Math.max(71, forecastTimestamps.length - 1);

  // Automated playback loop
  useEffect(() => {
    if (!isPlaying) return;

    const intervalMs = speed === 2 ? 500 : 1000;
    const timer = setInterval(() => {
      onHourChange((currentHour + 1) % (maxHours + 1));
    }, intervalMs);

    return () => clearInterval(timer);
  }, [isPlaying, currentHour, maxHours, speed, onHourChange]);

  const formatTimestamp = (idx: number) => {
    if (forecastTimestamps[idx]) {
      const d = new Date(forecastTimestamps[idx]);
      return d.toLocaleDateString(language === 'hi' ? 'hi-IN' : 'en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    }
    return `Hour +${idx}`;
  };

  return (
    <div className="absolute bottom-6 left-4 right-4 md:left-1/2 md:-translate-x-1/2 md:max-w-2xl z-30 pointer-events-auto">
      <div className="glass-panel-glow px-5 py-4 rounded-3xl border border-white/15 shadow-2xl flex flex-col gap-3">
        {/* Top Info Bar */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950/70 border border-cyan-700/50 px-2.5 py-0.5 rounded-full text-[11px]">
              <Clock className="w-3 h-3 text-cyan-300" />
              {currentHour === 0 ? (language === 'en' ? 'Live Telemetry' : 'लाइव टेलीमेट्री') : formatTimeOffset(currentHour)}
            </span>
            <span className="text-slate-400 font-medium tabular-nums hidden sm:inline">
              {formatTimestamp(currentHour)}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onHourChange(0)}
              disabled={currentHour === 0}
              className="text-[11px] font-semibold text-slate-400 hover:text-cyan-300 disabled:opacity-30 disabled:hover:text-slate-400 flex items-center gap-1 transition px-2 py-1 rounded-lg hover:bg-white/5"
              title="Reset to Live Telemetry"
            >
              <RotateCcw className="w-3 h-3" />
              <span>{language === 'en' ? 'Now' : 'अभी'}</span>
            </button>
            <button
              onClick={onToggleSpeed}
              className="text-[11px] font-bold text-slate-300 hover:text-cyan-300 bg-white/5 hover:bg-white/10 border border-white/10 px-2 py-0.5 rounded-md transition"
              title="Toggle Playback Speed"
            >
              {speed}x
            </button>
          </div>
        </div>

        {/* Timeline Range Scrubber */}
        <div className="relative flex items-center">
          <input
            type="range"
            min={0}
            max={maxHours}
            value={currentHour}
            onChange={(e) => onHourChange(Number(e.target.value))}
            aria-label={language === 'en' ? '72-Hour Forecast Timeline Slider' : '72 घंटे का पूर्वानुमान टाइमलाइन स्लाइडर'}
            className="w-full h-2.5 bg-slate-800/90 rounded-lg appearance-none cursor-pointer accent-cyan-400 focus:outline-none shadow-inner"
            style={{
              background: `linear-gradient(to right, #06b6d4 ${(currentHour / maxHours) * 100}%, #1e293b ${(currentHour / maxHours) * 100}%)`
            }}
          />
        </div>

        {/* Playback Controls & Markers */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onHourChange(Math.max(0, currentHour - 1))}
              disabled={currentHour === 0}
              className="p-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 disabled:opacity-30 transition border border-white/5"
              title="Step -1 Hour"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <button
              onClick={onTogglePlay}
              className="px-4 py-1.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold flex items-center gap-1.5 shadow-lg shadow-cyan-500/25 transition active:scale-95"
              title={isPlaying ? 'Pause' : 'Play 72h Timeline'}
            >
              {isPlaying ? (
                <>
                  <Pause className="w-4 h-4" />
                  <span className="text-xs">{language === 'en' ? 'Pause' : 'रोकें'}</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span className="text-xs">{language === 'en' ? 'Animate 72h' : 'पूर्वानुमान चलाएं'}</span>
                </>
              )}
            </button>

            <button
              onClick={() => onHourChange(Math.min(maxHours, currentHour + 1))}
              disabled={currentHour === maxHours}
              className="p-1.5 rounded-xl bg-white/5 hover:bg-white/15 text-slate-300 disabled:opacity-30 transition border border-white/5"
              title="Step +1 Hour"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* Quick Step Indicators */}
          <div className="flex items-center gap-1 text-[10px] text-slate-400 font-bold">
            <button
              onClick={() => onHourChange(0)}
              className={`px-1.5 py-0.5 rounded transition ${currentHour === 0 ? 'bg-cyan-500 text-slate-950 font-extrabold' : 'hover:text-slate-200'}`}
            >
              0h
            </button>
            <button
              onClick={() => onHourChange(12)}
              className={`px-1.5 py-0.5 rounded transition ${currentHour === 12 ? 'bg-cyan-500 text-slate-950 font-extrabold' : 'hover:text-slate-200'}`}
            >
              +12h
            </button>
            <button
              onClick={() => onHourChange(24)}
              className={`px-1.5 py-0.5 rounded transition ${currentHour === 24 ? 'bg-cyan-500 text-slate-950 font-extrabold' : 'hover:text-slate-200'}`}
            >
              +24h
            </button>
            <button
              onClick={() => onHourChange(48)}
              className={`px-1.5 py-0.5 rounded transition ${currentHour === 48 ? 'bg-cyan-500 text-slate-950 font-extrabold' : 'hover:text-slate-200'}`}
            >
              +48h
            </button>
            <button
              onClick={() => onHourChange(71)}
              className={`px-1.5 py-0.5 rounded transition ${currentHour === 71 ? 'bg-cyan-500 text-slate-950 font-extrabold' : 'hover:text-slate-200'}`}
            >
              +72h
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
