import { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell, ReferenceLine
} from 'recharts';
import { fetchModelVersions, fetchYearlyTrend, fetchPredictions, fetchErrorByRegion } from '../api';
import type { ModelVersion, YearlyTrend, Prediction, RegionError } from '../types';

const REGION_COLORS: Record<string, string> = {
  'Ic Anadolu': '#f59e0b', 'Karadeniz': '#3b82f6', 'Ege': '#10b981',
  'Marmara': '#8b5cf6', 'Akdeniz': '#ef4444', 'Dogu Anadolu': '#6366f1',
  'Guneydogu Anadolu': '#f97316', 'Bati Karadeniz': '#06b6d4',
};

export default function Dashboard() {
  const [latest, setLatest] = useState<ModelVersion | null>(null);
  const [trend, setTrend] = useState<YearlyTrend[]>([]);
  const [preds, setPreds] = useState<Prediction[]>([]);
  const [regionErr, setRegionErr] = useState<RegionError[]>([]);
  const [scatterMode, setScatterMode] = useState<'region' | 'city'>('region');

  useEffect(() => {
    fetchModelVersions().then(v => setLatest(v[v.length - 1]));
    fetchYearlyTrend().then(setTrend);
    fetchPredictions().then(setPreds);
    fetchErrorByRegion().then(setRegionErr);
  }, []);

  const r2Pct = latest ? Math.round(latest.r2_holdout * 100) : 0;

  // Bölge bazında ortalama tahmin vs gerçek
  const regionScatter = Object.entries(
    preds.reduce((acc, p) => {
      if (!acc[p.region]) acc[p.region] = { actual: [], predicted: [] };
      acc[p.region].actual.push(p.actual_yield);
      acc[p.region].predicted.push(p.predicted_yield);
      return acc;
    }, {} as Record<string, { actual: number[]; predicted: number[] }>)
  ).map(([region, vals]) => ({
    region,
    actual_yield: vals.actual.reduce((a, b) => a + b, 0) / vals.actual.length,
    predicted_yield: vals.predicted.reduce((a, b) => a + b, 0) / vals.predicted.length,
    error_pct: ((vals.predicted.reduce((a, b) => a + b, 0) / vals.predicted.length) -
                (vals.actual.reduce((a, b) => a + b, 0) / vals.actual.length)) /
               (vals.actual.reduce((a, b) => a + b, 0) / vals.actual.length) * 100,
    province: region,
    harvest_year: 0,
    error_kg: 0,
  }));

  return (
    <div className="dashboard">
      <div className="dashboard-hero">
        <div className="hero-text">
          <h1>🌾 Türkiye Buğday Verimi Tahmin Sistemi</h1>
          <p>78 İl · 2005–2024 · NASA POWER + MODIS + SoilGrids + TUIK</p>
        </div>
        {latest && (
          <div className="hero-badge">
            <div className="badge-r2">{latest.r2_holdout}</div>
            <div className="badge-label">Model R²</div>
            <div className="badge-sub">Ridge Regression · {latest.feature_count} özellik</div>
          </div>
        )}
      </div>

      {/* Ana metrikler */}
      {latest && (
        <div className="stat-cards">
          <StatCard icon="🎯" label="R² (Holdout)" value={String(latest.r2_holdout)} sub="2020-2024 testi" color="#16a34a" />
          <StatCard icon="📏" label="RMSE" value={`${latest.rmse_holdout} kg/da`} sub="Ortalama hata" color="#3b82f6" />
          <StatCard icon="📐" label="MAE" value={`${latest.mae_holdout} kg/da`} sub="Mutlak hata" color="#8b5cf6" />
          <StatCard icon="🔁" label="CV R²" value={String(latest.r2_cv)} sub="5-fold çapraz doğrulama" color="#f59e0b" />
          <StatCard icon="📊" label="Eğitim" value={latest.train_years} sub="Eğitim dönemi" color="#64748b" />
          <StatCard icon="🧪" label="Test" value={latest.holdout_years} sub="Holdout dönemi" color="#ef4444" />
        </div>
      )}

      <div className="dashboard-grid">
        {/* Yıllık trend */}
        <div className="chart-card wide">
          <h3>📈 Türkiye Geneli Yıllık Ortalama Buğday Verimi (2005–2024)</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="harvest_year" tick={{ fontSize: 12 }} />
              <YAxis unit=" kg/da" tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v: number) => [`${v?.toFixed(1)} kg/da`, 'Ort. Verim']} />
              <ReferenceLine x={2020} stroke="#ef4444" strokeDasharray="4 4" label={{ value: 'Holdout', fontSize: 11 }} />
              <Line type="monotone" dataKey="avg_yield" name="Ort Verim" stroke="#16a34a" strokeWidth={2.5} dot={{ r: 4, fill: '#16a34a' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Scatter tahmin vs gerçek */}
        <div className="chart-card">
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'0.25rem' }}>
            <h3>🎯 Tahmin vs Gerçek (Holdout 2020–2024)</h3>
            <div style={{ display:'flex', gap:4 }}>
              <button className={scatterMode==='region' ? 'tab active' : 'tab'} onClick={() => setScatterMode('region')}>Bölge</button>
              <button className={scatterMode==='city' ? 'tab active' : 'tab'} onClick={() => setScatterMode('city')}>İl</button>
            </div>
          </div>
          <p className="chart-sub">Noktalar köşegen çizgiye yakınsa → model başarılı. Üstte = fazla tahmin, altta = eksik tahmin.</p>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="actual_yield" name="Gerçek" type="number"
                domain={[80, 520]} tickCount={8}
                tick={{ fontSize: 11 }} unit=" kg/da"
                label={{ value: '← Gerçek Verim (kg/da)', position: 'insideBottom', offset: -15, fontSize: 12, fill: '#64748b' }}
              />
              <YAxis
                dataKey="predicted_yield" name="Tahmin" type="number"
                domain={[80, 520]} tickCount={8}
                tick={{ fontSize: 11 }} unit=" kg/da"
                label={{ value: 'Tahmin ↑', angle: -90, position: 'insideLeft', fontSize: 12, fill: '#64748b' }}
              />
              <Tooltip content={({ payload }) => {
                if (!payload?.length) return null;
                const d = payload[0].payload as Prediction;
                const absPct = Math.abs(d.error_pct);
                const color = absPct < 5 ? '#16a34a' : absPct < 15 ? '#f59e0b' : '#ef4444';
                return (
                  <div className="custom-tooltip">
                    <strong>{scatterMode === 'region' ? d.region || d.province : d.province}</strong>
                    {scatterMode === 'city' && <span> ({d.harvest_year})</span>}<br />
                    Gerçek: <strong>{d.actual_yield?.toFixed(0)} kg/da</strong><br />
                    Tahmin: <strong>{d.predicted_yield?.toFixed(0)} kg/da</strong><br />
                    Hata: <span style={{ color, fontWeight: 700 }}>{d.error_pct?.toFixed(1)}%</span>
                  </div>
                );
              }} />
              <Scatter
                data={[{ actual_yield: 100, predicted_yield: 100 }, { actual_yield: 520, predicted_yield: 520 }]}
                name="İdeal (y=x)"
                line={{ stroke: '#16a34a', strokeWidth: 2, strokeDasharray: '6 3' }}
                shape={() => null}
                legendType="none"
              />
              {scatterMode === 'region' ? (
                <Scatter data={regionScatter} name="Bölgeler">
                  {regionScatter.map((r, i) => (
                    <Cell key={i} fill={REGION_COLORS[r.region] || '#94a3b8'} fillOpacity={1} r={10} />
                  ))}
                </Scatter>
              ) : (
                <Scatter data={preds} name="İller">
                  {preds.map((p, i) => (
                    <Cell key={i} fill={REGION_COLORS[p.region] || '#94a3b8'} fillOpacity={0.7} r={5} />
                  ))}
                </Scatter>
              )}
            </ScatterChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', gap:'1rem', flexWrap:'wrap', fontSize:'0.75rem', color:'#64748b', marginTop:'0.5rem' }}>
            <span>🟢 Hata &lt;5% → Çok iyi</span>
            <span>🟡 Hata 5-15% → Kabul edilebilir</span>
            <span>🔴 Hata &gt;15% → Zor il</span>
            {Object.entries(REGION_COLORS).map(([r, c]) => (
              <span key={r}><span style={{ background: c, borderRadius: '50%', display:'inline-block', width:10, height:10, marginRight:4 }} />{r}</span>
            ))}
          </div>
        </div>

        {/* Bölge hata */}
        <div className="chart-card">
          <h3>📍 Bölge Bazında Ortalama Hata (%)</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={regionErr} layout="vertical" margin={{ left: 10, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis type="number" unit="%" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="region" width={140} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number) => [`${v?.toFixed(1)}%`, 'Ort. Mutlak Hata']} />
              <Bar dataKey="avg_abs_error_pct" radius={[0, 4, 4, 0]}>
                {regionErr.map((r, i) => (
                  <Cell key={i} fill={REGION_COLORS[r.region] || '#94a3b8'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model açıklama */}
      <div className="model-info-box">
        <h3>🔬 Model Hakkında</h3>
        <div className="model-info-grid">
          <div><strong>Algoritma:</strong> Ridge Regression (α=3.0)</div>
          <div><strong>Veri Kaynakları:</strong> TUIK, NASA POWER, MODIS Terra, SoilGrids WCS</div>
          <div><strong>Özellikler:</strong> Meteoroloji (sezon+MAM), NDVI/EVI, Toprak, GDD, Geçen Yıl Verimi</div>
          <div><strong>Doğrulama:</strong> 5-fold ardışık yıl çapraz doğrulaması + holdout</div>
          <div><strong>Gelişim:</strong> V1 R²=0.538 → V2 +Toprak R²=0.552 → V3 +GDD+LagYield R²=0.608</div>
          <div><strong>En önemli özellik:</strong> Geçen yıl verimi (%49), MAM dönemi (%14.7)</div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub, color }: { icon: string; label: string; value: string; sub: string; color: string }) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  );
}
