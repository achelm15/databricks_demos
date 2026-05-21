import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api';
import MetricsGrid from '../components/MetricsGrid';
import GenieChat from '../components/GenieChat';
import SavedReports from '../components/SavedReports';

export default function Dashboard() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'chat' | 'reports'>('overview');
  const [features, setFeatures] = useState<Record<string, boolean>>({});

  const { data: session } = useQuery({
    queryKey: ['session'],
    queryFn: api.getMe,
  });

  const { data: featureData } = useQuery({
    queryKey: ['features'],
    queryFn: api.getFeatures,
  });

  useEffect(() => {
    if (featureData?.features) setFeatures(featureData.features);
  }, [featureData]);

  const handleLogout = () => {
    localStorage.removeItem('session_id');
    navigate('/login');
  };

  return (
    <div style={{ minHeight: '100vh', background: '#f8f9fa' }}>
      {/* Top Navigation */}
      <nav style={{
        background: '#1a1a2e',
        padding: '0.75rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        color: 'white'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ fontSize: '1.25rem' }}>📊</span>
          <h1 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>Campaign Reporting</h1>
          {session && (
            <span style={{
              background: 'rgba(255,255,255,0.15)',
              padding: '2px 10px',
              borderRadius: '12px',
              fontSize: '0.75rem'
            }}>
              {session.distributor_name}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {features.sandbox_mode && (
            <button
              onClick={() => navigate('/sandbox')}
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                border: '1px solid rgba(255,255,255,0.3)',
                background: 'transparent',
                color: 'white',
                cursor: 'pointer',
                fontSize: '0.8rem'
              }}
            >
              🔀 Sandbox
            </button>
          )}
          <button
            onClick={handleLogout}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: 'none',
              background: 'rgba(255,255,255,0.1)',
              color: 'white',
              cursor: 'pointer',
              fontSize: '0.8rem'
            }}
          >
            Sign Out
          </button>
        </div>
      </nav>

      {/* Tab Bar */}
      <div style={{
        background: 'white',
        borderBottom: '1px solid #e0e0e0',
        padding: '0 2rem',
        display: 'flex',
        gap: '0'
      }}>
        {[
          { key: 'overview', label: '📈 Campaign Overview', show: true },
          { key: 'chat', label: '🤖 Ask Genie', show: features.genie_chat },
          { key: 'reports', label: '📋 Saved Reports', show: true },
        ].filter(t => t.show).map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            style={{
              padding: '1rem 1.5rem',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? '#e63946' : '#666',
              borderBottom: activeTab === tab.key ? '3px solid #e63946' : '3px solid transparent',
              fontSize: '0.9rem'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ padding: '2rem', maxWidth: '1400px', margin: '0 auto' }}>
        {activeTab === 'overview' && <MetricsGrid />}
        {activeTab === 'chat' && <GenieChat />}
        {activeTab === 'reports' && <SavedReports />}
      </div>

      {/* Footer */}
      <div style={{
        textAlign: 'center',
        padding: '1rem',
        color: '#999',
        fontSize: '0.75rem',
        borderTop: '1px solid #eee'
      }}>
        Powered by Databricks Lakebase — Scale-to-zero • Synced Tables • pgvector • UC Governance
      </div>
    </div>
  );
}
