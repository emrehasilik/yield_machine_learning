import { useEffect, useState } from 'react';
import TurkeyMap from '../components/TurkeyMap';
import type { MetricKey } from '../components/TurkeyMap';
import ProvinceDetail from '../components/ProvinceDetail';
import { fetchProvinces, fetchMapYear } from '../api';
import type { Province, MapYearData } from '../types';

const METRICS: { key: MetricKey; label: string; icon: string }[] = [
  { key: 'yield_kg_dekar', label: 'Verim',       icon: '🌾' },
  { key: 'rain_sum',       label: 'Yağış',        icon: '🌧️' },
  { key: 'tmean',          label: 'Sıcaklık',     icon: '🌡️' },
  { key: 'ndvi_max',       label: 'NDVI',         icon: '🛰️' },
  { key: 'gdd_season',     label: 'GDD',          icon: '☀️' },
  { key: 'hot_days_30',    label: 'Sıcak Günler', icon: '🔥' },
];

const YEARS = Array.from({ length: 20 }, (_, i) => 2024 - i);

export default function MapPage() {
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [mapData, setMapData] = useState<MapYearData[]>([]);
  const [year, setYear] = useState(2023);
  const [metric, setMetric] = useState<MetricKey>('yield_kg_dekar');
  const [selected, setSelected] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetchProvinces().then(setProvinces); }, []);

  useEffect(() => {
    setLoading(true);
    fetchMapYear(year).then(setMapData).finally(() => setLoading(false));
  }, [year]);

  const selectedProv = provinces.find(p => p.name_norm === selected);

  // Seçili yıl için harita istatistikleri
  const vals = mapData.map(d => d[metric] as number).filter(v => v != null && !isNaN(v));
  const avg = vals.length ? (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1) : '—';
  const max = vals.length ? Math.max(...vals).toFixed(1) : '—';
  const min = vals.length ? Math.min(...vals).toFixed(1) : '—';

  const topProv = [...mapData]
    .filter(d => (d[metric] as number) != null)
    .sort((a, b) => (b[metric] as number) - (a[metric] as number))
    .slice(0, 5);

  return (
    <div className="map-page">
      {/* Kontroller */}
      <div className="map-controls">
        <div className="control-group">
          <label>📅 Yıl</label>
          <div className="year-buttons">
            {YEARS.map(y => (
              <button key={y} className={year === y ? 'year-btn active' : 'year-btn'} onClick={() => setYear(y)}>
                {y}
              </button>
            ))}
          </div>
        </div>
        <div className="control-group">
          <label>📊 Gösterge</label>
          <div className="metric-buttons">
            {METRICS.map(m => (
              <button key={m.key} className={metric === m.key ? 'metric-btn active' : 'metric-btn'} onClick={() => setMetric(m.key)}>
                {m.icon} {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="map-layout">
        {/* Sol: Harita + istatistik */}
        <div className="map-left">
          <div className="map-header">
            <h2>Türkiye — {year}</h2>
            <div className="map-stats">
              <span className="map-stat"><strong>{avg}</strong> Ort.</span>
              <span className="map-stat"><strong>{max}</strong> Max</span>
              <span className="map-stat"><strong>{min}</strong> Min</span>
            </div>
          </div>

          {loading ? (
            <div className="map-loading">Yükleniyor...</div>
          ) : (
            <TurkeyMap
              data={mapData}
              selectedMetric={metric}
              selectedProvince={selected}
              onSelect={setSelected}
            />
          )}

          {/* Top 5 */}
          <div className="top5">
            <h4>🏆 En Yüksek 5 İl</h4>
            {topProv.map((p, i) => (
              <div
                key={p.name_norm}
                className={selected === p.name_norm ? 'top5-row selected' : 'top5-row'}
                onClick={() => setSelected(p.name_norm)}
              >
                <span className="top5-rank">#{i + 1}</span>
                <span className="top5-name">{p.name}</span>
                <span className="top5-val">{(p[metric] as number)?.toFixed(1)}</span>
              </div>
            ))}
          </div>

          {/* İl listesi */}
          <div className="prov-list-wrap">
            <h4>🗺️ Tüm İller</h4>
            <div className="province-list">
              {provinces.map(p => (
                <button
                  key={p.name_norm}
                  className={selected === p.name_norm ? 'prov-btn selected' : 'prov-btn'}
                  onClick={() => setSelected(p.name_norm)}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sağ: İl detay */}
        <div className="map-right">
          {selected && selectedProv ? (
            <ProvinceDetail provinceName={selected} provinceDisplay={selectedProv.name} />
          ) : (
            <div className="empty-state">
              <div style={{ fontSize: '4rem' }}>🗺️</div>
              <h3>Bir İl Seçin</h3>
              <p>Haritadan veya listeden bir ile tıklayarak 2005–2024 yılları arasındaki verim, meteoroloji ve uydu verilerini görüntüleyin.</p>
              <div className="hint-cards">
                <div className="hint">📊 Yıllık verim grafiği</div>
                <div className="hint">🌡️ Sıcaklık & yağış</div>
                <div className="hint">🛰️ NDVI uydu verisi</div>
                <div className="hint">🌱 Toprak özellikleri</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
