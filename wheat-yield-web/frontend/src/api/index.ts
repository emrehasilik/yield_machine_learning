import axios from 'axios';
import type { Province, YearRecord, ModelVersion, Prediction, YearlyTrend, RegionError, MapYearData } from '../types';

const api = axios.create({ baseURL: 'http://localhost:3001/api' });

export const fetchProvinces = (): Promise<Province[]> =>
  api.get('/provinces').then(r => r.data);

export const fetchProvinceHistory = (name: string): Promise<YearRecord[]> =>
  api.get(`/provinces/${name}/history`).then(r => r.data);

export const fetchModelVersions = (): Promise<ModelVersion[]> =>
  api.get('/model/versions').then(r => r.data);

export const fetchPredictions = (): Promise<Prediction[]> =>
  api.get('/model/predictions').then(r => r.data);

export const fetchYearlyTrend = (): Promise<YearlyTrend[]> =>
  api.get('/model/yearly-trend').then(r => r.data);

export const fetchErrorByRegion = (): Promise<RegionError[]> =>
  api.get('/model/error-by-region').then(r => r.data);

export const fetchMapYear = (year: number): Promise<MapYearData[]> =>
  api.get(`/map/${year}`).then(r => r.data);
