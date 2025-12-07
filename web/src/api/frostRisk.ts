import { apiGet } from "./client";

export interface CropStage {
  probability: number;
  frostProbabilityIndex: number;
  lt10: number;
  lt90: number;
  parameterA: number;
  parameterB: number;
}

export interface Crop {
  name: string;
  variety: string;
  stages: Record<string, CropStage>;
}

export interface CimisData {
  stationId: string;
  stationName: string;
  date: string; // ISO string; you can parse to Date in UI
  airTempMin: number;
  airTempMax: number;
  dewPointMin: number;
  dewPointMax: number;
  humidityMin: number;
  humidityMax: number;
  windSpeedAvg: number;
  et0: number;
  raw: Record<string, unknown>;
}

export interface FeatureProperties {
  temp: number;
  riskLevel: string;
  location: string;
  crop: Crop;
  cimis: CimisData;
}

export interface PointGeometry {
  type: "Point";
  coordinates: [number, number]; // [lon, lat]
}

export interface FrostRiskFeature {
  type: "Feature";
  properties: FeatureProperties;
  geometry: PointGeometry;
}

export interface FrostRiskQuery {
  lat: number;
  lon: number;
  date: string;   // 'YYYY-MM-DD'
  crop: string;
  variety: string;
  stationId?: string;
}

/**
 * Fetches frost risk data from the backend.
 * 
 * Usage:
 * const frost = await fetchFrostRisk({
 *   lat: 37.2,
 *   lon: -120.3,
 *   date: "2025-02-18",
 *   crop: "almond",
 *   variety: "nonpareil",
 *   stationId: "170",
 * });
 */
export async function fetchFrostRisk(params: FrostRiskQuery) {
  const search = new URLSearchParams({
    lat: String(params.lat),
    lon: String(params.lon),
    date: params.date,
    crop: params.crop,
    variety: params.variety,
    ...(params.stationId ? { stationId: params.stationId } : {}),
  });
  return apiGet<FrostRiskFeature>(`/frost-risk?${search.toString()}`);
}
