import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator, Dimensions,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { fetchProvinces, fetchProvinceHistory } from '../api';
import type { Province, YearRecord } from '../types';
import PROVINCES_DATA from '../turkeyProvinces.json';

const { width: SW } = Dimensions.get('window');
const MAP_H = Math.round(SW * 0.55);

// plate → name_norm
const PLATE_TO_NORM: Record<string, string> = {
  '01':'ADANA','02':'ADIYAMAN','03':'AFYON','04':'AGRI','05':'AMASYA',
  '06':'ANKARA','07':'ANTALYA','08':'ARTVIN','09':'AYDIN','10':'BALIKESIR',
  '11':'BILECIK','12':'BINGOL','13':'BITLIS','14':'BOLU','15':'BURDUR',
  '16':'BURSA','17':'CANAKKALE','18':'CANKIRI','19':'CORUM','20':'DENIZLI',
  '21':'DIYARBAKIR','22':'EDIRNE','23':'ELAZIG','24':'ERZINCAN','25':'ERZURUM',
  '26':'ESKISEHIR','27':'GAZIANTEP','28':'GIRESUN','29':'GUMUSHANE','30':'HAKKARI',
  '31':'HATAY','32':'ISPARTA','33':'MERSIN','34':'ISTANBUL','35':'IZMIR',
  '36':'KARS','37':'KASTAMONU','38':'KAYSERI','39':'KIRKLARELI','40':'KIRSEHIR',
  '41':'KOCAELI','42':'KONYA','43':'KUTAHYA','44':'MALATYA','45':'MANISA',
  '46':'KAHRAMANMARAS','47':'MARDIN','48':'MUGLA','49':'MUS','50':'NEVSEHIR',
  '51':'NIGDE','52':'ORDU','53':'RIZE','54':'SAKARYA','55':'SAMSUN',
  '56':'SIIRT','57':'SINOP','58':'SIVAS','59':'TEKIRDAG','60':'TOKAT',
  '61':'TRABZON','62':'TUNCELI','63':'SANLIURFA','64':'USAK','65':'VAN',
  '66':'YOZGAT','67':'ZONGULDAK','68':'AKSARAY','69':'BAYBURT','70':'KARAMAN',
  '71':'KIRIKKALE','72':'BATMAN','73':'SIRNAK','74':'BARTIN','75':'ARDAHAN',
  '76':'IGDIR','77':'YALOVA','78':'KARABUK','79':'KILIS','80':'OSMANIYE',
  '81':'DUZCE',
};

const C = { green: '#15803d', bg: '#f1f5f9', card: '#fff', text: '#1e293b', sub: '#64748b', border: '#e2e8f0' };

function buildMapHtml(provinceColors: Record<string, string>, selectedPlate: string): string {
  const paths = (PROVINCES_DATA as {p:string;c:string;d:string}[]).map(prov => {
    const fill = prov.p === selectedPlate ? '#15803d' : (provinceColors[prov.p] || '#a7c8a0');
    const stroke = prov.p === selectedPlate ? '#fff' : '#fff';
    const strokeW = prov.p === selectedPlate ? '1.5' : '0.4';
    return `<path id="p${prov.p}" data-plate="${prov.p}" data-city="${prov.c}" d="${prov.d}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeW}" onclick="sel('${prov.p}')" style="cursor:pointer"/>`;
  }).join('\n');

  return `<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{width:100%;height:100%;background:#f8fafc;overflow:hidden;display:flex;align-items:center;justify-content:center;}
svg{width:100%;height:auto;display:block;}
path:hover{opacity:0.75;}
#tooltip{position:fixed;bottom:8px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.75);color:#fff;padding:4px 12px;border-radius:12px;font-size:13px;font-family:sans-serif;pointer-events:none;white-space:nowrap;display:none;}
</style>
</head><body>
<svg viewBox="0 0 1050 620" xmlns="http://www.w3.org/2000/svg">
${paths}
</svg>
<div id="tooltip"></div>
<script>
function sel(plate){
  window.ReactNativeWebView.postMessage(JSON.stringify({type:'select',plate:plate}));
  var tt=document.getElementById('tooltip');
  var el=document.querySelector('[data-plate="'+plate+'"]');
  if(el){tt.innerText=el.getAttribute('data-city');tt.style.display='block';setTimeout(function(){tt.style.display='none';},1500);}
}
</script>
</body></html>`;
}

