import { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine
} from 'recharts';
import { fetchProvinceHistory } from '../api';
import type { YearRecord } from '../types';

interface Props {
  provinceName: string;
  provinceDisplay: string;
}

export default function ProvinceDetail({ provinceName, provinceDisplay }: Props) {
  const [data, setData] = useState<YearRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'yield' | 'meteo' | 'ndvi' | 'soil' | 'table'>('yield');

  useEffect(() => {
    setLoading(true);
    fetchProvinceHistory(provinceName)
      .then(setData)
      .finally(() => setLoading(false));
  }, [provinceName]);

  if (loading) return <div className="loading">Yükleniyor...</div>;
  if (!data.length) return <div className="empty">Veri bulunamadı</div>;

  const soil = data[0];
  const avgYield = (data.reduce((s, d) => s + d.actual_yield, 0) / data.length).toFixed(1);
  const maxY = Math.max(...data.map(d => d.actual_yield));
  const minY = Math.min(...data.map(d => d.actual_yield));
  const holdout = data.filter(d => d.predicted_yield !== null);
  const r2Text = holdout.length > 0 ? 'Holdout 2020-2024 dahil' : '';

  return (
    <div className="province-detail">
      <h2>{provinceDisplay} — Buğday Verimi Analizi</h2>

      {/* Özet kartlar */}
      <div className="stat-cards">
        <div className="card"><div className="card-label">Ortalama Verim</div><div className="card-value">{avgYield} kg/da</div></div>
        <div className="card"><div className="card-label">En Yüksek</div><div className="card-value">{maxY.toFixed(0)} kg/da</div></div>
        <div className="card"><div className="card-label">En Düşük</div><div className="card-value">{minY.toFixed(0)} kg/da</div></div>
        <div className="card"><div className="card-label">Veri Yılı</div><div className="card-value">{data.length}</div></div>
        {soil.soil_phh2o && <div className="card"><div className="card-label">Toprak pH</div><div className="card-value">{soil.soil_phh2o}</div></div>}
        {soil.soil_clay && <div className="card"><div className="card-label">Kil %</div><div className="card-value">{soil.soil_clay?.toFixed(1)}</div></div>}
      </div>

      {/* Sekmeler */}
      <div className="tabs">
        {(['yield','meteo','ndvi','soil','table'] as const).map(t => (
          <button key={t} className={tab === t ? 'tab active' : 'tab'} onClick={() => setTab(t)}>
            {{ yield:'Verim', meteo:'Meteoroloji', ndvi:'NDVI/EVI', soil:'Toprak', table:'Tablo' }[t]}
          </button>
        ))}
      </div>

      {/* Verim grafiği */}
      {tab === 'yield' && (
        <div className="chart-section">
          <h3>Gerçek ve Tahmin Edilen Verim (2005-2024)</h3>
          {r2Text && <p className="subtitle">{r2Text}</p>}
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis unit=" kg/da" />
              <Tooltip formatter={(v: number) => `${v?.toFixed(1)} kg/da`} />
              <Legend />
              <ReferenceLine x={2020} stroke="#ef4444" strokeDasharray="4 4" label="Holdout" />
              <Line type="monotone" dataKey="actual_yield" name="Gerçek Verim" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="predicted_yield" name="Tahmin" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>

          <h3 style={{marginTop:'2rem'}}>Yıllık Verim Değişimi (Bar)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis unit=" kg/da" />
              <Tooltip formatter={(v: number) => `${v?.toFixed(1)} kg/da`} />
              <ReferenceLine y={Number(avgYield)} stroke="#6366f1" strokeDasharray="4 4" label="Ort" />
              <Bar dataKey="actual_yield" name="Verim" fill="#16a34a" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Meteoroloji */}
      {tab === 'meteo' && (
        <div className="chart-section">
          <h3>Sezonluk Yağış (Eki-Tem)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis unit=" mm" />
              <Tooltip />
              <Bar dataKey="rain_sum" name="Toplam Yağış" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>

          <h3 style={{marginTop:'2rem'}}>Ortalama Sıcaklık & MAM Sıcaklık</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis unit=" °C" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="tmean" name="Sezon Ort °C" stroke="#ef4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="mam_tmean" name="MAM Ort °C" stroke="#f97316" strokeWidth={2} strokeDasharray="5 5" dot={false} />
            </LineChart>
          </ResponsiveContainer>

          <h3 style={{marginTop:'2rem'}}>Büyüme Derece Günü (GDD)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="gdd_season" name="Sezon GDD" fill="#8b5cf6" />
              <Bar dataKey="gdd_mam" name="MAM GDD" fill="#a78bfa" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* NDVI/EVI */}
      {tab === 'ndvi' && (
        <div className="chart-section">
          <h3>NDVI ve EVI (MODIS Uydu)</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="harvest_year" />
              <YAxis domain={[0, 0.8]} />
              <Tooltip formatter={(v: number) => v?.toFixed(4)} />
              <Legend />
              <Line type="monotone" dataKey="ndvi_max" name="NDVI Max" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="ndvi_mean" name="NDVI Ort" stroke="#4ade80" strokeWidth={2} strokeDasharray="5 5" dot={false} />
              <Line type="monotone" dataKey="evi_mean" name="EVI Ort" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Toprak */}
      {tab === 'soil' && (
        <div className="chart-section">
          <h3>Toprak Özellikleri (Statik — SoilGrids)</h3>
          <div className="soil-grid">
            <SoilCard label="Kil" value={soil.soil_clay} unit="g/kg" color="#b45309" />
            <SoilCard label="Kum" value={soil.soil_sand} unit="g/kg" color="#d97706" />
            <SoilCard label="Silt" value={null} unit="g/kg" color="#92400e" />
            <SoilCard label="Org. Karbon (SOC)" value={soil.soil_soc} unit="dg/kg" color="#166534" />
            <SoilCard label="pH (H₂O)" value={soil.soil_phh2o} unit="" color="#1d4ed8" />
          </div>
        </div>
      )}

      {/* Tablo */}
      {tab === 'table' && (
        <div className="chart-section">
          <h3>Ham Veri Tablosu</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Yıl</th><th>Gerçek (kg/da)</th><th>Tahmin</th><th>Hata kg</th><th>Hata %</th>
                  <th>Yağış mm</th><th>Sıcaklık °C</th><th>GDD Sezon</th><th>NDVI Max</th>
                </tr>
              </thead>
              <tbody>
                {data.map(r => (
                  <tr key={r.harvest_year} className={r.harvest_year >= 2020 ? 'holdout-row' : ''}>
                    <td>{r.harvest_year}{r.harvest_year >= 2020 ? ' *' : ''}</td>
                    <td>{r.actual_yield.toFixed(1)}</td>
                    <td>{r.predicted_yield?.toFixed(1) ?? '—'}</td>
                    <td style={{ color: r.error_kg && r.error_kg < 0 ? '#ef4444' : '#16a34a' }}>
                      {r.error_kg?.toFixed(1) ?? '—'}
                    </td>
                    <td style={{ color: r.error_pct && Math.abs(r.error_pct) > 15 ? '#ef4444' : 'inherit' }}>
                      {r.error_pct?.toFixed(1) ?? '—'}%
                    </td>
                    <td>{r.rain_sum?.toFixed(0) ?? '—'}</td>
                    <td>{r.tmean?.toFixed(1) ?? '—'}</td>
                    <td>{r.gdd_season?.toFixed(0) ?? '—'}</td>
                    <td>{r.ndvi_max?.toFixed(3) ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="table-note">* Holdout dönemi (2020-2024) — model bu yılları görmedi</p>
          </div>
        </div>
      )}
    </div>
  );
}

function SoilCard({ label, value, unit, color }: { label: string; value: number | null; unit: string; color: string }) {
  return (
    <div className="soil-card" style={{ borderLeftColor: color }}>
      <div className="soil-label">{label}</div>
      <div className="soil-value" style={{ color }}>{value != null ? `${value.toFixed(2)} ${unit}` : '—'}</div>
    </div>
  );
}
