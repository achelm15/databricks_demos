import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../api';

export default function SavedReports() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [showNew, setShowNew] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newQuery, setNewQuery] = useState('');

  const { data: reportsData, isLoading } = useQuery({
    queryKey: ['reports', searchQuery],
    queryFn: () => searchQuery ? api.searchReports(searchQuery) : api.getReports(),
  });

  const saveMutation = useMutation({
    mutationFn: (report: { title: string; query_text: string }) => api.saveReport(report),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      setShowNew(false);
      setNewTitle('');
      setNewQuery('');
    }
  });

  const reports = reportsData?.reports || [];

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Saved Reports</h2>
          <p style={{ color: '#666', fontSize: '0.8rem', marginTop: '0.25rem' }}>
            Reports are stored in Lakebase with pgvector embeddings for semantic search
          </p>
        </div>
        <button
          onClick={() => setShowNew(!showNew)}
          style={{
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            border: 'none',
            background: '#e63946',
            color: 'white',
            cursor: 'pointer',
            fontWeight: 500
          }}
        >
          + New Report
        </button>
      </div>

      {/* Search */}
      <div style={{ marginBottom: '1.5rem' }}>
        <input
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          placeholder="Search reports (semantic search via pgvector)..."
          style={{
            width: '100%',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            border: '2px solid #e0e0e0',
            fontSize: '0.9rem'
          }}
        />
      </div>

      {/* New Report Form */}
      {showNew && (
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '1.5rem',
          marginBottom: '1.5rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
        }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem' }}>Save New Report</h3>
          <input
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            placeholder="Report title..."
            style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ddd', marginBottom: '0.75rem' }}
          />
          <textarea
            value={newQuery}
            onChange={e => setNewQuery(e.target.value)}
            placeholder="Query or question..."
            rows={3}
            style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ddd', marginBottom: '0.75rem', resize: 'vertical' }}
          />
          <button
            onClick={() => saveMutation.mutate({ title: newTitle, query_text: newQuery })}
            disabled={!newTitle || !newQuery}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: 'none',
              background: '#2a9d8f',
              color: 'white',
              cursor: 'pointer'
            }}
          >
            Save Report
          </button>
        </div>
      )}

      {/* Reports List */}
      {isLoading ? (
        <p style={{ color: '#666' }}>Loading...</p>
      ) : reports.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#ccc', background: 'white', borderRadius: '12px' }}>
          <p>No saved reports yet. Create one from the Genie chat or manually.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '0.75rem' }}>
          {reports.map((r: any) => (
            <div key={r.report_id} style={{
              background: 'white',
              borderRadius: '10px',
              padding: '1rem 1.25rem',
              boxShadow: '0 1px 4px rgba(0,0,0,0.05)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{r.title}</div>
                <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '0.25rem' }}>
                  {r.query_text?.slice(0, 80)}{r.query_text?.length > 80 ? '...' : ''}
                </div>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#999', whiteSpace: 'nowrap' }}>
                {new Date(r.created_at).toLocaleDateString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