export default function MapScreen() {
  const webRef = useRef<WebView>(null);
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [provinceColors, setProvinceColors] = useState<Record<string, string>>({});
  const [selectedPlate, setSelectedPlate] = useState('');
  const [selected, setSelected] = useState<Province | null>(null);
  const [history, setHistory] = useState<YearRecord[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [html, setHtml] = useState(() => buildMapHtml({}, ''));

  useEffect(() => {
    fetchProvinces().then(data => {
      setProvinces(data);
      const max = Math.max(...data.map(p => p.avg_yield ?? 0));
      const min = Math.min(...data.map(p => p.avg_yield ?? 0));
      const normToPlate: Record<string, string> = {};
      Object.entries(PLATE_TO_NORM).forEach(([p, n]) => { normToPlate[n] = p; });
      const colors: Record<string, string> = {};
      data.forEach(p => {
        const plate = normToPlate[p.name_norm];
        if (!plate || p.avg_yield == null) return;
        const t = (p.avg_yield - min) / (max - min || 1);
        colors[plate] = interpolateColor('#c8e6c9', '#1b5e20', t);
      });
      setProvinceColors(colors);
      setHtml(buildMapHtml(colors, ''));
    });
  }, []);

  const handleMessage = (event: any) => {
    try {
      const msg = JSON.parse(event.nativeEvent.data);
      if (msg.type === 'select') {
        const plate = msg.plate;
        const norm = PLATE_TO_NORM[plate];
        if (!norm) return;
        const prov = provinces.find(p => p.name_norm === norm);
        if (!prov) return;
        setSelectedPlate(plate);
        setSelected(prov);
        setHtml(buildMapHtml(provinceColors, plate));
        setLoadingHistory(true);
        fetchProvinceHistory(norm)
          .then(setHistory)
          .finally(() => setLoadingHistory(false));
      }
    } catch {}
  };

  const avgYield = history.length ? history.reduce((a, b) => a + b.actual_yield, 0) / history.length : 0;
  const maxYield = history.length ? Math.max(...history.map(d => d.actual_yield)) : 0;
  const minYield = history.length ? Math.min(...history.map(d => d.actual_yield)) : 0;
  const chartMax = history.length ? Math.max(...history.map(d => Math.max(d.actual_yield, d.predicted_yield || 0))) : 1;
  const chartH = 110;

  return (
    <View style={s.container}>
      {/* Turkey Map */}
      <View style={[s.mapBox, { height: MAP_H }]}>
        <WebView
          ref={webRef}
          originWhitelist={['*']}
          source={{ html }}
          style={s.webview}
          scrollEnabled={false}
          onMessage={handleMessage}
          javaScriptEnabled
          showsHorizontalScrollIndicator={false}
          showsVerticalScrollIndicator={false}
        />
      </View>

      {/* Detail or hint */}
      {!selected ? (
        <View style={s.hint}>
          <Text style={s.hintEmoji}>👆</Text>
          <Text style={s.hintText}>Haritadan bir il seçin</Text>
          <Text style={s.hintSub}>78 il · 2005–2024 buğday verimi</Text>
        </View>
      ) : (
        <ScrollView style={s.detail} showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 32 }}>
          {/* Province header */}
          <View style={s.detailHeader}>
            <View>
              <Text style={s.detailName}>{selected.name}</Text>
              <Text style={s.detailRegion}>{selected.region}</Text>
            </View>
            <View style={s.badge}>
              <Text style={s.badgeText}>{selected.data_years} yıl veri</Text>
            </View>
          </View>

          {/* Summary cards */}
          <View style={s.cardRow}>
            <StatCard label="Ortalama" value={avgYield.toFixed(0)} unit="kg/da" color={C.green} loading={loadingHistory} />
            <StatCard label="En Yüksek" value={String(maxYield)} unit="kg/da" color="#f59e0b" loading={loadingHistory} />
            <StatCard label="En Düşük" value={String(minYield)} unit="kg/da" color="#ef4444" loading={loadingHistory} />
          </View>

          {loadingHistory ? (
            <View style={s.center}><ActivityIndicator color={C.green} size="large" /></View>
          ) : (
            <>
              {/* Bar chart */}
              <Text style={s.sectionTitle}>📈 Yıllık Verim (2005–2024)</Text>
              <View style={s.chartCard}>
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                  <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: chartH + 28, paddingTop: 6 }}>
                    {history.map(d => {
                      const h = Math.max(4, (d.actual_yield / chartMax) * chartH);
                      const ph = d.predicted_yield ? Math.max(4, (d.predicted_yield / chartMax) * chartH) : null;
                      const isHoldout = d.harvest_year >= 2020;
                      return (
                        <View key={d.harvest_year} style={{ alignItems: 'center', marginHorizontal: 2 }}>
                          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 1 }}>
                            <View style={[s.bar, { height: h, backgroundColor: isHoldout ? '#f59e0b' : C.green }]} />
                            {ph && <View style={[s.bar, { height: ph, backgroundColor: '#94a3b8' }]} />}
                          </View>
                          <Text style={s.barLabel}>{String(d.harvest_year).slice(2)}</Text>
                        </View>
                      );
                    })}
                  </View>
                </ScrollView>
                <View style={s.legend}>
                  <LegendDot color={C.green} label="Gerçek" />
                  <LegendDot color="#f59e0b" label="Holdout" />
                  <LegendDot color="#94a3b8" label="Tahmin" />
                </View>
              </View>

              {/* Holdout table */}
              <Text style={s.sectionTitle}>🧪 Holdout 2020–2024</Text>
              <View style={s.tableCard}>
                <View style={s.tableHead}>
                  {['Yıl', 'Gerçek', 'Tahmin', 'Hata %'].map(h => (
                    <Text key={h} style={s.th}>{h}</Text>
                  ))}
                </View>
                {history.filter(d => d.harvest_year >= 2020).map(d => {
                  const abs = Math.abs(d.error_pct ?? 0);
                  const col = abs < 5 ? '#16a34a' : abs < 15 ? '#f59e0b' : '#ef4444';
                  return (
                    <View key={d.harvest_year} style={s.tableRow}>
                      <Text style={s.td}>{d.harvest_year}</Text>
                      <Text style={s.td}>{d.actual_yield.toFixed(0)}</Text>
                      <Text style={s.td}>{d.predicted_yield?.toFixed(0) ?? '—'}</Text>
                      <Text style={[s.td, { color: col, fontWeight: '700' }]}>{d.error_pct?.toFixed(1)}%</Text>
                    </View>
                  );
                })}
              </View>

              {/* Meteo summary */}
              <Text style={s.sectionTitle}>🌡️ Meteoroloji Ortalaması</Text>
              <View style={s.infoBox}>
                {[
                  ['Sezon Sıcaklık', `${avg(history, 'tmean').toFixed(1)} °C`],
                  ['Sezon Yağış', `${avg(history, 'rain_sum').toFixed(0)} mm`],
                  ['MAM Sıcaklık', `${avg(history, 'mam_tmean').toFixed(1)} °C`],
                  ['MAM Yağış', `${avg(history, 'mam_rain_sum').toFixed(0)} mm`],
                  ['GDD Sezon', `${avg(history, 'gdd_season').toFixed(0)}`],
                  ['NDVI Max', `${avg(history, 'ndvi_max').toFixed(3)}`],
                ].map(([k, v]) => (
                  <View key={k} style={s.infoRow}>
                    <Text style={s.infoKey}>{k}</Text>
                    <Text style={s.infoVal}>{v}</Text>
                  </View>
                ))}
              </View>
            </>
          )}
        </ScrollView>
      )}
    </View>
  );
}

