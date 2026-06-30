import TurkeyMap from 'react-turkey-map';
import type { MapYearData } from '../types';

const METRIC_CONFIG = {
  yield_kg_dekar: { label: 'Verim (kg/da)', low: '#fff7e6', high: '#7c3800' },
  rain_sum:       { label: 'Yağış (mm)',    low: '#dbeafe', high: '#1e3a8a' },
  tmean:          { label: 'Sıcaklık (°C)', low: '#fee2e2', high: '#7f1d1d' },
  ndvi_max:       { label: 'NDVI Max',      low: '#f0fdf4', high: '#14532d' },
  gdd_season:     { label: 'GDD Sezon',     low: '#fffbeb', high: '#92400e' },
  hot_days_30:    { label: 'Sıcak Gün >30°C', low: '#fff7ed', high: '#7c2d12' },
};

export type MetricKey = keyof typeof METRIC_CONFIG;

// react-turkey-map il kodu → name_norm eşleştirmesi
const CITY_MAP: Record<string, string> = {
  '01':'ADANA','02':'ADIYAMAN','03':'AFYONKARAHISAR','04':'AGRI','05':'AMASYA',
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

function interpolateColor(low: string, high: string, t: number): string {
  const h = (s: string) => ({ r: parseInt(s.slice(1,3),16), g: parseInt(s.slice(3,5),16), b: parseInt(s.slice(5,7),16) });
  const l = h(low), hi = h(high);
  return `rgb(${Math.round(l.r+(hi.r-l.r)*t)},${Math.round(l.g+(hi.g-l.g)*t)},${Math.round(l.b+(hi.b-l.b)*t)})`;
}

interface Props {
  data: MapYearData[];
  selectedMetric: MetricKey;
  selectedProvince: string | null;
  onSelect: (name_norm: string) => void;
}

export default function TurkeyMapWrapper({ data, selectedMetric, selectedProvince, onSelect }: Props) {
  const cfg = METRIC_CONFIG[selectedMetric];
  const dataMap = new Map(data.map(d => [d.name_norm, d]));

  const values = data
    .map(d => d[selectedMetric] as number)
    .filter(v => v != null && !isNaN(v));
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);

  const customStyle = (cityCode: string) => {
    const norm = CITY_MAP[cityCode];
    if (!norm) return { fill: '#e2e8f0', stroke: '#fff', strokeWidth: 0.5, cursor: 'pointer' };
    if (norm === selectedProvince) return { fill: '#f59e0b', stroke: '#fff', strokeWidth: 1, cursor: 'pointer' };
    const row = dataMap.get(norm);
    const val = row ? (row[selectedMetric] as number) : null;
    if (val == null) return { fill: '#e2e8f0', stroke: '#fff', strokeWidth: 0.5, cursor: 'pointer' };
    const t = maxVal === minVal ? 0.5 : (val - minVal) / (maxVal - minVal);
    return { fill: interpolateColor(cfg.low, cfg.high, t), stroke: '#fff', strokeWidth: 0.5, cursor: 'pointer' };
  };

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const parent = target.tagName === 'path' ? target.parentElement : target;
    const plate = parent?.getAttribute('data-plate');
    if (plate) {
      const norm = CITY_MAP[plate];
      if (norm) onSelect(norm);
    }
  };

  return (
    <div>
      <div
        style={{ borderRadius: 12, overflow: 'hidden', background: '#f0f9ff', cursor: 'pointer' }}
        onClick={handleClick}
      >
        <TurkeyMap
          customStyle={customStyle}
          showTooltip={true}
        />
      </div>
      {/* Renk skalası */}
      <div style={{ display:'flex', alignItems:'center', gap:8, marginTop:8, fontSize:12, color:'#64748b' }}>
        <span>{isFinite(minVal) ? minVal.toFixed(1) : '—'}</span>
        <div style={{ flex:1, height:10, borderRadius:4, background:`linear-gradient(to right, ${cfg.low}, ${cfg.high})` }} />
        <span>{isFinite(maxVal) ? maxVal.toFixed(1) : '—'}</span>
        <span style={{ marginLeft:8, color:'#94a3b8' }}>{cfg.label}</span>
      </div>
    </div>
  );
}
