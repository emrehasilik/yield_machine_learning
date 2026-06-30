import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, Dimensions } from 'react-native';
import { fetchProvinceHistory } from '../api';
import type { YearRecord } from '../types';

const W = Dimensions.get('window').width - 32;
const COLORS = { green: '#15803d', card: '#fff', text: '#1e293b', sub: '#64748b', border: '#e2e8f0' };

export default function ProvinceDetailScreen({ route }: any) {
  const { province } = route.params;
  const [data, setData] = useState<YearRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProvinceHistory(province.name_norm).then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color={COLORS.green} /></View>;
  if (!data.length) return <View style={s.center}><Text style={s.err}>Veri bulunamadı</Text></View>;

  const avgYield = data.reduce((a, b) => a + b.actual_yield, 0) / data.length;
  const maxYield = Math.max(...data.map(d => d.actual_yield));
  const minYield = Math.min(...data.map(d => d.actual_yield));
  const chartMax = Math.max(...data.map(d => Math.max(d.actual_yield, d.predicted_yield || 0)));
  const chartH = 140;

  return (
    <ScrollView style={s.container} contentContainerStyle={{ paddingBottom: 32 }}>
      {/* Header */}
      <View style={s.header}>
        <Text style={s.headerTitle}>{province.name}</Text>
        <Text style={s.headerSub}>{province.region}</Text>
      </View>

      {/* Özet kartlar */}
      <View style={s.cardRow}>
        <SmallCard label="Ortalama" value={`${avgYield.toFixed(0)} kg/da`} color={COLORS.green} />
        <SmallCard label="En Yüksek" value={`${maxYield} kg/da`} color="#f59e0b" />
        <SmallCard label="En Düşük" value={`${minYield} kg/da`} color="#ef4444" />
      </View>

      {/* Verim Grafiği */}
      <Text style={s.sectionTitle}>📈 Yıllık Verim (2005–2024)</Text>
      <View style={s.chartCard}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: chartH + 40, paddingTop: 16 }}>
            {data.map(d => {
              const h = Math.max(4, (d.actual_yield / chartMax) * chartH);
              const ph = d.predicted_yield ? Math.max(4, (d.predicted_yield / chartMax) * chartH) : null;
              const isHoldout = d.harvest_year >= 2020;
              return (
                <View key={d.harvest_year} style={{ alignItems: 'center', marginHorizontal: 3 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 1 }}>
                    <View style={[s.bar, { height: h, backgroundColor: isHoldout ? '#f59e0b' : COLORS.green }]} />
                    {ph && <View style={[s.bar, { height: ph, backgroundColor: '#94a3b8', opacity: 0.7 }]} />}
                  </View>
                  <Text style={s.barLabel}>{String(d.harvest_year).slice(2)}</Text>
                </View>
              );
            })}
          </View>
        </ScrollView>
        <View style={s.legend}>
          <View style={s.legendItem}><View style={[s.dot, { backgroundColor: COLORS.green }]} /><Text style={s.legendText}>Gerçek</Text></View>
          <View style={s.legendItem}><View style={[s.dot, { backgroundColor: '#f59e0b' }]} /><Text style={s.legendText}>Holdout</Text></View>
          <View style={s.legendItem}><View style={[s.dot, { backgroundColor: '#94a3b8' }]} /><Text style={s.legendText}>Tahmin</Text></View>
        </View>
      </View>

      {/* Meteoroloji özeti */}
      <Text style={s.sectionTitle}>🌡️ Meteoroloji Özeti (Ort.)</Text>
      <View style={s.infoBox}>
        {[
          ['Sezon Sıcaklık', `${(data.reduce((a,b) => a+(b.tmean||0), 0)/data.length).toFixed(1)} °C`],
          ['Sezon Yağış', `${(data.reduce((a,b) => a+(b.rain_sum||0), 0)/data.length).toFixed(0)} mm`],
          ['MAM Sıcaklık', `${(data.reduce((a,b) => a+(b.mam_tmean||0), 0)/data.length).toFixed(1)} °C`],
          ['MAM Yağış', `${(data.reduce((a,b) => a+(b.mam_rain_sum||0), 0)/data.length).toFixed(0)} mm`],
          ['GDD Sezon', `${(data.reduce((a,b) => a+(b.gdd_season||0), 0)/data.length).toFixed(0)}`],
          ['NDVI Max Ort.', `${(data.reduce((a,b) => a+(b.ndvi_max||0), 0)/data.length).toFixed(3)}`],
        ].map(([k, v]) => (
          <View key={k} style={s.infoRow}>
            <Text style={s.infoKey}>{k}</Text>
            <Text style={s.infoVal}>{v}</Text>
          </View>
        ))}
      </View>

      {/* Holdout tahmin tablosu */}
      <Text style={s.sectionTitle}>🧪 Holdout Tahminleri (2020–2024)</Text>
      <View style={s.tableCard}>
        <View style={s.tableHead}>
          {['Yıl', 'Gerçek', 'Tahmin', 'Hata %'].map(h => (
            <Text key={h} style={s.th}>{h}</Text>
          ))}
        </View>
        {data.filter(d => d.harvest_year >= 2020).map(d => {
          const abs = Math.abs(d.error_pct || 0);
          const color = abs < 5 ? '#16a34a' : abs < 15 ? '#f59e0b' : '#ef4444';
          return (
            <View key={d.harvest_year} style={s.tableRow}>
              <Text style={s.td}>{d.harvest_year}</Text>
              <Text style={s.td}>{d.actual_yield.toFixed(0)}</Text>
              <Text style={s.td}>{d.predicted_yield?.toFixed(0) ?? '—'}</Text>
              <Text style={[s.td, { color, fontWeight: '700' }]}>{d.error_pct?.toFixed(1)}%</Text>
            </View>
          );
        })}
      </View>
    </ScrollView>
  );
}

function SmallCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <View style={[s.smallCard, { borderTopColor: color }]}>
      <Text style={s.smallLabel}>{label}</Text>
      <Text style={[s.smallValue, { color }]}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  err: { color: '#ef4444' },
  header: { backgroundColor: '#15803d', padding: 20 },
  headerTitle: { color: '#fff', fontSize: 22, fontWeight: '800' },
  headerSub: { color: 'rgba(255,255,255,0.8)', fontSize: 13, marginTop: 2 },
  sectionTitle: { fontSize: 14, fontWeight: '700', color: '#1e293b', margin: 16, marginBottom: 8 },
  cardRow: { flexDirection: 'row', paddingHorizontal: 12, gap: 8, marginTop: 12 },
  smallCard: { flex: 1, backgroundColor: COLORS.card, borderRadius: 10, padding: 10, borderTopWidth: 3, shadowColor: '#000', shadowOpacity: 0.04, shadowRadius: 3, elevation: 2 },
  smallLabel: { fontSize: 10, color: COLORS.sub, textTransform: 'uppercase' },
  smallValue: { fontSize: 13, fontWeight: '700', marginTop: 3 },
  chartCard: { backgroundColor: COLORS.card, marginHorizontal: 16, borderRadius: 12, padding: 12, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  bar: { width: 14, borderRadius: 3 },
  barLabel: { fontSize: 9, color: COLORS.sub, marginTop: 2 },
  legend: { flexDirection: 'row', gap: 12, marginTop: 8 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 11, color: COLORS.sub },
  infoBox: { backgroundColor: COLORS.card, marginHorizontal: 16, borderRadius: 12, padding: 16, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: COLORS.border },
  infoKey: { fontSize: 13, color: COLORS.sub },
  infoVal: { fontSize: 13, fontWeight: '600', color: COLORS.text },
  tableCard: { backgroundColor: COLORS.card, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  tableHead: { flexDirection: 'row', backgroundColor: '#f8fafc', paddingVertical: 10, paddingHorizontal: 16 },
  th: { flex: 1, fontSize: 12, fontWeight: '700', color: COLORS.sub, textAlign: 'center' },
  tableRow: { flexDirection: 'row', paddingVertical: 10, paddingHorizontal: 16, borderTopWidth: 1, borderTopColor: COLORS.border },
  td: { flex: 1, fontSize: 13, color: COLORS.text, textAlign: 'center' },
});
