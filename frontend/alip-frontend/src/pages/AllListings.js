import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMarketListings } from '../services/api';
import toast from 'react-hot-toast';

export default function AllListings() {
  const navigate                = useNavigate();
  const [listings, setListings] = useState([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState('');
  const [search, setSearch]     = useState('');
  const [filterCrop, setFilterCrop] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

 useEffect(() => {
    loadListings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadListings = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getMarketListings();
      setListings(Array.isArray(res.data.listings) ? res.data.listings : []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to load listings. Check the connection and try again.');
      toast.error('Failed to load listings!');
    } finally {
      setLoading(false);
    }
  };

  const normalizedSearch = search.trim().toLowerCase();
  const filtered = listings.filter((listing) => {
    const matchesSearch = !normalizedSearch || [
      listing.farmer_name,
      listing.location,
      listing.crop_name,
    ].some((value) => (value || '').toLowerCase().includes(normalizedSearch));
    const matchesCrop = filterCrop === 'all' || listing.crop_name === filterCrop;
    const matchesStatus = filterStatus === 'all' || listing.status === filterStatus;
    return matchesSearch && matchesCrop && matchesStatus;
  });

  // Get unique crop names for filter
  const uniqueCrops = ['all', ...new Set(listings.map(l => l.crop_name).filter(Boolean))];
  const uniqueStatuses = ['all', ...new Set(listings.map(l => l.status).filter(Boolean))];

  const getStatusColor = (status) => {
    if (status === 'available') return '#27ae60';
    if (status === 'sold')      return '#e74c3c';
    return '#f39c12';
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <span style={styles.loadingIcon}>⏳</span>
        <p>Loading listings...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.backBtn} onClick={() => navigate('/broker')}>
          ← Back
        </button>
        <h1 style={styles.headerTitle}>📦 All Crop Listings</h1>
        <button
          style={styles.refreshBtn}
          onClick={loadListings}
          disabled={loading}
        >
          🔄 Refresh
        </button>
      </div>

      <div style={styles.content}>
        {error && (
          <div style={styles.errorBox} role="alert">
            <span>{error}</span>
            <button style={styles.retryBtn} onClick={loadListings}>Retry</button>
          </div>
        )}
        {/* Stats Row */}
        <div style={styles.statsRow}>
          <div style={styles.statCard}>
            <p style={styles.statValue}>{listings.length}</p>
            <p style={styles.statLabel}>📦 Total Listings</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statValue}>
              {new Set(listings.map(l => l.location)).size}
            </p>
            <p style={styles.statLabel}>📍 Regions</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statValue}>
              {new Set(listings.map(l => l.crop_name)).size}
            </p>
            <p style={styles.statLabel}>🌾 Crop Types</p>
          </div>
          <div style={styles.statCard}>
            <p style={styles.statValue}>
              {listings.reduce((a, b) => a + b.quantity_kg, 0).toFixed(0)} kg
            </p>
            <p style={styles.statLabel}>⚖️ Total Quantity</p>
          </div>
        </div>

        {/* Search and Filter */}
        <div style={styles.filterCard}>
          <div style={styles.filterRow}>
            <input
              style={styles.searchInput}
              placeholder="🔍 Search by farmer, location, or crop..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              style={styles.select}
              value={filterCrop}
              onChange={(e) => setFilterCrop(e.target.value)}
            >
              {uniqueCrops.map(crop => (
                <option key={crop} value={crop}>
                  {crop === 'all' ? '🌾 All Crops' : crop}
                </option>
              ))}
            </select>
            <select
              style={styles.select}
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              {uniqueStatuses.map(status => (
                <option key={status} value={status}>
                  {status === 'all' ? 'All statuses' : status}
                </option>
              ))}
            </select>
          </div>
          <p style={styles.resultCount}>
            Showing {filtered.length} of {listings.length} listings
          </p>
        </div>

        {/* Listings Grid */}
        {filtered.length > 0 ? (
          <div style={styles.grid}>
            {filtered.map((listing, idx) => (
              <div key={listing._id || listing.id || `${listing.location}-${listing.crop_name}-${idx}`} style={styles.listingCard}>
                {/* Card Header */}
                <div style={styles.cardHeader}>
                  <span style={styles.cropIcon}>🌾</span>
                  <div>
                    <h3 style={styles.cropName}>
                      {listing.crop_name.charAt(0).toUpperCase() +
                       listing.crop_name.slice(1)}
                    </h3>
                    <span style={{
                      ...styles.statusBadge,
                      background: getStatusColor(listing.status)
                    }}>
                      {listing.status}
                    </span>
                  </div>
                </div>

                {/* Card Details */}
                <div style={styles.cardDetails}>
                  <div style={styles.detailRow}>
                    <span style={styles.detailIcon}>👨‍🌾</span>
                    <span style={styles.detailText}>{listing.farmer_name}</span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailIcon}>📍</span>
                    <span style={styles.detailText}>
                      {listing.location.charAt(0).toUpperCase() +
                       listing.location.slice(1)}
                    </span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailIcon}>⚖️</span>
                    <span style={styles.detailText}>
                      {listing.quantity_kg} kg available
                    </span>
                  </div>
                  <div style={styles.detailRow}>
                    <span style={styles.detailIcon}>💰</span>
                    <span style={styles.detailText}>
                      ₹{listing.price_per_kg}/kg
                    </span>
                  </div>
                  {listing.contact && (
                    <div style={styles.detailRow}>
                      <span style={styles.detailIcon}>📞</span>
                      <span style={styles.detailText}>{listing.contact}</span>
                    </div>
                  )}
                </div>

                {/* Total Value */}
                <div style={styles.totalValue}>
                  <p style={styles.totalLabel}>Total Value</p>
                  <p style={styles.totalAmount}>
                    ₹{(listing.quantity_kg * listing.price_per_kg).toFixed(2)}
                  </p>
                </div>

                {/* Contact Button */}
                <button
                  style={styles.contactBtn}
                  onClick={() => {
                    if (listing.contact) {
                      toast.success(`Contact: ${listing.contact}`);
                    } else {
                      toast.error('No contact info available');
                    }
                  }}
                >
                  📞 Contact Farmer
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div style={styles.emptyCard}>
            <span style={styles.emptyIcon}>📭</span>
            <h3 style={styles.emptyTitle}>No Listings Found</h3>
            <p style={styles.emptyText}>
              {listings.length === 0
                ? 'No crop listings available yet. Farmers need to add listings.'
                : 'No listings match your search. Try different filters.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container:        { minHeight: '100vh', background: '#f5f6fa' },
  loadingContainer: {
    minHeight:      '100vh',
    display:        'flex',
    flexDirection:  'column',
    alignItems:     'center',
    justifyContent: 'center',
    fontSize:       '18px',
    color:          '#666'
  },
  loadingIcon: { fontSize: '48px', marginBottom: '16px' },
  header: {
    background:     'linear-gradient(135deg, #1a237e, #283593)',
    padding:        '16px 32px',
    display:        'flex',
    alignItems:     'center',
    gap:            '16px'
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
  headerTitle: { color: 'white', margin: '0', fontSize: '22px', flex: 1 },
  refreshBtn: {
    padding:      '8px 16px',
    background:   'rgba(255,255,255,0.2)',
    color:        'white',
    border:       '1px solid rgba(255,255,255,0.4)',
    borderRadius: '8px',
    cursor:       'pointer',
    fontSize:     '13px'
  },
  content: { padding: '24px 32px' },
  statsRow: {
    display:             'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap:                 '16px',
    marginBottom:        '24px'
  },
  statCard: {
    background:   'white',
    borderRadius: '12px',
    padding:      '20px',
    textAlign:    'center',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)'
  },
  statValue: {
    fontSize:   '24px',
    fontWeight: 'bold',
    color:      '#2c3e50',
    margin:     '0 0 4px'
  },
  statLabel: { color: '#666', margin: '0', fontSize: '13px' },
  filterCard: {
    background:   'white',
    borderRadius: '16px',
    padding:      '20px',
    marginBottom: '24px',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)'
  },
  filterRow: { display: 'flex', gap: '12px', marginBottom: '8px' },
  searchInput: {
    flex:         1,
    padding:      '12px 16px',
    border:       '2px solid #e0e0e0',
    borderRadius: '8px',
    fontSize:     '14px',
    outline:      'none'
  },
  select: {
    padding:      '12px 16px',
    border:       '2px solid #e0e0e0',
    borderRadius: '8px',
    fontSize:     '14px',
    outline:      'none',
    cursor:       'pointer',
    background:   'white'
  },
  resultCount: { color: '#666', margin: '0', fontSize: '13px' },
  errorBox: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', padding: '14px 16px', marginBottom: '16px', border: '1px solid #fda29b', borderRadius: '8px', background: '#fff5f5', color: '#912018', fontSize: '14px' },
  retryBtn: { border: '1px solid #d92d20', borderRadius: '6px', padding: '7px 12px', background: 'white', color: '#b42318', cursor: 'pointer', fontWeight: '600' },
  grid: {
    display:             'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap:                 '20px'
  },
  listingCard: {
    background:   'white',
    borderRadius: '16px',
    padding:      '20px',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)'
  },
  cardHeader: {
    display:      'flex',
    alignItems:   'center',
    gap:          '12px',
    marginBottom: '16px',
    paddingBottom:'16px',
    borderBottom: '1px solid #f0f0f0'
  },
  cropIcon:  { fontSize: '36px' },
  cropName: {
    fontSize:   '18px',
    fontWeight: 'bold',
    color:      '#2c3e50',
    margin:     '0 0 4px'
  },
  statusBadge: {
    display:      'inline-block',
    padding:      '2px 10px',
    borderRadius: '10px',
    color:        'white',
    fontSize:     '11px',
    fontWeight:   'bold'
  },
  cardDetails:  { marginBottom: '16px' },
  detailRow: {
    display:      'flex',
    alignItems:   'center',
    gap:          '8px',
    marginBottom: '8px'
  },
  detailIcon: { fontSize: '16px', width: '20px' },
  detailText: { color: '#555', fontSize: '14px' },
  totalValue: {
    background:   '#f0fff4',
    borderRadius: '8px',
    padding:      '12px',
    marginBottom: '12px',
    display:      'flex',
    justifyContent:'space-between',
    alignItems:   'center'
  },
  totalLabel:  { color: '#666', margin: '0', fontSize: '13px' },
  totalAmount: { color: '#27ae60', fontWeight: 'bold', margin: '0', fontSize: '16px' },
  contactBtn: {
    width:        '100%',
    padding:      '10px',
    background:   'linear-gradient(135deg, #1a237e, #283593)',
    color:        'white',
    border:       'none',
    borderRadius: '8px',
    cursor:       'pointer',
    fontWeight:   'bold',
    fontSize:     '14px'
  },
  emptyCard: {
    background:   'white',
    borderRadius: '16px',
    padding:      '48px',
    textAlign:    'center',
    boxShadow:    '0 4px 20px rgba(0,0,0,0.08)'
  },
  emptyIcon:  { fontSize: '64px', display: 'block', marginBottom: '16px' },
  emptyTitle: { fontSize: '20px', color: '#2c3e50', margin: '0 0 8px' },
  emptyText:  { color: '#666', fontSize: '14px', margin: '0' }
};