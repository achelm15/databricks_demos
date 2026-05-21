import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

interface SandboxInfo {
  branch_id: string;
  branch_name: string;
  expires_in: string;
  message: string;
}

export default function Sandbox() {
  const navigate = useNavigate();
  const [sandbox, setSandbox] = useState<SandboxInfo | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const handleCreate = async () => {
    setCreating(true);
    setError('');
    try {
      const result = await api.createSandbox();
      setSandbox(result);
    } catch (e: any) {
      setError(e.message || 'Failed to create sandbox');
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async () => {
    if (!sandbox) return;
    try {
      await api.deleteSandbox(sandbox.branch_id);
      setSandbox(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f8f9fa' }}>
      {/* Nav */}
      <nav style={{
        background: '#1a1a2e',
        padding: '0.75rem 2rem',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        color: 'white'
      }}>
        <button
          onClick={() => navigate('/dashboard')}
          style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '1rem' }}
        >
          ← Back
        </button>
        <h1 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>🔀 Sandbox Mode</h1>
        <span style={{
          background: '#f4a261',
          padding: '2px 8px',
          borderRadius: '4px',
          fontSize: '0.7rem',
          fontWeight: 600
        }}>
          LAKEBASE BRANCHING
        </span>
      </nav>

      <div style={{ padding: '3rem', maxWidth: '800px', margin: '0 auto' }}>
        {/* Explanation */}
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '2rem',
          marginBottom: '2rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
        }}>
          <h2 style={{ margin: '0 0 1rem', fontSize: '1.2rem' }}>What is Sandbox Mode?</h2>
          <p style={{ color: '#555', lineHeight: 1.6, marginBottom: '1rem' }}>
            Sandbox mode creates an <strong>instant copy-on-write branch</strong> of the production database using Lakebase branching.
            This gives you a complete, isolated environment to:
          </p>
          <ul style={{ color: '#555', lineHeight: 2, paddingLeft: '1.5rem' }}>
            <li>Test audience segments before activating to a live campaign</li>
            <li>Run what-if scenarios on frequency caps without affecting production</li>
            <li>Explore data freely without cross-tenant leakage risk</li>
            <li>Compare sandbox results with production before promoting changes</li>
          </ul>
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem 1rem',
            background: '#f0f8ff',
            borderRadius: '8px',
            fontSize: '0.8rem',
            color: '#457b9d'
          }}>
            <strong>How it works:</strong> Lakebase creates a branch in ~2 seconds using copy-on-write storage.
            No data is duplicated. Only changes you make in the sandbox consume additional storage.
            Branches auto-expire after 1 hour.
          </div>
        </div>

        {/* Action Area */}
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '2rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
          textAlign: 'center'
        }}>
          {!sandbox ? (
            <>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔀</div>
              <button
                onClick={handleCreate}
                disabled={creating}
                style={{
                  padding: '1rem 2rem',
                  borderRadius: '8px',
                  border: 'none',
                  background: '#2a9d8f',
                  color: 'white',
                  fontWeight: 600,
                  fontSize: '1rem',
                  cursor: 'pointer'
                }}
              >
                {creating ? 'Creating Branch...' : 'Create Sandbox Branch'}
              </button>
              {error && <p style={{ color: '#e63946', marginTop: '1rem' }}>{error}</p>}
            </>
          ) : (
            <div>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>✅</div>
              <h3 style={{ color: '#2a9d8f' }}>Sandbox Active!</h3>
              <div style={{
                background: '#f5f5f5',
                borderRadius: '8px',
                padding: '1rem',
                marginTop: '1rem',
                textAlign: 'left',
                fontSize: '0.85rem'
              }}>
                <p><strong>Branch:</strong> {sandbox.branch_id}</p>
                <p><strong>Expires:</strong> {sandbox.expires_in}</p>
                <p><strong>Status:</strong> {sandbox.message}</p>
              </div>
              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button
                  onClick={() => navigate('/dashboard')}
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '6px',
                    border: 'none',
                    background: '#457b9d',
                    color: 'white',
                    cursor: 'pointer'
                  }}
                >
                  Use Sandbox
                </button>
                <button
                  onClick={handleDelete}
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '6px',
                    border: '1px solid #e63946',
                    background: 'transparent',
                    color: '#e63946',
                    cursor: 'pointer'
                  }}
                >
                  Delete Branch
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
