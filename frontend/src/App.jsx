// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, AlertTriangle, CheckCircle, Lock, RefreshCw, Eye, ShieldAlert } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api';

export default function App() {
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [activeTab, setActiveTab] = useState('ALL');
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [overrideCarbon, setOverrideCarbon] = useState('');
  const [correctionReason, setCorrectionReason] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const recordsRes = await axios.get(`${API_BASE}/records/`);
      const batchesRes = await axios.get(`${API_BASE}/batches/`);
      setRecords(recordsRes.data);
      setBatches(batchesRes.data);
    } catch (err) {
      console.error("Data synchronization error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (e, type) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    setLoading(true);
    try {
      const url = type === 'SAP' ? `${API_BASE}/records/ingest-sap/` : `${API_BASE}/records/ingest-utility/`;
      await axios.post(url, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      fetchDashboardData();
    } catch (err) {
      alert("Ingestion pipeline failure. Check format structure.");
    } finally {
      setLoading(false);
    }
  };

  const triggerConcurSync = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/records/sync-concur/`);
      fetchDashboardData();
    } catch (err) {
      alert("API wire sync timeout.");
    } finally {
      setLoading(false);
    }
  };

  const executeStateTransition = async (id, targetStatus) => {
    try {
      const payload = { status: targetStatus };
      if (targetStatus === 'APPROVED' && overrideCarbon) {
        payload.co2e_kg = parseFloat(overrideCarbon);
        payload.reason = correctionReason || "Manual adjustment before locking";
      }
      await axios.post(`${API_BASE}/records/${id}/update-status/`, payload);
      setSelectedRecord(null);
      setOverrideCarbon('');
      setCorrectionReason('');
      fetchDashboardData();
    } catch (err) {
      alert(err.response?.data?.error || "State transition denied.");
    }
  };

  const filteredRecords = records.filter(rec => activeTab === 'ALL' || rec.status === activeTab);

  return (
    <div style={{ padding: '24px', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Header Block */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '32px', borderBottom: '1px solid #e2e8f0', paddingBottom: '16px' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '28px', fontWeight: '700', color: '#1e293b' }}>Breathe ESG Operational Console</h1>
          <p style={{ margin: '4px 0 0 0', color: '#64748b' }}>Enterprise Environmental Ledger Multi-Tenant Ingestion System</p>
        </div>
        <button onClick={fetchDashboardData} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', background: '#fff', border: '1px solid #cbd5e1', borderRadius: '6px', cursor: 'pointer', fontWeight: '500' }}>
          <RefreshCw size={16} className={loading ? "spin-animation" : ""} /> Sync View
        </button>
      </header>

      {/* Ingestion Pipeline Grid Controls */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>1. SAP Gateway (Scope 1/3)</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', background: '#f1f5f9', border: '2px dashed #cbd5e1', borderRadius: '6px', cursor: 'pointer', justifyContent: 'center' }}>
            <Upload size={18} /> Ingest SAP CSV Dump
            <input type="file" accept=".csv" onChange={(e) => handleFileUpload(e, 'SAP')} style={{ display: 'none' }} />
          </label>
        </div>

        <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>2. Utility Intake (Scope 2)</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', background: '#f1f5f9', border: '2px dashed #cbd5e1', borderRadius: '6px', cursor: 'pointer', justifyContent: 'center' }}>
            <Upload size={18} /> Load Portal Export
            <input type="file" accept=".csv" onChange={(e) => handleFileUpload(e, 'UTILITY')} style={{ display: 'none' }} />
          </label>
        </div>

        <div style={{ background: '#fff', padding: '20px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>3. Concur API Wire (Scope 3)</h3>
          <button onClick={triggerConcurSync} style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '8px', padding: '14px', background: '#0f172a', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', justifyContent: 'center', fontWeight: '500' }}>
            Sync Concur Endpoints
          </button>
        </div>
      </section>

      {/* Primary Dashboard Workspace Layout */}
      <main style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
        {/* Main Records Ledger Panel */}
        <div style={{ flex: 1, background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0', padding: '20px' }}>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', borderBottom: '2px solid #f1f5f9', paddingBottom: '12px' }}>
            {['ALL', 'PENDING', 'SUSPICIOUS', 'APPROVED'].map(tab => (
              <button key={tab} onClick={() => setActiveTab(tab)} style={{ padding: '8px 16px', background: activeTab === tab ? '#e2e8f0' : 'none', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: '600', color: activeTab === tab ? '#0f172a' : '#64748b' }}>
                {tab} ({tab === 'ALL' ? records.length : records.filter(r => r.status === tab).length})
              </button>
            ))}
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #f1f5f9', color: '#64748b', fontSize: '13px' }}>
                  <th style={{ padding: '12px' }}>Origin Stream</th>
                  <th style={{ padding: '12px' }}>GHG Scope</th>
                  <th style={{ padding: '12px' }}>Target Category</th>
                  <th style={{ padding: '12px' }}>Metrics Received</th>
                  <th style={{ padding: '12px' }}>Calculated CO₂e</th>
                  <th style={{ padding: '12px' }}>System State</th>
                  <th style={{ padding: '12px' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords.map(rec => (
                  <tr key={rec.id} style={{ borderBottom: '1px solid #f1f5f9', background: rec.status === 'SUSPICIOUS' ? '#fffbeb' : 'inherit', fontSize: '14px' }}>
                    <td style={{ padding: '12px', fontWeight: '500' }}>{rec.batch_detail?.source_type}</td>
                    <td style={{ padding: '12px' }}><span style={{ padding: '2px 8px', borderRadius: '12px', background: '#f1f5f9', fontSize: '12px', fontWeight: '700' }}>S{rec.scope}</span></td>
                    <td style={{ padding: '12px', color: '#334155' }}>{rec.category}</td>
                    <td style={{ padding: '12px' }}>{rec.original_value} <span style={{ fontSize: '12px', color: '#64748b' }}>{rec.original_unit}</span></td>
                    <td style={{ padding: '12px', fontWeight: '600' }}>{rec.co2e_kg ? `${rec.co2e_kg} kg` : 'Unassigned'}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: '600', color: rec.status === 'APPROVED' ? '#16a34a' : rec.status === 'SUSPICIOUS' ? '#d97706' : '#2563eb' }}>
                        {rec.status === 'APPROVED' ? <Lock size={12} /> : rec.status === 'SUSPICIOUS' ? <AlertTriangle size={12} /> : null}
                        {rec.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>
                      <button onClick={() => { setSelectedRecord(rec); setOverrideCarbon(rec.co2e_kg || ''); }} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', padding: '6px 12px', background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}>
                        <Eye size={14} /> Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Side Audit Drawer Panel */}
        {selectedRecord && (
          <aside style={{ width: '450px', background: '#fff', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '24px', position: 'sticky', top: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '18px', margin: 0 }}>Inspection Engine</h2>
              <button onClick={() => setSelectedRecord(null)} style={{ border: 'none', background: 'none', fontSize: '20px', cursor: 'pointer', color: '#64748b' }}>&times;</button>
            </div>

            {/* Suspicious Anomalies Banner */}
            {selectedRecord.validation_flags.length > 0 && (
              <div style={{ background: '#fef3c7', border: '1px solid #f59e0b', padding: '12px', borderRadius: '6px', marginBottom: '20px', color: '#b45309', fontSize: '13px' }}>
                <div style={{ fontWeight: '700', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}><ShieldAlert size={16}/> Pipeline Anomalies Identified:</div>
                <ul style={{ margin: 0, paddingLeft: '20px' }}>
                  {selectedRecord.validation_flags.map((flag, k) => <li key={k}><code>{flag}</code></li>)}
                </ul>
              </div>
            )}

            {/* Micro Metadata Metrics Readout */}
            <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '6px', marginBottom: '20px', fontSize: '13px' }}>
              <div style={{ marginBottom: '6px' }}><strong>System Tracker ID:</strong> <span style={{ fontFamily: 'monospace' }}>{selectedRecord.id}</span></div>
              <div style={{ marginBottom: '6px' }}><strong>Batch Line Context:</strong> Row index position #{selectedRecord.source_row_index}</div>
              <div><strong>Lineage Payload Blueprint:</strong></div>
              <pre style={{ margin: '8px 0 0 0', background: '#0f172a', color: '#38bdf8', padding: '12px', borderRadius: '4px', overflowX: 'auto', fontSize: '11px' }}>
                {JSON.stringify(selectedRecord.raw_data_payload, null, 2)}
              </pre>
            </div>

            {/* Modification and Sign-off Actions Block */}
            {!selectedRecord.is_locked ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <label style={{ fontSize: '13px', fontWeight: '600' }}>
                  Override Calculated Impact Value (CO₂e kg):
                  <input type="number" value={overrideCarbon} onChange={(e) => setOverrideCarbon(e.target.value)} style={{ width: '100%', marginTop: '4px', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px' }} />
                </label>
                
                <label style={{ fontSize: '13px', fontWeight: '600' }}>
                  Audit Correction Justification:
                  <textarea value={correctionReason} onChange={(e) => setCorrectionReason(e.target.value)} placeholder="Provide compliance context rationale..." style={{ width: '100%', marginTop: '4px', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '4px', minHeight: '60px' }} />
                </label>

                <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                  <button onClick={() => executeStateTransition(selectedRecord.id, 'APPROVED')} style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', padding: '12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}>
                    <CheckCircle size={16} /> Approve & Lock row
                  </button>
                  {selectedRecord.status !== 'SUSPICIOUS' && (
                    <button onClick={() => executeStateTransition(selectedRecord.id, 'SUSPICIOUS')} style={{ padding: '12px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: '600' }}>
                      Flag
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '16px', border: '2px solid #16a34a', background: '#f0fdf4', color: '#16a34a', borderRadius: '6px', fontWeight: '600' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', marginBottom: '4px' }}><Lock size={18} /> Row Vault Locked for Audits</div>
                <div style={{ fontSize: '12px', color: '#15803d' }}>This data transaction line item has been verified and signed off.</div>
              </div>
            )}

            {/* Historical Footprints Log Trail */}
            {selectedRecord.audit_trail?.length > 0 && (
              <div style={{ marginTop: '24px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '14px' }}>Immutable Verification Trail</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '180px', overflowY: 'auto' }}>
                  {selectedRecord.audit_trail.map((log) => (
                    <div key={log.id} style={{ fontSize: '12px', background: '#f8fafc', padding: '8px', borderLeft: '3px solid #64748b' }}>
                      <div style={{ color: '#64748b' }}><strong>{log.changed_field}</strong> updated from <code>{log.old_value || 'None'}</code> &rarr; <code>{log.new_value}</code></div>
                      <div style={{ fontStyle: 'italic', color: '#475569', marginTop: '2px' }}>"{log.reason}"</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </aside>
        )}
      </main>

      {/* Embedded CSS Micro-Animations */}
      <style>{`
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .spin-animation { animation: spin 1s linear infinite; }
      `}</style>
    </div>
  );
}