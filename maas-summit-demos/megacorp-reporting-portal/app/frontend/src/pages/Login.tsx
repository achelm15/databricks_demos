import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const TENANTS = [
  { id: 'big-mountain', name: 'Big Mountain Media', tier: 'enterprise' },
  { id: 'curious-globe', name: 'Curious Globe Networks', tier: 'premium' },
  { id: 'rainbow-hemisphere', name: 'Rainbow Hemisphere Inc', tier: 'premium' },
  { id: 'wily-one', name: 'Wily One Digital', tier: 'standard' },
  { id: 'large-mouse', name: 'Large Mouse Entertainment', tier: 'enterprise' },
];

export default function Login() {
  const [selectedTenant, setSelectedTenant] = useState('');
  const [role, setRole] = useState<'admin' | 'analyst'>('admin');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async () => {
    if (!selectedTenant) return;
    setLoading(true);
    setError('');
    try {
      const email = `${role}@${selectedTenant}.demo`;
      await api.login(email, selectedTenant);
      navigate('/dashboard');
    } catch (e: any) {
      setError(e.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem'
    }}>
      <div style={{
        background: 'white',
        borderRadius: '16px',
        padding: '3rem',
        width: '100%',
        maxWidth: '480px',
        boxShadow: '0 25px 50px rgba(0,0,0,0.3)'
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📊</div>
          <h1 style={{ fontSize: '1.5rem', color: '#1a1a2e', margin: 0 }}>
            Campaign Reporting Portal
          </h1>
          <p style={{ color: '#666', marginTop: '0.5rem', fontSize: '0.9rem' }}>
            Powered by Databricks Lakebase
          </p>
        </div>

        {/* Tenant Selection */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', color: '#333' }}>
            Select Your Organization
          </label>
          <div style={{ display: 'grid', gap: '0.5rem' }}>
            {TENANTS.map(t => (
              <button
                key={t.id}
                onClick={() => setSelectedTenant(t.id)}
                style={{
                  padding: '0.75rem 1rem',
                  border: selectedTenant === t.id ? '2px solid #e63946' : '2px solid #eee',
                  borderRadius: '8px',
                  background: selectedTenant === t.id ? '#fff5f5' : 'white',
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  transition: 'all 0.2s'
                }}
              >
                <span style={{ fontWeight: 500 }}>{t.name}</span>
                <span style={{
                  fontSize: '0.7rem',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: t.tier === 'enterprise' ? '#e63946' : t.tier === 'premium' ? '#f4a261' : '#ccc',
                  color: 'white',
                  fontWeight: 600,
                  textTransform: 'uppercase'
                }}>
                  {t.tier}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Role Selection */}
        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', fontWeight: 600, marginBottom: '0.5rem', color: '#333' }}>
            Role
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {(['admin', 'analyst'] as const).map(r => (
              <button
                key={r}
                onClick={() => setRole(r)}
                style={{
                  flex: 1,
                  padding: '0.6rem',
                  border: role === r ? '2px solid #e63946' : '2px solid #eee',
                  borderRadius: '8px',
                  background: role === r ? '#fff5f5' : 'white',
                  cursor: 'pointer',
                  fontWeight: 500,
                  textTransform: 'capitalize'
                }}
              >
                {r === 'admin' ? '👑' : '📈'} {r}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{ color: '#e63946', marginBottom: '1rem', fontSize: '0.9rem' }}>
            {error}
          </div>
        )}

        {/* Login Button */}
        <button
          onClick={handleLogin}
          disabled={!selectedTenant || loading}
          style={{
            width: '100%',
            padding: '0.9rem',
            borderRadius: '8px',
            border: 'none',
            background: selectedTenant ? '#e63946' : '#ccc',
            color: 'white',
            fontWeight: 600,
            fontSize: '1rem',
            cursor: selectedTenant ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s'
          }}
        >
          {loading ? 'Signing in...' : 'Sign In to Portal'}
        </button>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.75rem', color: '#999' }}>
          <p>Demo: Multi-Tenant Self-Serve Reporting Portal</p>
          <p style={{ marginTop: '0.25rem' }}>
            Scale-to-zero • Branching • Synced Tables • pgvector • UC RLS
          </p>
        </div>
      </div>
    </div>
  );
}
