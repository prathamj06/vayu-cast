export interface SourceAttribution {
  traffic: number;
  stubble: number;
  industry: number;
  dust: number;
}

export interface HexagonData {
  hex_id: string;
  centroid: [number, number]; // [lat, lon]
  zone_name: string;
  aqi: number;
  color_rgb: [number, number, number, number]; // [R, G, B, Alpha]
  source_attribution: SourceAttribution;
  advisory_en: string;
  advisory_hi: string;
  forecast_72h: number[]; // Array of 72 hourly AQI predicted integers
  hourly_weather?: {
    temp: number[];
    humidity: number[];
    wind_speed: number[];
    wind_dir: number[];
    blh: number[];
  };
}

export interface WeatherSummary {
  temp: number;
  humidity: number;
  wind_speed: number;
  wind_dir: number;
  blh: number;
}

export interface TelemetryHealth {
  is_stale: boolean;
  source: string;
  active_count: number;
  ingestion_mode: string;
  staleness_reason?: string;
  timestamp?: string;
  seasonal_factor?: number;
}

export interface CalibrationMetrics {
  mean_bias_error: number;
  forecast_accuracy_pct: number;
  rolling_rmse: number;
  total_verification_cycles: number;
  last_recalibration_time?: string;
}

export interface GridPayload {
  timestamp: string;
  generated_at: string;
  nct_average_aqi: number;
  nct_category: string;
  dominant_pollutant: string;
  active_stations_count: number;
  total_hexagons: number;
  telemetry_health?: TelemetryHealth;
  calibration_metrics?: CalibrationMetrics;
  forecast_timestamps: string[];
  weather_summary?: WeatherSummary;
  zones_summary: {
    [zone: string]: {
      current_aqi: number;
      category?: string;
      dominant_source: string;
      advisory_en: string;
      advisory_hi: string;
    };
  };
  hexagons: HexagonData[];
}

export interface AQICategory {
  label: string;
  label_hi: string;
  min: number;
  max: number;
  color: string;
  rgb: [number, number, number, number];
  description: string;
  textColor: string;
}
