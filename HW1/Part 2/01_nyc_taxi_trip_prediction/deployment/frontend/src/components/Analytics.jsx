import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

export default function Analytics() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/metrics');
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to fetch metrics", err);
      }
    };
    fetchMetrics();
  }, []);

  if (!data) return <div style={{ textAlign: 'center', marginTop: '2rem' }}>Loading analytics...</div>;

  return (
    <div className="analytics-container" style={{ background: 'var(--bg-main)', border: '1px solid var(--border-light)', boxShadow: 'var(--shadow-sm)' }}>
      
      <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: '2rem' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>RMSE (seconds)</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>{data.metrics.rmse_sec}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>MAE (seconds)</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>{data.metrics.mae_sec}</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>R-Squared</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--primary)' }}>{data.metrics.r_squared}</div>
        </div>
      </div>

      <div style={{ height: 250, width: '100%' }}>
        <ResponsiveContainer>
          <BarChart data={data.feature_importance} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-light)" />
            <XAxis type="number" stroke="var(--text-muted)" />
            <YAxis dataKey="feature" type="category" width={120} stroke="var(--text-muted)" fontSize={11} />
            <Tooltip 
              contentStyle={{ backgroundColor: 'var(--bg-panel)', borderColor: 'var(--border-light)', borderRadius: '8px', color: 'var(--text-main)' }} 
              itemStyle={{ color: 'var(--primary)' }} 
            />
            <Bar dataKey="importance" fill="var(--primary)" radius={[0, 4, 4, 0]}>
              {
                data.feature_importance.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={index === 0 ? 'var(--primary)' : 'var(--primary-hover)'} />
                ))
              }
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
