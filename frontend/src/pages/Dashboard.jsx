import { useState, useEffect } from 'react';
import {
  TrendingUp, AlertTriangle, CheckCircle2,
  Clock, Flame, Zap, Plane, FileText, Database,
  Building2, BarChart3, Trophy, ShieldCheck
} from 'lucide-react';
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer,
  AreaChart, Area
} from 'recharts';
import api from '../api/client';

/* ── Scope palette matching Breathe Zero pastel tones ── */
const SCOPE_COLORS = { 1: '#6DD5A8', 2: '#F9A8B8', 3: '#FDBA74' };
const SCOPE_LABELS = { 1: 'Scope 1', 2: 'Scope 2', 3: 'Scope 3' };

const SOURCE_COLORS = { SAP_FUEL: '#6DD5A8', UTILITY_ELECTRICITY: '#F9A8B8', TRAVEL: '#FDBA74' };
const SOURCE_LABELS = {
  SAP_FUEL: 'SAP Fuel',
  UTILITY_ELECTRICITY: 'Utility Electricity',
  TRAVEL: 'Corporate Travel',
};

const CONFIDENCE_COLORS = { HIGH: '#6DD5A8', MEDIUM: '#FDBA74', LOW: '#FCA5A5' };

const formatCO2 = (kg) => {
  const n = parseFloat(kg);
  if (isNaN(n)) return '0 kg';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}t`;
  return `${Math.round(n)} kg`;
};

const formatMonth = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-GB', { month: 'short', year: '2-digit' });
};

const tooltipStyle = {
  background: '#FFFFFF',
  border: '1px solid #E2E8F0',
  borderRadius: '8px',
  color: '#1E293B',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.06)',
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getStats(), api.getJobs()])
      .then(([statsData, jobsData]) => {
        setStats(statsData);
        setJobs(jobsData.results || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="animate-slide-up">
        <div className="page-header">
          <div className="skeleton skeleton-title" />
          <div className="skeleton skeleton-text" style={{ width: '30%' }} />
        </div>
        <div className="stats-grid">
          {[1,2,3,4,5].map(i => <div key={i} className="skeleton skeleton-card" />)}
        </div>
        <div className="skeleton skeleton-chart" style={{ marginBottom: 'var(--sp-8)' }} />
        <div className="charts-grid">
          <div className="skeleton skeleton-chart" />
          <div className="skeleton skeleton-chart" />
        </div>
      </div>
    );
  }

  /* ── Prepare chart data ── */
  const scopeData = (stats?.scope_breakdown || []).map(s => ({
    name: `Scope ${s.ghg_scope}`,
    value: parseFloat(s.total_co2e) || 0,
    count: s.count,
    scope: s.ghg_scope,
  }));

  const sourceData = (stats?.source_breakdown || []).map(s => ({
    name: SOURCE_LABELS[s.source_type] || s.source_type,
    value: parseFloat(s.total_co2e) || 0,
    count: s.count,
    source: s.source_type,
  }));

  const confidenceData = (stats?.confidence_breakdown || []).map(c => ({
    name: c.confidence,
    value: c.count,
  }));

  // Monthly trend by scope → pivot into { month, scope1, scope2, scope3 }
  const monthlyByScope = {};
  (stats?.monthly_by_scope || []).forEach(entry => {
    const key = entry.month;
    if (!monthlyByScope[key]) {
      monthlyByScope[key] = { month: key, monthLabel: formatMonth(key), scope1: 0, scope2: 0, scope3: 0, total: 0 };
    }
    monthlyByScope[key][`scope${entry.ghg_scope}`] = entry.total_co2e;
    monthlyByScope[key].total += entry.total_co2e;
  });
  const monthlyTrendData = Object.values(monthlyByScope).sort(
    (a, b) => new Date(a.month) - new Date(b.month)
  );

  const facilityData = (stats?.facility_breakdown || []).map(f => ({
    name: f.facility_name.length > 22 ? f.facility_name.substring(0, 20) + '…' : f.facility_name,
    fullName: f.facility_name,
    value: f.total_co2e,
    count: f.count,
    country: f.country,
  }));

  const categoryData = (stats?.category_breakdown || []).map(c => ({
    name: c.ghg_category,
    value: c.total_co2e,
    count: c.count,
    scope: c.ghg_scope,
  }));

  const topRecords = stats?.top_records || [];

  return (
    <div className="animate-slide-up">
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Emissions overview across Scope 1, 2, and 3</p>
      </div>

      {/* ─── Scope KPI Cards (matching reference: large number + tCO2e) ─── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 'var(--sp-4)',
        marginBottom: 'var(--sp-8)',
      }}>
        {scopeData.map(s => (
          <div key={s.scope} className="card" style={{
            padding: 'var(--sp-5) var(--sp-6)',
            borderTop: `3px solid ${SCOPE_COLORS[s.scope]}`,
          }}>
            <div style={{
              fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-secondary)',
              textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--sp-2)',
            }}>
              SCOPE {s.scope}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-2)' }}>
              <span style={{
                fontSize: '2rem', fontWeight: 800, color: 'var(--text-primary)',
                letterSpacing: '-0.03em', lineHeight: 1,
              }}>
                {formatCO2(s.value).replace('t', '').replace(' kg', '')}
              </span>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', fontWeight: 500 }}>
                tCO2e
              </span>
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--sp-1)' }}>
              {s.count} records
            </div>
          </div>
        ))}

        {/* Total */}
        <div className="card" style={{
          padding: 'var(--sp-5) var(--sp-6)',
          borderTop: '3px solid var(--brand)',
          background: 'var(--brand-light)',
        }}>
          <div style={{
            fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--brand-text)',
            textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 'var(--sp-2)',
          }}>
            TOTAL CO₂e
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--sp-2)' }}>
            <span style={{
              fontSize: '2rem', fontWeight: 800, color: 'var(--brand-text)',
              letterSpacing: '-0.03em', lineHeight: 1,
            }}>
              {formatCO2(stats?.total_co2e_kg || 0).replace('t', '').replace(' kg', '')}
            </span>
            <span style={{ fontSize: 'var(--text-sm)', color: 'var(--brand-text)', fontWeight: 500, opacity: 0.7 }}>
              tCO2e
            </span>
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--brand-text)', marginTop: 'var(--sp-1)', opacity: 0.7 }}>
            {stats?.total_records || 0} records
          </div>
        </div>
      </div>

      {/* ─── Review Status Row ─── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 'var(--sp-3)',
        marginBottom: 'var(--sp-8)',
      }}>
        {[
          { label: 'Pending', value: stats?.pending, bg: 'var(--warning-bg)', color: 'var(--warning-text)', icon: Clock },
          { label: 'Approved', value: stats?.approved, bg: 'var(--success-bg)', color: 'var(--success-text)', icon: CheckCircle2 },
          { label: 'Flagged', value: stats?.flagged, bg: 'var(--danger-bg)', color: 'var(--danger-text)', icon: AlertTriangle },
        ].map(({ label, value, bg, color, icon: Icon }) => (
          <div key={label} style={{
            display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
            padding: 'var(--sp-4)', background: bg,
            borderRadius: 'var(--r-xl)',
          }}>
            <Icon size={18} color={color} />
            <div>
              <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color }}>{value || 0}</div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* ─── Monthly Trend (hero chart — stacked bar like reference) ─── */}
      <div className="card chart-card" style={{ marginBottom: 'var(--sp-8)' }}>
        <h3>
          <TrendingUp size={16} color="var(--brand)" />
          Emissions by Scope (TCO₂e)
        </h3>
        {monthlyTrendData.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyTrendData} barCategoryGap="20%">
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis
                  dataKey="monthLabel"
                  tick={{ fill: '#64748B', fontSize: 12 }}
                  axisLine={{ stroke: '#E2E8F0' }}
                  tickLine={false}
                />
                <YAxis
                  tick={{ fill: '#64748B', fontSize: 12 }}
                  axisLine={{ stroke: '#E2E8F0' }}
                  tickLine={false}
                  tickFormatter={v => formatCO2(v)}
                />
                <Tooltip
                  formatter={(value, name) => [formatCO2(value), SCOPE_LABELS[name.replace('scope', '')] || name]}
                  contentStyle={tooltipStyle}
                  cursor={false}
                />
                <Bar dataKey="scope1" name="scope1" stackId="a" fill="#6DD5A8" radius={[0,0,0,0]} />
                <Bar dataKey="scope2" name="scope2" stackId="a" fill="#F9A8B8" radius={[0,0,0,0]} />
                <Bar dataKey="scope3" name="scope3" stackId="a" fill="#FDBA74" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
            {/* Legend */}
            <div style={{
              display: 'flex', gap: 'var(--sp-6)', justifyContent: 'center',
              marginTop: 'var(--sp-4)',
            }}>
              {[1, 2, 3].map(s => (
                <div key={s} style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  fontSize: 'var(--text-xs)', color: 'var(--text-secondary)',
                }}>
                  <span style={{
                    width: 12, height: 12, borderRadius: 'var(--r-sm)',
                    background: SCOPE_COLORS[s], display: 'inline-block',
                  }} />
                  {SCOPE_LABELS[s]}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="empty-state"><p>No data yet. Upload emissions data to see trends.</p></div>
        )}
      </div>

      {/* ─── Row: Scope Donut + Source Bar ─── */}
      <div className="charts-grid">
        <div className="card chart-card">
          <h3>Emissions by GHG Scope</h3>
          {scopeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={scopeData}
                  cx="50%" cy="50%"
                  innerRadius={55} outerRadius={95}
                  paddingAngle={3}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${formatCO2(value)}`}
                >
                  {scopeData.map(entry => (
                    <Cell key={entry.name} fill={SCOPE_COLORS[entry.scope]} stroke="#fff" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip formatter={v => formatCO2(v)} contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No data yet.</p></div>
          )}
        </div>

        <div className="card chart-card">
          <h3>Emissions by Source</h3>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sourceData} barSize={36}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
                <YAxis tick={{ fill: '#64748B', fontSize: 12 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} tickFormatter={v => formatCO2(v)} />
                <Tooltip formatter={v => [formatCO2(v), 'CO₂e']} contentStyle={tooltipStyle} cursor={false} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {sourceData.map(entry => (
                    <Cell key={entry.name} fill={SOURCE_COLORS[entry.source] || '#94A3B8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No data yet.</p></div>
          )}
        </div>
      </div>

      {/* ─── Row: Facility + Category ─── */}
      <div className="charts-grid">
        <div className="card chart-card">
          <h3>
            <Building2 size={16} color="var(--info)" />
            Emissions by Facility
          </h3>
          {facilityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={facilityData} layout="vertical" barSize={14} margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} tickFormatter={v => formatCO2(v)} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#64748B', fontSize: 11 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} width={130} />
                <Tooltip formatter={(v, n, p) => [formatCO2(v), `${p.payload.fullName} (${p.payload.country})`]} contentStyle={tooltipStyle} cursor={false} />
                <Bar dataKey="value" radius={[0, 4, 4, 0]} fill="#6DD5A8" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No facility data.</p></div>
          )}
        </div>

        <div className="card chart-card">
          <h3>
            <BarChart3 size={16} color="var(--warning)" />
            Emissions by Category
          </h3>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={categoryData} barSize={22}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" vertical={false} />
                <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 10 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} angle={-30} textAnchor="end" height={70} />
                <YAxis tick={{ fill: '#64748B', fontSize: 11 }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} tickFormatter={v => formatCO2(v)} />
                <Tooltip formatter={(v, n, p) => [formatCO2(v), `${SCOPE_LABELS[p.payload.scope]} · ${p.payload.count} records`]} contentStyle={tooltipStyle} cursor={false} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {categoryData.map((entry, i) => (
                    <Cell key={i} fill={SCOPE_COLORS[entry.scope] || '#94A3B8'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state"><p>No data.</p></div>
          )}
        </div>
      </div>

      {/* ─── Row: Data Quality + Top Emitters ─── */}
      <div className="charts-grid">
        <div className="card chart-card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3>
            <ShieldCheck size={16} color="var(--success)" />
            Data Quality
          </h3>
          {confidenceData.length > 0 ? (
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={confidenceData}
                    cx="50%" cy="50%"
                    innerRadius={55} outerRadius={95}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {confidenceData.map(entry => (
                      <Cell key={entry.name} fill={CONFIDENCE_COLORS[entry.name] || '#94A3B8'} stroke="#fff" strokeWidth={2} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: 'var(--sp-4)', justifyContent: 'center', marginTop: 'var(--sp-2)', width: '100%' }}>
                {confidenceData.map(c => (
                  <div key={c.name} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: 'var(--text-xs)' }}>
                    <span style={{ width: 8, height: 8, borderRadius: '50%', background: CONFIDENCE_COLORS[c.name], display: 'inline-block' }} />
                    <span style={{ color: 'var(--text-secondary)' }}>{c.name}: {c.value}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p>No data.</p></div>
          )}
        </div>

        <div className="card chart-card">
          <h3>
            <Trophy size={16} color="var(--warning)" />
            Top 5 Emitting Records
          </h3>
          {topRecords.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {topRecords.map((record, idx) => {
                const maxCO2 = topRecords[0]?.co2e_kg || 1;
                const pct = (record.co2e_kg / maxCO2) * 100;
                return (
                  <div key={record.id} style={{
                    display: 'flex', alignItems: 'center', gap: 'var(--sp-3)',
                    padding: 'var(--sp-3)', borderRadius: 'var(--r-lg)',
                    background: 'var(--bg-body)',
                  }}>
                    <span style={{
                      fontWeight: 800, fontSize: 'var(--text-md)',
                      color: idx === 0 ? 'var(--warning)' : 'var(--text-muted)',
                      width: '20px', textAlign: 'center', flexShrink: 0,
                    }}>
                      {idx + 1}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{
                        fontSize: 'var(--text-sm)', fontWeight: 500,
                        whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        color: 'var(--text-primary)',
                      }}>
                        {record.activity_description}
                      </div>
                      <div style={{ display: 'flex', gap: '5px', alignItems: 'center', marginTop: '2px' }}>
                        <span className={`badge badge-scope${record.ghg_scope}`} style={{ fontSize: '9px' }}>
                          Scope {record.ghg_scope}
                        </span>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                          {record.facility_name || SOURCE_LABELS[record.source_type] || ''}
                        </span>
                      </div>
                      <div style={{ marginTop: '4px', height: '3px', background: 'var(--border-light)', borderRadius: '2px' }}>
                        <div style={{
                          width: `${pct}%`, height: '100%', borderRadius: '2px',
                          background: SCOPE_COLORS[record.ghg_scope] || 'var(--brand)',
                          transition: 'width 0.5s ease',
                        }} />
                      </div>
                    </div>
                    <div style={{
                      fontWeight: 700, fontSize: 'var(--text-sm)',
                      color: 'var(--text-primary)', whiteSpace: 'nowrap', flexShrink: 0,
                    }}>
                      {formatCO2(record.co2e_kg)}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state"><p>No records yet.</p></div>
          )}
        </div>
      </div>

      {/* ─── Recent Ingestion Jobs ─── */}
      <div className="card" style={{ marginTop: 'var(--sp-4)' }}>
        <h3 style={{ marginBottom: 'var(--sp-5)', fontSize: 'var(--text-md)', fontWeight: 600 }}>
          Recent Ingestion Jobs
        </h3>
        {jobs.length > 0 ? (
          <div className="jobs-list">
            {jobs.slice(0, 5).map(job => {
              const iconClass = job.source_type === 'SAP_FUEL' ? 'sap'
                : job.source_type === 'UTILITY_ELECTRICITY' ? 'utility' : 'travel';
              const Icon = job.source_type === 'SAP_FUEL' ? Flame
                : job.source_type === 'UTILITY_ELECTRICITY' ? Zap : Plane;
              return (
                <div className="job-item" key={job.id}>
                  <div className="job-info">
                    <div className={`job-icon ${iconClass}`}><Icon size={16} /></div>
                    <div className="job-details">
                      <h4>{job.file_name}</h4>
                      <div className="job-meta">
                        {job.source_type_display} · {new Date(job.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="job-stats">
                    <div className="job-stat">
                      <div className="job-stat-value" style={{ color: 'var(--success)' }}>{job.success_rows}</div>
                      <div className="job-stat-label">Success</div>
                    </div>
                    <div className="job-stat">
                      <div className="job-stat-value" style={{ color: 'var(--danger)' }}>{job.error_rows}</div>
                      <div className="job-stat-label">Errors</div>
                    </div>
                    <span className={`badge badge-${job.status.toLowerCase()}`}>{job.status}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon"><FileText size={24} color="var(--text-muted)" /></div>
            <h3>No ingestion jobs yet</h3>
            <p>Upload your first data file to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
