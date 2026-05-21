import { useState } from 'react';
import api from '../api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  status?: string;
  data?: any;
}

export default function GenieChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const SUGGESTIONS = [
    "What is my total reach across all campaigns?",
    "Which campaign has the highest CTV reach?",
    "Show me reach by marketing region for the top 5 regions",
    "Compare mobile vs web impressions across campaigns",
    "Which content has the best match rate?",
  ];

  const handleAsk = async (question?: string) => {
    const q = question || input;
    if (!q.trim()) return;

    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setInput('');
    setLoading(true);

    try {
      const result = await api.askGenie(q);
      
      if (result.status === 'error') {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `I couldn't process that question directly. ${result.fallback || result.message}`,
          status: 'error'
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: `Query submitted to Genie (conversation: ${result.conversation_id}). Scoped to your publisher data.`,
          status: 'processing',
          data: result
        }]);

        // Poll for results (simplified)
        if (result.conversation_id && result.message_id) {
          setTimeout(async () => {
            try {
              const pollResult = await api.getGenieResult(result.conversation_id, result.message_id);
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: `Results ready: ${JSON.stringify(pollResult.result || pollResult, null, 2).slice(0, 500)}`,
                status: pollResult.status
              }]);
            } catch (e) {
              // Polling may not complete in demo
            }
          }, 3000);
        }
      }
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${e.message}`,
        status: 'error'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.1rem', color: '#1a1a2e' }}>Ask Genie About Your Campaigns</h2>
        <p style={{ color: '#666', fontSize: '0.85rem', marginTop: '0.25rem' }}>
          Natural language queries against your isolated data slice. Powered by the campaign_reach_metrics Metric View + UC governance.
        </p>
      </div>

      {/* Suggestion Chips */}
      {messages.length === 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <p style={{ fontSize: '0.8rem', color: '#999', marginBottom: '0.5rem' }}>Try asking:</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => handleAsk(s)}
                style={{
                  padding: '0.5rem 0.75rem',
                  borderRadius: '20px',
                  border: '1px solid #e0e0e0',
                  background: 'white',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  color: '#457b9d',
                  transition: 'all 0.2s'
                }}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '1.5rem',
        minHeight: '300px',
        maxHeight: '500px',
        overflowY: 'auto',
        boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
        marginBottom: '1rem'
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '3rem', color: '#ccc' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</div>
            <p>Ask a question about your campaign performance</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: '1rem',
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start'
          }}>
            <div style={{
              maxWidth: '80%',
              padding: '0.75rem 1rem',
              borderRadius: '12px',
              background: msg.role === 'user' ? '#e63946' : '#f5f5f5',
              color: msg.role === 'user' ? 'white' : '#333',
              fontSize: '0.9rem'
            }}>
              {msg.content}
              {msg.status && msg.status !== 'error' && (
                <div style={{ fontSize: '0.7rem', marginTop: '0.25rem', opacity: 0.7 }}>
                  Status: {msg.status}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: '#666', fontStyle: 'italic', fontSize: '0.85rem' }}>
            Querying Genie...
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAsk()}
          placeholder="Ask about your campaign reach, impressions, devices..."
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            border: '2px solid #e0e0e0',
            fontSize: '0.9rem',
            outline: 'none'
          }}
        />
        <button
          onClick={() => handleAsk()}
          disabled={loading || !input.trim()}
          style={{
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            background: '#e63946',
            color: 'white',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          Ask
        </button>
      </div>

      {/* Architecture Note */}
      <div style={{
        marginTop: '1rem',
        padding: '0.75rem',
        background: '#f0f8ff',
        borderRadius: '8px',
        fontSize: '0.75rem',
        color: '#457b9d'
      }}>
        <strong>Architecture:</strong> Genie queries the UC-governed campaign_reach_metrics Metric View.
        Your question is scoped to your publisher via UC row-level security. Results are tenant-isolated at the data layer.
      </div>
    </div>
  );
}