function avg(data: YearRecord[], key: keyof YearRecord): number {
  const vals = data.map(d => d[key] as number | null).filter(v => v != null) as number[];
  return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

function interpolateColor(hex1: string, hex2: string, t: number): string {
  const r1 = parseInt(hex1.slice(1, 3), 16), g1 = parseInt(hex1.slice(3, 5), 16), b1 = parseInt(hex1.slice(5, 7), 16);
  const r2 = parseInt(hex2.slice(1, 3), 16), g2 = parseInt(hex2.slice(3, 5), 16), b2 = parseInt(hex2.slice(5, 7), 16);
  const r = Math.round(r1 + (r2 - r1) * t).toString(16).padStart(2, '0');
  const g = Math.round(g1 + (g2 - g1) * t).toString(16).padStart(2, '0');
  const b = Math.round(b1 + (b2 - b1) * t).toString(16).padStart(2, '0');
  return `#${r}${g}${b}`;
}

function StatCard({ label, value, unit, color, loading }: { label: string; value: string; unit: string; color: string; loading: boolean }) {
  return (
    <View style={[s.statCard, { borderTopColor: color }]}>
      <Text style={s.statLabel}>{label}</Text>
      {loading
        ? <ActivityIndicator size="small" color={color} style={{ marginTop: 6 }} />
        : <>
            <Text style={[s.statValue, { color }]}>{value}</Text>
            <Text style={s.statUnit}>{unit}</Text>
          </>
      }
    </View>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
      <Text style={{ fontSize: 11, color: C.sub }}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  mapBox: { backgroundColor: '#f1f5f9', borderBottomWidth: 1, borderBottomColor: C.border },
  webview: { flex: 1, backgroundColor: 'transparent' },
  hint: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  hintEmoji: { fontSize: 44 },
  hintText: { fontSize: 18, fontWeight: '700', color: C.text },
  hintSub: { fontSize: 13, color: C.sub },
  detail: { flex: 1 },
  detailHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', backgroundColor: C.green, padding: 16 },
  detailName: { color: '#fff', fontSize: 20, fontWeight: '800' },
  detailRegion: { color: 'rgba(255,255,255,0.8)', fontSize: 12, marginTop: 2 },
  badge: { backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  badgeText: { color: '#fff', fontSize: 11, fontWeight: '600' },
  cardRow: { flexDirection: 'row', padding: 12, gap: 8 },
  statCard: { flex: 1, backgroundColor: C.card, borderRadius: 10, padding: 10, borderTopWidth: 3, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3 },
  statLabel: { fontSize: 10, color: C.sub, textTransform: 'uppercase' },
  statValue: { fontSize: 18, fontWeight: '800', marginTop: 2 },
  statUnit: { fontSize: 10, color: C.sub },
  center: { padding: 32, alignItems: 'center' },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: C.text, marginHorizontal: 16, marginTop: 12, marginBottom: 6 },
  chartCard: { backgroundColor: C.card, marginHorizontal: 16, borderRadius: 12, padding: 12, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3 },
  bar: { width: 12, borderRadius: 2 },
  barLabel: { fontSize: 9, color: C.sub, marginTop: 2 },
  legend: { flexDirection: 'row', gap: 12, marginTop: 8 },
  tableCard: { backgroundColor: C.card, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden', elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3 },
  tableHead: { flexDirection: 'row', backgroundColor: '#f8fafc', paddingVertical: 8, paddingHorizontal: 12 },
  th: { flex: 1, fontSize: 11, fontWeight: '700', color: C.sub, textAlign: 'center' },
  tableRow: { flexDirection: 'row', paddingVertical: 9, paddingHorizontal: 12, borderTopWidth: 1, borderTopColor: C.border },
  td: { flex: 1, fontSize: 13, color: C.text, textAlign: 'center' },
  infoBox: { backgroundColor: C.card, marginHorizontal: 16, borderRadius: 12, padding: 14, elevation: 2, shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 3 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 7, borderBottomWidth: 1, borderBottomColor: C.border },
  infoKey: { fontSize: 13, color: C.sub },
  infoVal: { fontSize: 13, fontWeight: '600', color: C.text },
});
