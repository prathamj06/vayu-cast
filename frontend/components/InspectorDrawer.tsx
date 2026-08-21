'use client';

import React, { useState } from 'react';
import {
  X,
  MapPin,
  Flame,
  Car,
  Factory,
  Tornado,
  Sparkles,
  HeartPulse,
  TrendingUp,
  AlertTriangle,
  Info,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { HexagonData } from '@/types';
import { getAQICategory, formatTimeOffset } from '@/lib/aqi-utils';

interface InspectorDrawerProps {
  hexagon: HexagonData | null;
  currentHour: number;
  onClose: () => void;
  language: 'en' | 'hi';
  forecastTimestamps?: string[];
}

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({
  hexagon,
  currentHour,
  onClose,
  language,
  forecastTimestamps = [],
}) => {
  const [activeTab, setActiveTab] = useState<'advisory' | 'attribution' | 'chart'>('advisory');

  if (!hexagon) return null;

  const currentAQI = hexagon.forecast_72h?.[currentHour] ?? hexagon.aqi;
  const initialAQI = hexagon.aqi;
  const category = getAQICategory(currentAQI);
  const attr = hexagon.source_attribution;

  // Build Recharts data series from 72h forecast array
  const chartData = (hexagon.forecast_72h || []).map((val, idx) => {
    let label = `+${idx}h`;
    if (forecastTimestamps[idx]) {
      const dt = new Date(forecastTimestamps[idx]);
      label = `${dt.getHours()}:00`;
    }
    return {
      hour: idx,
      label,
      aqi: val,
      isCurrent: idx === currentHour,
    };
  });

  return (
    <aside aria-label={language === 'en' ? 'Zone Air Quality Inspector Drawer' : 'क्षेत्र वायु गुणवत्ता विश्लेषक'} className="fixed inset-y-0 right-0 z-40 w-full sm:w-[440px] glass-panel-glow border-l border-white/15 p-5 flex flex-col justify-between overflow-y-auto shadow-2xl transition-all duration-300 animate-in slide-in-from-right">
      {/* Header & Close Button */}
      <div className="flex flex-col gap-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <MapPin className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-extrabold text-lg text-white tracking-tight">
                  {hexagon.zone_name}
                </h2>
                <span className="text-[10px] font-mono uppercase bg-slate-800/80 text-slate-300 border border-slate-700 px-1.5 py-0.5 rounded">
                  H3 Res 8
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                {hexagon.centroid[0].toFixed(4)}°N, {hexagon.centroid[1].toFixed(4)}°E
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition"
            title="Close Inspector"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Selected Hour AQI Score Card */}
        <div
          className="p-4 rounded-2xl border transition-all flex items-center justify-between shadow-xl"
          style={{
            backgroundColor: `${category.color}15`,
            borderColor: `${category.color}40`,
          }}
        >
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-300">
                {formatTimeOffset(currentHour)} AQI
              </span>
              {currentHour > 0 && (
                <span className="text-[10px] text-cyan-400 font-semibold">
                  (Live: {initialAQI})
                </span>
              )}
            </div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <span
                className="text-4xl font-black tabular-nums tracking-tighter"
                style={{ color: category.color }}
              >
                {currentAQI}
              </span>
              <span className="text-sm font-bold" style={{ color: category.color }}>
                {language === 'en' ? category.label : category.label_hi}
              </span>
            </div>
          </div>

          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg"
            style={{ backgroundColor: category.color }}
          >
            <HeartPulse className="w-6 h-6 text-slate-950 font-bold" />
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-white/5 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('advisory')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'advisory'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{language === 'en' ? 'AI Advisory' : 'एआई परामर्श'}</span>
          </button>
          <button
            onClick={() => setActiveTab('attribution')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'attribution'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Factory className="w-3.5 h-3.5" />
            <span>{language === 'en' ? 'Attribution' : 'प्रदूषण स्रोत'}</span>
          </button>
          <button
            onClick={() => setActiveTab('chart')}
            className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
              activeTab === 'chart'
                ? 'bg-cyan-500 text-slate-950 font-bold shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5" />
            <span>{language === 'en' ? '72h Curve' : '72h ग्राफ'}</span>
          </button>
        </div>

        {/* Tab 1: Gemini AI Multilingual Health Advisory */}
        {activeTab === 'advisory' && (
          <div className="flex flex-col gap-3 animate-in fade-in duration-200">
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-2">
              <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
                <Sparkles className="w-4 h-4 text-cyan-300" />
                <span>Google Gemini AI Health Intelligence</span>
              </div>

              {/* English Advisory */}
              <div className="bg-slate-900/70 p-3 rounded-xl border border-white/5">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                  English Health Directive
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-medium">
                  {hexagon.advisory_en || category.description}
                </p>
              </div>

              {/* Hindi Advisory */}
              <div className="bg-slate-900/70 p-3 rounded-xl border border-white/5">
                <div className="text-[10px] uppercase font-bold text-slate-400 mb-1">
                  हिंदी स्वास्थ्य सलाह (Hindi Directive)
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-medium">
                  {hexagon.advisory_hi || category.label_hi}
                </p>
              </div>
            </div>

            {/* General Health Action Precautions */}
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">
                  {language === 'en' ? 'Clinical Advisory: ' : 'चिकित्सीय सलाह: '}
                </span>
                <span>
                  {currentAQI > 200
                    ? (language === 'en' ? 'Wear N95/FFP2 respirators. Restrict outdoor physical exertion.' : 'N95/FFP2 मास्क लगाएं। बाहर शारीरिक व्यायाम से बचें।')
                    : (language === 'en' ? 'Satisfactory conditions for general population.' : 'सामान्य आबादी के लिए स्थिति सामान्य है।')}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Satellite & Physics Source Attribution */}
        {activeTab === 'attribution' && (
          <div className="flex flex-col gap-3 animate-in fade-in duration-200">
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-3">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
                  {language === 'en' ? 'Pollution Source Fingerprint' : 'प्रदूषण स्रोत विभाजन'}
                </span>
                <span className="text-[10px] text-cyan-400 font-mono">100% Normalized</span>
              </div>

              {/* Traffic */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-rose-400">
                    <Car className="w-3.5 h-3.5" />
                    {language === 'en' ? 'Vehicular Traffic' : 'वाहनों का धुआं'}
                  </span>
                  <span className="text-white font-mono tabular-nums">{attr.traffic}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-rose-500 transition-all duration-500 rounded-full"
                    style={{ width: `${attr.traffic}%` }}
                  />
                </div>
              </div>

              {/* Stubble Burning */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-amber-400">
                    <Flame className="w-3.5 h-3.5" />
                    {language === 'en' ? 'Agricultural Stubble' : 'पराली जलाना'}
                  </span>
                  <span className="text-white font-mono tabular-nums">{attr.stubble}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500 transition-all duration-500 rounded-full"
                    style={{ width: `${attr.stubble}%` }}
                  />
                </div>
              </div>

              {/* Industrial Emissions */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-indigo-400">
                    <Factory className="w-3.5 h-3.5" />
                    {language === 'en' ? 'Industrial Emissions' : 'औद्योगिक उत्सर्जन'}
                  </span>
                  <span className="text-white font-mono tabular-nums">{attr.industry}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 transition-all duration-500 rounded-full"
                    style={{ width: `${attr.industry}%` }}
                  />
                </div>
              </div>

              {/* Road Dust */}
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="flex items-center gap-1.5 text-emerald-400">
                    <Tornado className="w-3.5 h-3.5" />
                    {language === 'en' ? 'Road Dust & Resuspension' : 'सड़क की धूल'}
                  </span>
                  <span className="text-white font-mono tabular-nums">{attr.dust}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 transition-all duration-500 rounded-full"
                    style={{ width: `${attr.dust}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-white/5 text-[11px] text-slate-400 flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <p>
                {language === 'en'
                  ? 'Source apportionment calculated via spatial distance decay, wind vectors, and seasonal agricultural emissions modeling.'
                  : 'स्रोत विभाजन स्थानिक दूरी, वायु प्रवाह और मौसमी कृषि उत्सर्जन मॉडल पर आधारित है।'}
              </p>
            </div>
          </div>
        )}

        {/* Tab 3: 72-Hour XGBoost Forecast Curve */}
        {activeTab === 'chart' && (
          <div className="flex flex-col gap-3 animate-in fade-in duration-200">
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex flex-col gap-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-300 uppercase tracking-wider text-[11px]">
                  {language === 'en' ? '72-Hour AQI Trajectory' : '72 घंटे का AQI प्रक्षेपवक्र'}
                </span>
                <span className="text-[10px] text-cyan-400 font-mono">XGBoost v3</span>
              </div>

              <div className="h-44 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id="aqiAreaGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.6} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="hour"
                      stroke="#64748b"
                      fontSize={10}
                      tickLine={false}
                      tickFormatter={(val) => `+${val}h`}
                      interval={11}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={10}
                      tickLine={false}
                      domain={[0, 450]}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const p = payload[0].payload;
                          const c = getAQICategory(p.aqi);
                          return (
                            <div className="glass-panel p-2.5 rounded-xl border border-white/15 text-xs shadow-2xl">
                              <div className="text-[10px] text-slate-400 font-medium">
                                +{p.hour}h Forecast
                              </div>
                              <div className="flex items-baseline gap-1.5 mt-0.5">
                                <span className="font-black text-sm" style={{ color: c.color }}>
                                  AQI {p.aqi}
                                </span>
                                <span className="text-[10px]" style={{ color: c.color }}>
                                  {language === 'en' ? c.label : c.label_hi}
                                </span>
                              </div>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <ReferenceLine y={100} stroke="#ffff00" strokeDasharray="3 3" opacity={0.4} />
                    <ReferenceLine y={200} stroke="#ff0000" strokeDasharray="3 3" opacity={0.4} />
                    <ReferenceLine y={300} stroke="#8f3f97" strokeDasharray="3 3" opacity={0.4} />
                    <Area
                      type="monotone"
                      dataKey="aqi"
                      stroke="#06b6d4"
                      strokeWidth={2.5}
                      fillOpacity={1}
                      fill="url(#aqiAreaGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Legend of Risk Thresholds */}
              <div className="flex items-center justify-between text-[9px] text-slate-400 font-semibold pt-1 border-t border-white/5">
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00E400]" /> 0-50 Good
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FFFF00]" /> 51-100 Mod
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#FF0000]" /> 151-200 Unhealthy
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#7E0023]" /> 301+ Haz
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="pt-4 border-t border-white/10 text-[10px] text-slate-500 font-medium flex items-center justify-between">
        <span>VAYUCAST AI Core • CPCB Telemetry</span>
        <span className="font-mono">{hexagon.hex_id}</span>
      </div>
    </aside>
  );
};
