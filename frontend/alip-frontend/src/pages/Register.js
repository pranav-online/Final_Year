import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registerUser } from '../services/api';
import AuthShell from '../components/AuthShell';
import toast from 'react-hot-toast';

export default function Register() {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'farmer',
    phone: '',
    location: ''
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await registerUser(form);
      toast.success('Registration successful! Please login.');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed!');
    }
    setLoading(false);
  };

  return (
    <AuthShell
      mode="register"
      eyebrow="Farmer Broker Crop Intelligence"
      title="Join ALIP"
      subtitle="start smarter farming"
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2 className="auth-form-title">Create your account</h2>
        <p className="auth-form-subtitle">
          Choose your role and connect to the ALIP agriculture network.
        </p>

        <div className="auth-role-container">
          {['farmer', 'broker'].map((role) => (
            <button
              key={role}
              type="button"
              className={`auth-role-button ${form.role === role ? 'active' : ''}`}
              onClick={() => setForm({ ...form, role })}
            >
              {role === 'farmer' ? 'Farmer' : 'Broker'}
            </button>
          ))}
        </div>

        {[
          { key: 'full_name', label: 'Full Name', type: 'text', placeholder: 'Enter your name' },
          { key: 'email', label: 'Email', type: 'email', placeholder: 'Enter your email' },
          { key: 'password', label: 'Password', type: 'password', placeholder: 'Create password' },
          { key: 'phone', label: 'Phone', type: 'text', placeholder: 'Phone number' },
          { key: 'location', label: 'Location', type: 'text', placeholder: 'Your city/district' }
        ].map((field) => (
          <div key={field.key} className="auth-input-group">
            <label className="auth-label">{field.label}</label>
            <input
              className="auth-input"
              type={field.type}
              placeholder={field.placeholder}
              value={form[field.key]}
              onChange={(e) => setForm({ ...form, [field.key]: e.target.value })}
              required={['full_name', 'email', 'password'].includes(field.key)}
            />
          </div>
        ))}

        <div className="auth-primary-wrap">
          <div className="auth-primary-ring" />
          <div className="auth-primary-ring second" />
          <button
            className="auth-primary-button"
            style={{ opacity: loading ? 0.7 : 1 }}
            type="submit"
            disabled={loading}
          >
            <span className="auth-button-icon">{loading ? '...' : '\u2713'}</span>
            <span>{loading ? 'Registering...' : 'Create Account'}</span>
          </button>
        </div>

        <p className="auth-switch">
          Already have an account?{' '}
          <Link to="/login" className="auth-switch-link">Login here</Link>
        </p>
      </form>
    </AuthShell>
  );
}
