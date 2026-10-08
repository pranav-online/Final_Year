import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function FarmerDashboard() {
  const { user, logout } = useAuth();
  const navigate         = useNavigate();

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully!');
    navigate('/login');
  };

  const modules = [
    {
      icon:        '🔬',
      title:       'Disease Detection',
      description: 'Upload leaf image to detect crop disease',
      color:       '#e74c3c',
      path:        '/disease'
    },
    {
      icon:        '🌦️',
      title:       'Weather Advisory',
      description: 'Get real-time weather based farming advice',
      color:       '#3498db',
      path:        '/weather'
    },
    {
      icon:        '🌱',
      title:       'Crop Recommendation',
      description: 'Get best crop suggestion for your region',
      color:       '#27ae60',
      path:        '/crop'
    },
    {
      icon:        '📦',
      title:       'Add Crop Listing',
      description: 'List your crop for market sale',
      color:       '#f39c12',
      path:        '/listing'
    }
  ];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <span style={styles.logo}>🌱</span>
          <div>
            <h1 style={styles.headerTitle}>ALIP</h1>
            <p style={styles.headerSub}>Farmer Dashboard</p>
          </div>
        </div>
        <div style={styles.headerRight}>
          <span style={styles.welcome}>
            👨‍🌾 {user?.full_name}
          </span>
          <button
               style={styles.logoutBtn}
               onClick={() => navigate('/profile')}
          >👤 Profile</button>
          <button style={styles.logoutBtn} onClick={handleLogout}>
            🚪 Logout
          </button>
        </div>
      </div>

      {/* Welcome Banner */}
      <div style={styles.banner}>
        <h2 style={styles.bannerTitle}>
          Welcome back, {user?.full_name}! 🌾
        </h2>
        <p style={styles.bannerText}>
          What would you like to do today?
        </p>
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
  container: {
    minHeight:  '100vh',
    background: '#f5f6fa'
  },
  header: {
    background:     'linear-gradient(135deg, #1a472a, #2d6a4f)',
    padding:        '16px 32px',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'space-between'
  },
  
  headerLeft: {
    display:    'flex',
    alignItems: 'center',
    gap:        '12px'
  },
  logo:        { fontSize: '32px' },
  headerTitle: { color: 'white', margin: '0', fontSize: '22px' },
  headerSub:   { color: '#a8d5b5', margin: '0', fontSize: '12px' },
  headerRight: {
    display:    'flex',
    alignItems: 'center',
    gap:        '16px'
  },
  welcome: {
    color:      'white',
    fontSize:   '14px',
    fontWeight: '600'
  },
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
    background:   'linear-gradient(135deg, #2d6a4f, #40916c)',
    margin:       '24px 32px',
    borderRadius: '16px',
    padding:      '32px',
    color:        'white'
  },
  bannerTitle: { margin: '0 0 8px 0', fontSize: '24px' },
  bannerText:  { margin: '0', opacity: 0.8 },
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
    transition:   'transform 0.2s',
    textAlign:    'center'
  },
  cardIcon: {
    width:        '64px',
    height:       '64px',
    borderRadius: '16px',
    display:      'flex',
    alignItems:   'center',
    justifyContent:'center',
    fontSize:     '28px',
    margin:       '0 auto 16px'
  },
  cardTitle: {
    fontSize:     '18px',
    fontWeight:   'bold',
    color:        '#2c3e50',
    margin:       '0 0 8px 0'
  },
  cardDesc: {
    fontSize: '13px',
    color:    '#666',
    margin:   '0 0 20px 0'
  },
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
