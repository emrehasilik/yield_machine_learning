import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, FlatList, TextInput, TouchableOpacity, ActivityIndicator } from 'react-native';
import { fetchProvinces } from '../api';
import type { Province } from '../types';

const REGION_COLORS: Record<string, string> = {
  'Akdeniz': '#ef4444', 'Ege': '#10b981', 'Marmara': '#8b5cf6',
  'Ic Anadolu': '#f59e0b', 'Karadeniz': '#3b82f6', 'Dogu Anadolu': '#6366f1',
  'Guneydogu Anadolu': '#f97316', 'Bati Karadeniz': '#06b6d4',
};

export default function ProvinceListScreen({ navigation }: any) {
  const [provinces, setProvinces] = useState<Province[]>([]);
  const [filtered, setFiltered] = useState<Province[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProvinces()
      .then(data => { setProvinces(data); setFiltered(data); })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!search) { setFiltered(provinces); return; }
    setFiltered(provinces.filter(p => p.name.toLowerCase().includes(search.toLowerCase())));
  }, [search, provinces]);

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#15803d" /></View>;

  return (
    <View style={s.container}>
      <View style={s.searchBox}>
        <Text style={s.searchIcon}>🔍</Text>
        <TextInput
          style={s.input}
          placeholder="İl ara..."
          value={search}
          onChangeText={setSearch}
          placeholderTextColor="#94a3b8"
        />
      </View>
      <Text style={s.count}>{filtered.length} il listeleniyor</Text>
      <FlatList
        data={filtered}
        keyExtractor={item => item.name_norm}
        renderItem={({ item }) => (
          <TouchableOpacity style={s.row} onPress={() => navigation.navigate('ProvinceDetail', { province: item })}>
            <View style={[s.regionDot, { backgroundColor: REGION_COLORS[item.region] || '#94a3b8' }]} />
            <View style={s.rowText}>
              <Text style={s.rowName}>{item.name}</Text>
              <Text style={s.rowSub}>{item.region} · {item.data_years} yıl veri</Text>
            </View>
            <View style={s.rowRight}>
              <Text style={s.rowYield}>{item.avg_yield?.toFixed(0)}</Text>
              <Text style={s.rowUnit}>kg/da ort.</Text>
            </View>
            <Text style={s.arrow}>›</Text>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={s.separator} />}
      />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  searchBox: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', margin: 12, borderRadius: 12, paddingHorizontal: 12, shadowColor: '#000', shadowOpacity: 0.06, shadowRadius: 4, elevation: 2 },
  searchIcon: { fontSize: 16, marginRight: 8 },
  input: { flex: 1, height: 44, fontSize: 15, color: '#1e293b' },
  count: { fontSize: 12, color: '#94a3b8', paddingHorizontal: 16, marginBottom: 4 },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', paddingHorizontal: 16, paddingVertical: 14 },
  regionDot: { width: 12, height: 12, borderRadius: 6, marginRight: 12 },
  rowText: { flex: 1 },
  rowName: { fontSize: 15, fontWeight: '600', color: '#1e293b' },
  rowSub: { fontSize: 12, color: '#64748b', marginTop: 2 },
  rowRight: { alignItems: 'flex-end', marginRight: 8 },
  rowYield: { fontSize: 16, fontWeight: '700', color: '#15803d' },
  rowUnit: { fontSize: 10, color: '#94a3b8' },
  arrow: { fontSize: 20, color: '#cbd5e1' },
  separator: { height: 1, backgroundColor: '#f1f5f9' },
});
