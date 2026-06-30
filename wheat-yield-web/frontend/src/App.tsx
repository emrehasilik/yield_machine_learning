import { useState } from 'react';
import Dashboard from './pages/Dashboard';
import MapPage from './pages/MapPage';
import './App.css';

type View = 'dashboard' | 'map';

export default function App() {
  const [view, setView] = useState<View>('dashboard');

  return (
    <div className="app">
      <nav className="navbar">
        <div className="nav-brand">🌾 Buğday Verim Tahmin Sistemi</div>
        <div className="nav-links">
          <button className={view === 'dashboard' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('dashboard')}>
            📊 Dashboard
          </button>
          <button className={view === 'map' ? 'nav-btn active' : 'nav-btn'} onClick={() => setView('map')}>
            🗺️ Türkiye Haritası
          </button>
        </div>
      </nav>
      <main className="main-content">
        {view === 'dashboard' ? <Dashboard /> : <MapPage />}
      </main>
    </div>
  );
}
