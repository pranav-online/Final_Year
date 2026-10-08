import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function UserProfile() {
  const navigate      = useNavigate();
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');

  const handleLogout = () => {
    logout();
    toast.success('Logged out successfully!');
    navigate('/login');
  };

  const stats = user?.role === 'farmer'
    ? [
        { icon: '🔬', label: 'Disease Scans',      value: '12' },
        { icon: '🌦️', label: 'Weather Checks',     value: '8'  },
        { icon: '🌱', label: 'Crop Recommendations',value: '5'  },
        { icon: '📦', label: 'Crop Listings',       value: '3'  }
      ]
    : [
        { icon: '📊', label: 'Demand Analysis',    value: '15' },
        { icon: '📦', label: 'Listings Viewed',    value: '24' },
        { icon: '🗺️', label: 'Regions Monitored',  value: '6'  },
        { icon: '🔔', label: 'Alerts Received',    value: '9'  }
      ];

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={{
        ...styles.header,
        background: user?.role === 'farmer'
          ? 'linear-gradient(135deg, #1a472a, #2d6a4f)'
          : 'linear-gradient(135deg, #1a237e, #283593)'
      }}>
        <button
          style={styles.backBtn}
          onClick={() => navigate(user?.role === 'farmer' ? '/farmer' : '/broker')}
        >
          ← Back
        </button>
        <h1 style={styles.headerTitle}>👤 My Profile</h1>
      </div>

      <div style={styles.content}>
        {/* Profile Card */}
        <div style={styles.profileCard}>
          {/* Avatar */}
          <div style={{
            ...styles.avatar,
            background: user?.role === 'farmer'
              ? 'linear-gradient(135deg, #1a472a, #2d6a4f)'
              : 'linear-gradient(135deg, #1a237e, #283593)'
          }}>
            {user?.full_name?.charAt(0).toUpperCase()}
          </div>

          <h2 style={styles.userName}>{user?.full_name}</h2>
          <span style={{
            ...styles.roleBadge,
            background: user?.role === 'farmer' ? '#27ae60' : '#3949ab'
          }}>
            {user?.role === 'farmer' ? '👨‍🌾 Farmer' : '🏪 Broker'}
          </span>

          {/* Tabs */}
          <div style={styles.tabs}>
            {['profile', 'stats', 'settings'].map(tab => (
              <button
                key={tab}
                style={{
                  ...styles.tab,
                  borderBottom: activeTab === tab
                    ? '3px solid #2d6a4f' : '3px solid transparent',
                  color: activeTab === tab ? '#2d6a4f' : '#666',
                  fontWeight: activeTab === tab ? 'bold' : 'normal'
                }}
                onClick={() => setActiveTab(tab)}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div style={styles.tabContent}>
              {[
                { icon: '👤', label: 'Full Name', value: user?.full_name },
                { icon: '📧', label: 'Email',     value: user?.email || 'Not available' },
                { icon: '🎭', label: 'Role',      value: user?.role?.charAt(0).toUpperCase() + user?.role?.slice(1) },
              ].map((item, idx) => (
                <div key={idx} style={styles.infoRow}>
                  <span style={styles.infoIcon}>{item.icon}</span>
                  <div>
                    <p style={styles.infoLabel}>{item.label}</p>
                    <p style={styles.infoValue}>{item.value}</p>
                  </div>
                </div>
              ))}

              {/* Account Info */}
              <div style={styles.accountBox}>
                <h3 style={styles.accountTitle}>📋 Account Information</h3>
                <div style={styles.accountRow}>
                  <span style={styles.accountLabel}>Account Type</span>
                  <span style={styles.accountValue}>
                    {user?.role === 'farmer' ? 'Farmer Account' : 'Broker Account'}
                  </span>
                </div>
                <div style={styles.accountRow}>
                  <span style={styles.accountLabel}>Platform</span>
                  <span style={styles.accountValue}>ALIP v1.0</span>
                </div>
                <div style={styles.accountRow}>
                  <span style={styles.accountLabel}>Status</span>
                  <span style={{...styles.accountValue, color: '#27ae60'}}>
                    ✅ Active
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Stats Tab */}
          {activeTab === 'stats' && (
            <div style={styles.tabContent}>
              <h3 style={styles.statsTitle}>📊 Your Activity Stats</h3>
              <div style={styles.statsGrid}>
                {stats.map((stat, idx) => (
                  <div key={idx} style={styles.statCard}>
                    <span style={styles.statIcon}>{stat.icon}</span>
                    <p style={styles.statValue}>{stat.value}</p>
                    <p style={styles.statLabel}>{stat.label}</p>
                  </div>
                ))}
              </div>

              {/* Activity Summary */}
              <div style={styles.activityBox}>
                <h3 style={styles.activityTitle}>🌟 Platform Usage</h3>
                {[
                  { label: 'Disease Detection', percent: 75, color: '#e74c3c' },
                  { label: 'Weather Advisory',  percent: 50, color: '#3498db' },
                  { label: 'Crop Recommendation',percent: 40, color: '#27ae60' },
                  { label: 'Market Module',      percent: 60, color: '#f39c12' }
                ].map((item, idx) => (
                  <div key={idx} style={styles.activityRow}>
                    <div style={styles.activityHeader}>
                      <span style={styles.activityLabel}>{item.label}</span>
                      <span style={styles.activityPercent}>{item.percent}%</span>
                    </div>
                    <div style={styles.progressTrack}>
                      <div style={{
                        ...styles.progressFill,
                        width:      `${item.percent}%`,
                        background: item.color
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Settings Tab */}
          {activeTab === 'settings' && (
            <div style={styles.tabContent}>
              <h3 style={styles.settingsTitle}>⚙️ Account Settings</h3>

              {/* Settings Options */}
              {[
                { icon: '🔔', label: 'Notifications',    desc: 'Receive market alerts'    },
                { icon: '🌙', label: 'Dark Mode',        desc: 'Toggle dark theme'        },
                { icon: '🌐', label: 'Language',         desc: 'English (Default)'        },
                { icon: '📱', label: 'Mobile Alerts',    desc: 'SMS notifications'        }
              ].map((setting, idx) => (
                <div key={idx} style={styles.settingRow}>
                  <div style={styles.settingLeft}>
                    <span style={styles.settingIcon}>{setting.icon}</span>
                    <div>
                      <p style={styles.settingLabel}>{setting.label}</p>
                      <p style={styles.settingDesc}>{setting.desc}</p>
                    </div>
                  </div>
                  <div style={styles.toggle}>
                    <div style={styles.toggleDot} />
                  </div>
                </div>
              ))}

              {/* Danger Zone */}
              <div style={styles.dangerZone}>
                <h3 style={styles.dangerTitle}>⚠️ Account Actions</h3>
                <button
                  style={styles.logoutBtn}
                  onClick={handleLogout}
                >
                  🚪 Logout from ALIP
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f6fa' },
  header: {
    padding:     '16px 32px',
    display:     'flex',
    alignItems:  'center',
    gap:         '16px'
  },
  backBtn: {
    padding:      '8px 16px',
    background:   'rgba(255,255,255,0.2)',
    color:        'white',
    border:       'none',
    borderRadius: '8px',
    cursor:       'pointer',
    fontSize:     '14px'
  },
  headerTitle: { color: 'white', margin: '0', fontSize: '22px' },
  content: {
    padding:        '24px 32px',
    display:        'flex',
    justifyContent: 'center'
  },
  profileCard: {
    background:   'white',
    borderRadius: '20px',
    padding:      '32px',
    width:        '600px',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)',
    textAlign:    'center'
  },
  avatar: {
    width:          '80px',
    height:         '80px',
    borderRadius:   '50%',
    display:        'flex',
    alignItems:     'center',
    justifyContent: 'center',
    fontSize:       '32px',
    fontWeight:     'bold',
    color:          'white',
    margin:         '0 auto 16px'
  },
  userName: { fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', margin: '0 0 8px' },
  roleBadge: {
    display:      'inline-block',
    padding:      '6px 16px',
    borderRadius: '20px',
    color:        'white',
    fontSize:     '13px',
    fontWeight:   'bold',
    marginBottom: '24px'
  },
  tabs: {
    display:       'flex',
    borderBottom:  '1px solid #f0f0f0',
    marginBottom:  '24px',
    justifyContent:'center',
    gap:           '8px'
  },
  tab: {
    padding:    '12px 24px',
    background: 'none',
    border:     'none',
    cursor:     'pointer',
    fontSize:   '15px',
    transition: 'all 0.2s'
  },
  tabContent:   { textAlign: 'left' },
  infoRow: {
    display:      'flex',
    alignItems:   'center',
    gap:          '16px',
    padding:      '16px',
    background:   '#f8f9fa',
    borderRadius: '10px',
    marginBottom: '12px'
  },
  infoIcon:  { fontSize: '24px' },
  infoLabel: { color: '#999', fontSize: '12px', margin: '0 0 2px' },
  infoValue: { color: '#2c3e50', fontSize: '15px', fontWeight: '600', margin: '0' },
  accountBox: {
    background:   '#f0fff4',
    borderRadius: '12px',
    padding:      '16px',
    marginTop:    '16px'
  },
  accountTitle: { fontSize: '15px', color: '#2c3e50', margin: '0 0 12px' },
  accountRow: {
    display:        'flex',
    justifyContent: 'space-between',
    padding:        '8px 0',
    borderBottom:   '1px solid #e0f2e9'
  },
  accountLabel: { color: '#666', fontSize: '13px' },
  accountValue: { color: '#2c3e50', fontSize: '13px', fontWeight: '600' },
  statsTitle:  { fontSize: '16px', color: '#2c3e50', margin: '0 0 16px' },
  statsGrid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap:                 '12px',
    marginBottom:        '20px'
  },
  statCard: {
    background:   '#f8f9fa',
    borderRadius: '12px',
    padding:      '20px',
    textAlign:    'center'
  },
  statIcon:  { fontSize: '28px', display: 'block', marginBottom: '8px' },
  statValue: { fontSize: '24px', fontWeight: 'bold', color: '#2c3e50', margin: '0 0 4px' },
  statLabel: { color: '#666', fontSize: '12px', margin: '0' },
  activityBox: {
    background:   '#f8f9fa',
    borderRadius: '12px',
    padding:      '16px'
  },
  activityTitle:  { fontSize: '15px', color: '#2c3e50', margin: '0 0 16px' },
  activityRow:    { marginBottom: '14px' },
  activityHeader: { display: 'flex', justifyContent: 'space-between', marginBottom: '6px' },
  activityLabel:  { color: '#555', fontSize: '13px' },
  activityPercent:{ color: '#2c3e50', fontSize: '13px', fontWeight: 'bold' },
  progressTrack: {
    height:       '8px',
    background:   '#e0e0e0',
    borderRadius: '4px',
    overflow:     'hidden'
  },
  progressFill: {
    height:       '100%',
    borderRadius: '4px',
    transition:   'width 0.5s ease'
  },
  settingsTitle: { fontSize: '16px', color: '#2c3e50', margin: '0 0 16px' },
  settingRow: {
    display:        'flex',
    justifyContent: 'space-between',
    alignItems:     'center',
    padding:        '16px',
    background:     '#f8f9fa',
    borderRadius:   '10px',
    marginBottom:   '10px'
  },
  settingLeft:  { display: 'flex', alignItems: 'center', gap: '12px' },
  settingIcon:  { fontSize: '24px' },
  settingLabel: { fontWeight: '600', color: '#2c3e50', margin: '0 0 2px', fontSize: '14px' },
  settingDesc:  { color: '#999', margin: '0', fontSize: '12px' },
  toggle: {
    width:          '44px',
    height:         '24px',
    background:     '#27ae60',
    borderRadius:   '12px',
    display:        'flex',
    alignItems:     'center',
    padding:        '2px',
    cursor:         'pointer',
    justifyContent: 'flex-end'
  },
  toggleDot: {
    width:        '20px',
    height:       '20px',
    background:   'white',
    borderRadius: '50%'
  },
  dangerZone: {
    background:   '#fff5f5',
    borderRadius: '12px',
    padding:      '16px',
    marginTop:    '20px'
  },
  dangerTitle: { fontSize: '15px', color: '#e74c3c', margin: '0 0 12px' },
  logoutBtn: {
    width:        '100%',
    padding:      '12px',
    background:   '#e74c3c',
    color:        'white',
    border:       'none',
    borderRadius: '8px',
    fontSize:     '15px',
    fontWeight:   'bold',
    cursor:       'pointer'
  }
};