import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import { fetchModelVersions, fetchYearlyTrend } from '../api';
import type { ModelVersion, YearlyTrend } from '../types';

const COLORS = { green: '#15803d', light: '#f0fdf4', card: '#fff', text: '#1e293b', sub: '#64748b', border: '#e2e8f0' };

export default function DashboardScreen() {
  const [model, setModel] = useState<ModelVersion | null>(null);
  const [trend, setTrend] = useState<YearlyTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([fetchModelVersions(), fetchYearlyTrend()])
      .then(([versions, t]) => {
        setModel(versions[versions.length - 1]);
        setTrend(t);
      })
      .catch(() => setError('Backend\'e bağlanılamadı. IP adresini kontrol edin.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color={COLORS.green} /></View>;
  if (error) return <View style={s.center}><Text style={s.error}>{error}</Text></View>;

  const maxYield = Math.max(...trend.map(t => t.avg_yield));

  return (
    <ScrollView style={s.container} contentContainerStyle={{ paddingBottom: 32 }}>
      {/* Hero */}
      <View style={s.hero}>
        <Text style={s.heroTitle}>🌾 Buğday Verim Tahmin</Text>
        <Text style={s.heroSub}>78 İl · 2005–2024 · NASA + MODIS + SoilGrids</Text>
        {model && (
          <View style={s.r2Box}>
            <Text style={s.r2Num}>{model.r2_holdout}</Text>
            <Text style={s.r2Label}>Model R²</Text>
          </View>
        )}
      </View>

      {/* Metrik kartları */}
      {model && (
        <>
          <Text style={s.sectionTitle}>Model Performansı (V3)</Text>
          <View style={s.cardRow}>
            <MetricCard icon="🎯" label="R² Holdout" value={String(model.r2_holdout)} color="#16a34a" />
            <MetricCard icon="📏" label="RMSE" value={`${model.rmse_holdout} kg/da`} color="#3b82f6" />
          </View>
          <View style={s.cardRow}>
            <MetricCard icon="📐" label="MAE" value={`${model.mae_holdout} kg/da`} color="#8b5cf6" />
            <MetricCard icon="🔁" label="CV R²" value={String(model.r2_cv)} color="#f59e0b" />
          </View>
          <View style={s.cardRow}>
            <MetricCard icon="⚙️" label="Algoritma" value={model.algorithm} color="#64748b" />
            <MetricCard icon="📊" label="Özellik" value={`${model.feature_count} adet`} color="#ef4444" />
          </View>
        </>
      )}

      {/* Yıllık trend bar chart — manuel */}
      <Text style={s.sectionTitle}>Türkiye Yıllık Ort. Verim (kg/da)</Text>
      <View style={s.chartBox}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={s.barChart}>
            {trend.map(t => (
              <View key={t.harvest_year} style={s.barWrap}>
                <Text style={s.barVal}>{Math.round(t.avg_yield)}</Text>
                <View style={[s.bar, {
                  height: Math.max(8, (t.avg_yield / maxYield) * 120),
                  backgroundColor: t.harvest_year >= 2020 ? '#f59e0b' : COLORS.green
                }]} />
                <Text style={s.barLabel}>{String(t.harvest_year).slice(2)}</Text>
              </View>
            ))}
          </View>
        </ScrollView>
        <View style={s.legend}>
          <View style={s.legendItem}><View style={[s.dot, { backgroundColor: COLORS.green }]} /><Text style={s.legendText}>Eğitim (2005–19)</Text></View>
          <View style={s.legendItem}><View style={[s.dot, { backgroundColor: '#f59e0b' }]} /><Text style={s.legendText}>Holdout (2020–24)</Text></View>
        </View>
      </View>

      {/* Model açıklaması */}
      <Text style={s.sectionTitle}>Model Hakkında</Text>
      <View style={s.infoBox}>
        {[
          ['Veri Kaynakları', 'TUIK + NASA POWER + MODIS + SoilGrids'],
          ['Doğrulama', '5-fold ardışık yıl çapraz doğrulama'],
          ['En Önemli Özellik', 'Geçen yıl verimi (%49)'],
          ['İkinci Önemli', 'MAM dönemi özellikleri (%14.7)'],
          ['Gelişim', 'V1: 0.538 → V2: 0.552 → V3: 0.608'],
        ].map(([k, v]) => (
          <View key={k} style={s.infoRow}>
            <Text style={s.infoKey}>{k}</Text>
            <Text style={s.infoVal}>{v}</Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

function MetricCard({ icon, label, value, color }: { icon: string; label: string; value: string; color: string }) {
  return (
    <View style={[s.metricCard, { borderTopColor: color }]}>
      <Text style={s.metricIcon}>{icon}</Text>
      <Text style={s.metricLabel}>{label}</Text>
      <Text style={[s.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  error: { color: '#ef4444', textAlign: 'center', padding: 16 },
  hero: { backgroundColor: COLORS.green, padding: 24, alignItems: 'center' },
  heroTitle: { color: '#fff', fontSize: 20, fontWeight: '800', marginBottom: 4 },
  heroSub: { color: 'rgba(255,255,255,0.8)', fontSize: 12, marginBottom: 16 },
  r2Box: { backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 12, padding: 12, alignItems: 'center' },
  r2Num: { color: '#fff', fontSize: 36, fontWeight: '900' },
  r2Label: { color: 'rgba(255,255,255,0.8)', fontSize: 11, textTransform: 'uppercase', letterSpacing: 1 },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: COLORS.text, margin: 16, marginBottom: 8 },
  cardRow: { flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginBottom: 8 },
  metricCard: { flex: 1, backgroundColor: COLORS.card, borderRadius: 12, padding: 14, borderTopWidth: 3, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  metricIcon: { fontSize: 20, marginBottom: 4 },
  metricLabel: { fontSize: 10, color: COLORS.sub, textTransform: 'uppercase', letterSpacing: 0.5 },
  metricValue: { fontSize: 16, fontWeight: '700', marginTop: 2 },
  chartBox: { backgroundColor: COLORS.card, marginHorizontal: 16, borderRadius: 12, padding: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  barChart: { flexDirection: 'row', alignItems: 'flex-end', gap: 4 },
  barWrap: { alignItems: 'center', gap: 2 },
  bar: { width: 18, borderRadius: 3 },
  barVal: { fontSize: 7, color: COLORS.sub },
  barLabel: { fontSize: 9, color: COLORS.sub },
  legend: { flexDirection: 'row', gap: 16, marginTop: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 11, color: COLORS.sub },
  infoBox: { backgroundColor: COLORS.card, marginHorizontal: 16, borderRadius: 12, padding: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  infoRow: { paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  infoKey: { fontSize: 11, color: COLORS.sub, marginBottom: 2 },
  infoVal: { fontSize: 13, color: COLORS.text, fontWeight: '500' },
});
