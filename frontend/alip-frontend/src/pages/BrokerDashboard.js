import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getMarketSummary } from '../services/api';
import toast from 'react-hot-toast';


export default function BrokerDashboard() {
  const { user, logout }      = useAuth();
  const navigate              = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSummary();
  }, []);

  const loadSummary = async () => {
    try {
      const res = await getMarketSummary();
      setSummary(res.data);
    } catch (err) {
      toast.error('Failed to load market data!');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    logout();
    toast.success('Logged out!');
    navigate('/login');
  };

const modules = [
    {
      icon:        '📊',
      title:       'Demand Analysis',
      description: 'Analyze regional crop demand and alerts',
      color:       '#9b59b6',
      path:        '/demand'
    },
    {
      icon:        '📦',
      title:       'All Listings',
      description: 'View all available crop listings',
      color:       '#e67e22',
      path:        '/listings'
    },
    {
      icon:        '🗺️',
      title:       'Regional Supply',
      description: 'Check crop supply by region',
      color:       '#2980b9',
      path:        '/supply'
    },
    {
      icon:        '➕',
      title:       'Add Crop Listing',
      description: 'Add new crop availability listing',
      color:       '#27ae60',
      path:        '/listing'
    },
    {
      icon:        '🔔',
      title:       'Notifications',
      description: 'View market alerts and supply notifications',
      color:       '#e74c3c',
      path:        '/notifications'
    }
  ];
  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.logo}>🏪</span>
          <div>
            <h1 style={styles.headerTitle}>ALIP</h1>
            <p style={styles.headerSub}>Broker Dashboard</p>
          </div>
        </div>
        <div style={styles.headerRight}>
          <span style={styles.welcome}>🏪 {user?.full_name}</span>
          <button
            style={styles.logoutBtn}
              onClick={() => navigate('/profile')}
          >
             👤 Profile
          </button>
          <button style={styles.logoutBtn} onClick={handleLogout}>
            🚪 Logout
          </button>
        </div>
      </div>

      {/* Stats Banner */}
      <div style={styles.banner}>
        <h2 style={styles.bannerTitle}>
          Market Overview 📈
        </h2>
        {loading ? (
          <p style={styles.bannerText}>Loading market data...</p>
        ) : summary ? (
          <div style={styles.statsRow}>
            <div style={styles.statItem}>
              <p style={styles.statValue}>{summary.total_listings}</p>
              <p style={styles.statLabel}>Total Listings</p>
            </div>
            <div style={styles.statItem}>
              <p style={styles.statValue}>{summary.regions_active}</p>
              <p style={styles.statLabel}>Active Regions</p>
            </div>
            <div style={styles.statItem}>
              <p style={styles.statValue}>
                {Object.keys(
                  Object.values(summary.regional_summary || {})
                    .reduce((a, b) => ({...a, ...b}), {})
                ).length}
              </p>
              <p style={styles.statLabel}>Crop Types</p>
            </div>
          </div>
        ) : (
          <p style={styles.bannerText}>No market data available yet.</p>
        )}
      </div>

      {/* Module Cards */}
      <div style={styles.grid}>
        {modules.map((mod, idx) => (
          <div
            key={idx}
            style={styles.card}
            onClick={() => navigate(mod.path)}
          >
            <div style={{...styles.cardIcon, background: mod.color}}>
              {mod.icon}
            </div>
            <h3 style={styles.cardTitle}>{mod.title}</h3>
            <p style={styles.cardDesc}>{mod.description}</p>
            <button style={{...styles.cardBtn, background: mod.color}}>
              Open →
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f6fa' },
  header: {
    background:     'linear-gradient(135deg, #1a237e, #283593)',
    padding:        '16px 32px',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'space-between'
  },
  headerLeft:  { display: 'flex', alignItems: 'center', gap: '12px' },
  logo:        { fontSize: '32px' },
  headerTitle: { color: 'white', margin: '0', fontSize: '22px' },
  headerSub:   { color: '#9fa8da', margin: '0', fontSize: '12px' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '16px' },
  welcome:     { color: 'white', fontSize: '14px', fontWeight: '600' },
  logoutBtn: {
    padding:      '8px 16px',
    background:   'rgba(255,255,255,0.2)',
    color:        'white',
    border:       '1px solid rgba(255,255,255,0.4)',
    borderRadius: '8px',
    cursor:       'pointer',
    fontSize:     '13px'
  },
  banner: {
    background:   'linear-gradient(135deg, #283593, #3949ab)',
    margin:       '24px 32px',
    borderRadius: '16px',
    padding:      '32px',
    color:        'white'
  },
  bannerTitle: { margin: '0 0 16px', fontSize: '24px' },
  bannerText:  { margin: '0', opacity: 0.8 },
  statsRow:    { display: 'flex', gap: '40px' },
  statItem:    { textAlign: 'center' },
  statValue:   { fontSize: '36px', fontWeight: 'bold', margin: '0' },
  statLabel:   { opacity: 0.8, margin: '4px 0 0', fontSize: '13px' },
  grid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap:                 '24px',
    padding:             '0 32px 32px'
  },
  card: {
    background:   'white',
    borderRadius: '16px',
    padding:      '28px',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)',
    cursor:       'pointer',
    textAlign:    'center'
  },
  cardIcon: {
    width:         '64px',
    height:        '64px',
    borderRadius:  '16px',
    display:       'flex',
    alignItems:    'center',
    justifyContent:'center',
    fontSize:      '28px',
    margin:        '0 auto 16px'
  },
  cardTitle: { fontSize: '18px', fontWeight: 'bold', color: '#2c3e50', margin: '0 0 8px' },
  cardDesc:  { fontSize: '13px', color: '#666', margin: '0 0 20px' },
  cardBtn: {
    padding:      '10px 24px',
    color:        'white',
    border:       'none',
    borderRadius: '8px',
    cursor:       'pointer',
    fontWeight:   'bold',
    fontSize:     '14px'
  }
};
