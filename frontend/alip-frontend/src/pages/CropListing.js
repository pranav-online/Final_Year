import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { addCropListing } from '../services/api';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

export default function CropListing() {
  const navigate    = useNavigate();
  const { user }    = useAuth();
  const [form, setForm] = useState({
    farmer_name:   user?.full_name || '',
    location:      '',
    crop_name:     '',
    quantity_kg:   '',
    price_per_kg:  '',
    status:        'available',
    contact:       ''
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    const quantity = Number(form.quantity_kg);
    const price = Number(form.price_per_kg);
    if (!form.farmer_name.trim() || !form.location.trim() || !form.crop_name.trim()) {
      toast.error('Enter your name, location, and crop.');
      return;
    }
    if (!Number.isFinite(quantity) || quantity <= 0 || !Number.isFinite(price) || price <= 0) {
      toast.error('Quantity and price must be greater than zero.');
      return;
    }
    setLoading(true);
    try {
      await addCropListing({
        ...form,
        farmer_name: form.farmer_name.trim(),
        location: form.location.trim(),
        crop_name: form.crop_name.trim(),
        quantity_kg: quantity,
        price_per_kg: price
      });
      toast.success('Crop listing added successfully!');
      setSuccess(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add listing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div style={styles.container}>
        <div style={styles.successBox}>
          <span style={styles.successIcon}>✅</span>
          <h2 style={styles.successTitle}>Listing Added!</h2>
          <p style={styles.successText}>
            Your crop has been listed in the market successfully.
          </p>
          <button
            style={styles.successBtn}
            onClick={() => {
              setSuccess(false);
              setForm({...form, crop_name: '', quantity_kg: '', price_per_kg: ''});
            }}
          >
            ➕ Add Another
          </button>
          <button
            style={{...styles.successBtn, background: '#666', marginLeft: '12px'}}
            onClick={() => navigate(user?.role === 'broker' ? '/broker' : '/farmer')}
          >
            ← Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <button
          style={styles.backBtn}
          onClick={() => navigate(user?.role === 'broker' ? '/broker' : '/farmer')}
        >
          ← Back
        </button>
        <h1 style={styles.headerTitle}>📦 Add Crop Listing</h1>
      </div>

      <div style={styles.content}>
        <form style={styles.card} onSubmit={handleSubmit}>
          <h2 style={styles.cardTitle}>List Your Crop for Sale</h2>
          <p style={styles.cardDesc}>
            Fill in the details to list your crop in the market
          </p>

          {[
            { key: 'farmer_name',  label: 'Farmer Name *',   type: 'text',   placeholder: 'Your name' },
            { key: 'location',     label: 'Location *',      type: 'text',   placeholder: 'City/District' },
            { key: 'crop_name',    label: 'Crop Name *',     type: 'text',   placeholder: 'e.g. rice, wheat' },
            { key: 'quantity_kg',  label: 'Quantity (kg) *', type: 'number', placeholder: 'e.g. 500' },
            { key: 'price_per_kg', label: 'Price per kg (₹)*',type: 'number',placeholder: 'e.g. 25' },
            { key: 'contact',      label: 'Contact Number',  type: 'text',   placeholder: 'Phone number' }
          ].map(field => (
            <div key={field.key} style={styles.inputGroup}>
              <label style={styles.label}>{field.label}</label>
              <input
                style={styles.input}
                type={field.type}
                required={field.key !== 'contact'}
                min={field.type === 'number' ? '0.01' : undefined}
                step={field.type === 'number' ? 'any' : undefined}
                placeholder={field.placeholder}
                value={form[field.key]}
                onChange={(e) => setForm({...form, [field.key]: e.target.value})}
              />
            </div>
          ))}

          <button
            style={{...styles.submitBtn, opacity: loading ? 0.7 : 1}}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? '⏳ Adding...' : '📦 Add Listing'}
          </button>
        </form>
      </div>
    </div>
  );
}

const styles = {
  container: { minHeight: '100vh', background: '#f5f6fa' },
  header: {
    background: 'linear-gradient(135deg, #1a472a, #2d6a4f)',
    padding: '16px 32px', display: 'flex',
    alignItems: 'center', gap: '16px'
  },
  backBtn: {
    padding: '8px 16px', background: 'rgba(255,255,255,0.2)',
    color: 'white', border: 'none', borderRadius: '8px',
    cursor: 'pointer', fontSize: '14px'
  },
  headerTitle: { color: 'white', margin: '0', fontSize: '22px' },
  content: { padding: '24px 32px', maxWidth: '600px', margin: '0 auto' },
  card: {
    background: 'white', borderRadius: '16px',
    padding: '32px', boxShadow: '0 4px 20px rgba(0,0,0,0.08)'
  },
  cardTitle: { fontSize: '20px', fontWeight: 'bold', color: '#2c3e50', margin: '0 0 8px' },
  cardDesc:  { color: '#666', fontSize: '14px', margin: '0 0 24px' },
  inputGroup: { marginBottom: '16px' },
  label: {
    display: 'block', marginBottom: '6px',
    fontWeight: '600', color: '#333', fontSize: '14px'
  },
  input: {
    width: '100%', padding: '12px 16px',
    border: '2px solid #e0e0e0', borderRadius: '8px',
    fontSize: '15px', outline: 'none', boxSizing: 'border-box'
  },
  submitBtn: {
    width: '100%', padding: '14px',
    background: 'linear-gradient(135deg, #27ae60, #2ecc71)',
    color: 'white', border: 'none', borderRadius: '8px',
    fontSize: '16px', fontWeight: 'bold', cursor: 'pointer', marginTop: '8px'
  },
  successBox: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    minHeight: '100vh', textAlign: 'center', padding: '32px'
  },
  successIcon:  { fontSize: '80px', marginBottom: '16px' },
  successTitle: { fontSize: '28px', color: '#27ae60', margin: '0 0 8px' },
  successText:  { color: '#666', margin: '0 0 24px', fontSize: '16px' },
  successBtn: {
    padding: '12px 24px', background: '#27ae60',
    color: 'white', border: 'none', borderRadius: '8px',
    fontSize: '15px', fontWeight: 'bold', cursor: 'pointer'
  }
};