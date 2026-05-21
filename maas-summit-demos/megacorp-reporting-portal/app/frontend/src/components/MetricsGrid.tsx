import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts';
import api from '../api';

const COLORS = ['#e63946', '#457b9d', '#2a9d8f', '#e9c46a', '#f4a261', '#264653'];

export default function MetricsGrid() {
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ['overview'],
    queryFn: api.getOverview,
  });

  const { data: deviceData, isLoading: loadingDevice } = useQuery({
    queryKey: ['reach-device'],
    queryFn: api.getReachByDevice,
  });

  const { data: regionData } = useQuery({
    queryKey: ['reach-region'],
    queryFn: () => api.getReachByRegion(),
  });

  if (loadingOverview) {
    return <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>Loading campaign data from Lakebase...</div>;
  }

  const campaigns = overview?.campaigns || [];
  const totalReach = campaigns.reduce((sum: number, c: any) => sum + (c.total_reach || 0), 0);
  const totalImpressions = campaigns.reduce((sum: number, c: any) => sum + (c.total_impressions || 0), 0);

  return (
    <div>
      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <KPICard label="Total Reach" value={totalReach.toLocaleString()} subtitle="Unique individuals" color="#e63946" />
        <KPICard label="Matched Impressions" value={totalImpressions.toLocaleString()} subtitle="Audience-matched" color="#457b9d" />
        <KPICard label="Active Campaigns" value={campaigns.length.toString()} subtitle="Running now" color="#2a9d8f" />
        <KPICard label="Publisher" value={overview?.publisher || '-'} subtitle="Your network" color="#264653" />
      </div>

      {/* Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Campaign Reach Bar Chart */}
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', color: '#333' }}>Reach by Campaign</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={campaigns.slice(0, 6)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="campaign" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="total_reach" fill="#e63946" radius={[4, 4, 0, 0]} name="Reach" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Device Breakdown Pie */}
        <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
          <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', color: '#333' }}>Reach by Device Type</h3>
          {!loadingDevice && deviceData?.data && (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={deviceData.data}
                  dataKey="reach"
                  nameKey="device_type"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {deviceData.data.map((_: any, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Region Table */}
      <div style={{ background: 'white', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '0.95rem', color: '#333' }}>Top Regions by Reach</h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #eee' }}>
              <th style={{ textAlign: 'left', padding: '0.5rem' }}>Region</th>
              <th style={{ textAlign: 'right', padding: '0.5rem' }}>Reach</th>
              <th style={{ textAlign: 'right', padding: '0.5rem' }}>Impressions</th>
            </tr>
          </thead>
          <tbody>
            {(regionData?.data || []).slice(0, 10).map((row: any, i: number) => (
              <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
                <td style={{ padding: '0.5rem' }}>{row.marketing_region}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem', fontWeight: 600 }}>{row.reach?.toLocaleString()}</td>
                <td style={{ textAlign: 'right', padding: '0.5rem', color: '#666' }}>{row.impressions?.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Data Source Badge */}
      <div style={{ marginTop: '1rem', textAlign: 'right', fontSize: '0.7rem', color: '#bbb' }}>
        Data source: media_advertising.gold.reach_cube → Lakebase synced table (sub-5s latency)
      </div>
    </div>
  );
}

function KPICard({ label, value, subtitle, color }: { label: string; value: string; subtitle: string; color: string }) {
  return (
    <div style={{
      background: 'white',
      borderRadius: '12px',
      padding: '1.25rem',
      boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
      borderLeft: `4px solid ${color}`
    }}>
      <div style={{ fontSize: '0.75rem', color: '#999', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
      <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1a1a2e', marginTop: '0.25rem' }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '0.25rem' }}>{subtitle}</div>
    </div>
  );
}
