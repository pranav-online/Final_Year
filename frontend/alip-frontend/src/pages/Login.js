import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { loginUser } from '../services/api';
import { useAuth } from '../context/AuthContext';
import AuthShell from '../components/AuthShell';
import toast from 'react-hot-toast';

export default function Login() {
  const [form, setForm] = useState({ email: '', password: '' });
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await loginUser(form);
      login({
        full_name: res.data.full_name,
        role: res.data.role
      }, res.data.access_token);

      toast.success(`Welcome back, ${res.data.full_name}!`);

      if (res.data.role === 'farmer') {
        navigate('/farmer');
      } else {
        navigate('/broker');
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed!');
    }
    setLoading(false);
  };

  return (
    <AuthShell
      mode="login"
      eyebrow="Real-time Farming Intelligence"
      title="ALIP"
      subtitle="secure farm access"
    >
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2 className="auth-form-title">Welcome back</h2>
        <p className="auth-form-subtitle">
          Login to continue to your agriculture intelligence portal.
        </p>

        <div className="auth-input-group">
          <label className="auth-label">Email</label>
          <input
            className="auth-input"
            type="email"
            placeholder="Enter your email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>

        <div className="auth-input-group">
          <label className="auth-label">Password</label>
          <input
            className="auth-input"
            type="password"
            placeholder="Enter your password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />
        </div>

        <div className="auth-primary-wrap">
          <div className="auth-primary-ring" />
          <div className="auth-primary-ring second" />
          <button
            className="auth-primary-button"
            style={{ opacity: loading ? 0.7 : 1 }}
            type="submit"
            disabled={loading}
          >
            <span className="auth-button-icon">{loading ? '...' : '\u{1F512}'}</span>
            <span>{loading ? 'Logging in...' : 'Login'}</span>
          </button>
        </div>

        <p className="auth-switch">
          Don't have an account?{' '}
          <Link to="/register" className="auth-switch-link">
            Register here
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
