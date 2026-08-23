'use client';

import React from 'react';
import { Wind, Activity, Thermometer, Droplets, Compass, Layers, Globe, ShieldAlert, Sparkles } from 'lucide-react';
import { GridPayload } from '@/types';
import { getAQICategory } from '@/lib/aqi-utils';

interface HeaderProps {
  data: GridPayload | null;
  currentHour?: number;
  language: 'en' | 'hi';
  onLanguageToggle: () => void;
  selectedZone: string | null;
  onSelectZone: (zone: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  data,
  currentHour = 0,
  language,
  onLanguageToggle,
  selectedZone,
  onSelectZone,
}) => {
  const avgAQI = data?.nct_average_aqi ?? 142;
  const category = getAQICategory(avgAQI);
  
  // Continuously dynamically resolves meteorological metrics for the current active forecast/live hour
  const baseWeather = data?.weather_summary;
  const activeWeather = baseWeather?.hourly?.[currentHour] || baseWeather;

  const zones = data?.zones_summary ? Object.keys(data.zones_summary) : [];

  return (
    <header className="absolute top-4 left-4 right-4 z-30 pointer-events-none flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
      {/* Brand & Average Badge */}
      <div className="flex items-center gap-3 pointer-events-auto">
        <div className="glass-panel px-4 py-2.5 rounded-2xl flex items-center gap-3 border border-white/10 shadow-2xl">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Wind className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold tracking-wider text-xl bg-clip-text text-transparent bg-gradient-to-r from-cyan-300 via-sky-200 to-blue-400">
                VAYU
              </span>
              <span className="text-[10px] uppercase font-bold tracking-widest bg-cyan-950/80 text-cyan-400 border border-cyan-700/50 px-1.5 py-0.5 rounded-md">
                NCT Delhi
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium flex items-center gap-1.5">
              <span>{language === 'en' ? 'Urban Air Intelligence • 72h Forecast' : 'शहरी वायु गुणवत्ता मंच • 72 घंटे का पूर्वानुमान'}</span>
              {data?.generated_at && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="text-cyan-400/90 font-mono text-[10px]">{data.generated_at}</span>
                </>
              )}
            </p>
          </div>
        </div>

        {/* NCT Delhi Average AQI Pill */}
        <div className="glass-panel px-4 py-2 rounded-2xl flex items-center gap-3 border border-white/10 shadow-xl hidden sm:flex">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {language === 'en' ? 'NCT Average' : 'एनसीटी औसत'}
            </span>
            <div className="flex items-baseline gap-1.5">
              <span
                className="text-2xl font-black tabular-nums tracking-tight"
                style={{ color: category.color }}
              >
                {Math.round(avgAQI)}
              </span>
              <span className="text-xs font-semibold" style={{ color: category.color }}>
                {language === 'en' ? category.label : category.label_hi}
              </span>
            </div>
          </div>
          <div
            className="w-3 h-3 rounded-full animate-pulse shadow-md"
            style={{ backgroundColor: category.color, boxShadow: `0 0 12px ${category.color}` }}
          />
        </div>
      </div>

      {/* Atmospheric Telemetry & Interactive Controls */}
      <div className="flex items-center gap-2 pointer-events-auto flex-wrap justify-end">
        {/* Dynamic Live Weather Metrics Synchronized with Timeline Hour */}
        {activeWeather && (
          <div className="glass-panel px-3.5 py-2 rounded-2xl flex items-center gap-4 text-xs text-slate-300 hidden lg:flex border border-white/10 transition-all duration-300">
            <div className="flex items-center gap-1.5" title="Surface Temperature">
              <Thermometer className="w-3.5 h-3.5 text-amber-400" />
              <span className="tabular-nums font-semibold">{activeWeather.temp}°C</span>
            </div>
            <div className="flex items-center gap-1.5" title="Relative Humidity">
              <Droplets className="w-3.5 h-3.5 text-blue-400" />
              <span className="tabular-nums font-semibold">{activeWeather.humidity}%</span>
            </div>
            <div className="flex items-center gap-1.5" title="Wind Velocity & Direction">
              <Compass className="w-3.5 h-3.5 text-emerald-400" />
              <span className="tabular-nums font-semibold">{activeWeather.wind_speed} km/h ({activeWeather.wind_dir}°)</span>
            </div>
            <div className="flex items-center gap-1.5" title="Atmospheric Boundary Layer Height">
              <Layers className="w-3.5 h-3.5 text-purple-400" />
              <span className="tabular-nums font-semibold">BLH {activeWeather.blh}m</span>
            </div>
          </div>
        )}

        {/* Zone Selector */}
        {zones.length > 0 && (
          <div className="glass-panel rounded-2xl px-2 py-1 flex items-center border border-white/10">
            <select
              value={selectedZone || ''}
              onChange={(e) => onSelectZone(e.target.value)}
              aria-label={language === 'en' ? 'Select Municipal Zone' : 'नगर निगम क्षेत्र चुनें'}
              className="bg-transparent text-xs font-semibold text-slate-200 py-1.5 px-2 rounded-xl focus:outline-none cursor-pointer border-none"
            >
              <option value="" className="bg-slate-900 text-slate-300">
                {language === 'en' ? 'All Municipal Zones' : 'सभी नगर निगम क्षेत्र'}
              </option>
              {zones.map((z) => (
                <option key={z} value={z} className="bg-slate-900 text-slate-200">
                  {z}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Language Switcher */}
        <button
          onClick={onLanguageToggle}
          className="glass-panel px-3 py-2 rounded-2xl flex items-center gap-1.5 text-xs font-bold text-slate-200 hover:text-white hover:bg-white/10 transition border border-white/10 shadow-lg"
          title="Toggle English / Hindi"
        >
          <Globe className="w-3.5 h-3.5 text-cyan-400" />
          <span>{language === 'en' ? 'हिंदी' : 'English'}</span>
        </button>
      </div>
    </header>
  );
};
