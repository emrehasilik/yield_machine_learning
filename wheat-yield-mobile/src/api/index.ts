import axios from 'axios';
import type { Province, YearRecord, ModelVersion, YearlyTrend } from '../types';

// Bilgisayarının IP'si — expo telefondan bağlanınca localhost çalışmaz
// "ipconfig" ile IPv4 adresini bul ve buraya yaz
const BASE_URL = 'http://172.20.10.4:3001/api';

const api = axios.create({ baseURL: BASE_URL, timeout: 10000 });

export const fetchProvinces = (): Promise<Province[]> =>
  api.get('/provinces').then(r => r.data);

export const fetchProvinceHistory = (name: string): Promise<YearRecord[]> =>
  api.get(`/provinces/${name}/history`).then(r => r.data);

export const fetchModelVersions = (): Promise<ModelVersion[]> =>
  api.get('/model/versions').then(r => r.data);

export const fetchYearlyTrend = (): Promise<YearlyTrend[]> =>
  api.get('/model/yearly-trend').then(r => r.data);
