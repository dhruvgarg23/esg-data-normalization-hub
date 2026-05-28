import { useState, useEffect, useCallback, Fragment } from 'react';
import {
  CheckCircle, XCircle, Flag, Lock, ChevronDown, ChevronRight,
  Search, CheckSquare, X, SlidersHorizontal
} from 'lucide-react';
import api from '../api/client';

const SCOPE_LABELS = { 1: 'Scope 1', 2: 'Scope 2', 3: 'Scope 3' };

const formatCO2 = (kg) => {
  const n = parseFloat(kg);
  if (isNaN(n)) return '—';
  if (n >= 1000) return `${(n / 1000).toFixed(2)} t`;
  return `${n.toFixed(2)} kg`;
};

const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

const STATUS_META = {
  PENDING:  { label: 'Pending',  cls: 'badge-pending' },
  APPROVED: { label: 'Approved', cls: 'badge-approved' },
  FLAGGED:  { label: 'Flagged',  cls: 'badge-flagged' },
  REJECTED: { label: 'Rejected', cls: 'badge-rejected' },
};

const CONFIDENCE_META = {
  HIGH:   { cls: 'badge-high' },
  MEDIUM: { cls: 'badge-medium' },
  LOW:    { cls: 'badge-low' },
};

/* ── Inline action button ── */
function ActionBtn({ icon: Icon, label, onClick, variant = 'ghost', disabled }) {
  const colors = {
    approve: { color: '#15803D', bg: '#F0FDF4', hoverBg: '#DCFCE7' },
    flag:    { color: '#92400E', bg: '#FFFBEB', hoverBg: '#FEF3C7' },
    reject:  { color: '#991B1B', bg: '#FEF2F2', hoverBg: '#FEE2E2' },
  };
  const c = colors[variant] || {};
  return (
    <button
      title={label}
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        width: '28px', height: '28px', borderRadius: '6px',
        border: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
        background: c.bg || 'var(--bg-body)',
        color: c.color || 'var(--text-secondary)',
        transition: 'background 120ms ease',
        opacity: disabled ? 0.4 : 1,
      }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.background = c.hoverBg || 'var(--bg-hover)'; }}
      onMouseLeave={e => { e.currentTarget.style.background = c.bg || 'var(--bg-body)'; }}
    >
      <Icon size={13} />
    </button>
  );
}

/* ── Source pill ── */
const SOURCE_PILLS = {
  SAP_FUEL: { label: 'SAP Fuel', bg: '#EFF6FF', color: '#1E40AF' },
  UTILITY_ELECTRICITY: { label: 'Utility', bg: '#FFFBEB', color: '#92400E' },
  TRAVEL: { label: 'Travel', bg: '#FFF7ED', color: '#9A3412' },
};

export default function Review() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    source_type: '', ghg_scope: '', review_status: '', confidence: '',
  });
  const [selected, setSelected] = useState(new Set());
  const [expandedRow, setExpandedRow] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reviewModal, setReviewModal] = useState(null);
  const [reviewNotes, setReviewNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchRecords = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getEmissions(filters);
      setRecords(data.results || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { fetchRecords(); }, [fetchRecords]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const handleExpand = async (record) => {
    if (expandedRow === record.id) {
      setExpandedRow(null);
      setDetailData(null);
      return;
    }
    setExpandedRow(record.id);
    setDetailData(null);
    setDetailLoading(true);
    try {
      const detail = await api.getEmissionDetail(record.id);
      setDetailData(detail);
    } catch (err) {
      console.error(err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleReview = async (recordId, action) => {
    if ((action === 'REJECT' || action === 'FLAG') && !reviewNotes.trim()) {
      showToast('Notes are required when rejecting or flagging', 'error');
      return;
    }
    setActionLoading(true);
    try {
      await api.reviewRecord(recordId, action, reviewNotes);
      showToast(`Record ${action.charAt(0) + action.slice(1).toLowerCase()}d`);
      setReviewModal(null);
      setReviewNotes('');
      setExpandedRow(null);
      fetchRecords();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleBulkApprove = async () => {
    if (selected.size === 0) return;
    setActionLoading(true);
    try {
      const data = await api.bulkApprove([...selected]);
      showToast(`${data.approved} record${data.approved !== 1 ? 's' : ''} approved`);
      setSelected(new Set());
      fetchRecords();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const unlocked = records.filter(r => !r.is_locked);
  const toggleSelectAll = () => {
    if (selected.size === unlocked.length && unlocked.length > 0) {
      setSelected(new Set());
    } else {
      setSelected(new Set(unlocked.map(r => r.id)));
    }
  };

  const pendingCount = records.filter(r => r.review_status === 'PENDING').length;

  return (
    <div className="animate-slide-up">
      {/* Page header */}
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-4)' }}>
          <div>
            <h2>Review & Approve</h2>
            <p>Review emission records, flag anomalies, and sign off for audit</p>
          </div>
          {selected.size > 0 && (
            <button
              className="btn btn-primary"
              onClick={handleBulkApprove}
              disabled={actionLoading}
              style={{ alignSelf: 'flex-start' }}
            >
              <CheckSquare size={15} />
              Approve {selected.size} selected
            </button>
          )}
        </div>
      </div>

      {/* Filter bar */}
      <div style={{
        display: 'flex', gap: 'var(--sp-3)', flexWrap: 'wrap',
        alignItems: 'center', marginBottom: 'var(--sp-5)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', color: 'var(--text-muted)' }}>
          <SlidersHorizontal size={15} />
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-secondary)' }}>Filter by</span>
        </div>

        {[
          {
            key: 'source_type', placeholder: 'All Sources',
            options: [
              { value: 'SAP_FUEL', label: 'SAP Fuel' },
              { value: 'UTILITY_ELECTRICITY', label: 'Utility' },
              { value: 'TRAVEL', label: 'Travel' },
            ],
          },
          {
            key: 'ghg_scope', placeholder: 'All Scopes',
            options: [
              { value: '1', label: 'Scope 1' },
              { value: '2', label: 'Scope 2' },
              { value: '3', label: 'Scope 3' },
            ],
          },
          {
            key: 'review_status', placeholder: 'All Statuses',
            options: [
              { value: 'PENDING', label: 'Pending' },
              { value: 'FLAGGED', label: 'Flagged' },
              { value: 'APPROVED', label: 'Approved' },
              { value: 'REJECTED', label: 'Rejected' },
            ],
          },
          {
            key: 'confidence', placeholder: 'All Confidence',
            options: [
              { value: 'HIGH', label: 'High' },
              { value: 'MEDIUM', label: 'Medium' },
              { value: 'LOW', label: 'Low' },
            ],
          },
        ].map(({ key, placeholder, options }) => (
          <select
            key={key}
            className="form-select"
            value={filters[key]}
            onChange={e => setFilters(f => ({ ...f, [key]: e.target.value }))}
            style={{ width: 'auto', minWidth: '130px' }}
          >
            <option value="">{placeholder}</option>
            {options.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        ))}

        {/* Active filters badge */}
        {Object.values(filters).some(Boolean) && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => setFilters({ source_type: '', ghg_scope: '', review_status: '', confidence: '' })}
          >
            <X size={12} />
            Clear filters
          </button>
        )}
      </div>

      {/* Summary strip */}
      {!loading && records.length > 0 && (
        <div style={{
          display: 'flex', gap: 'var(--sp-2)', alignItems: 'center',
          marginBottom: 'var(--sp-4)',
          fontSize: 'var(--text-xs)', color: 'var(--text-muted)',
        }}>
          <span>{records.length} records</span>
          {pendingCount > 0 && (
            <>
              <span>·</span>
              <span style={{ color: '#92400E', fontWeight: 600 }}>
                {pendingCount} pending review
              </span>
            </>
          )}
        </div>
      )}

      {/* Table or empty/loading state */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="skeleton" style={{ height: '52px', borderRadius: 'var(--r-lg)' }} />
          ))}
        </div>
      ) : records.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state-icon">
            <Search size={22} color="var(--text-muted)" />
          </div>
          <h3>No records found</h3>
          <p>Try adjusting your filters, or upload new data to get started.</p>
        </div>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th className="checkbox-cell">
                  <input
                    type="checkbox"
                    aria-label="Select all"
                    checked={unlocked.length > 0 && selected.size === unlocked.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th style={{ width: '32px' }} />
                <th>Source & Scope</th>
                <th>Description</th>
                <th>CO₂e</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(record => {
                const sourcePill = SOURCE_PILLS[record.source_type] || { label: record.source_type, bg: 'var(--bg-body)', color: 'var(--text-secondary)' };
                const isExpanded = expandedRow === record.id;
 
                return (
                  <Fragment key={record.id}>
                    <tr className={record.is_locked ? 'locked' : ''}>
                      {/* Checkbox */}
                      <td className="checkbox-cell">
                        {!record.is_locked ? (
                          <input
                            type="checkbox"
                            aria-label={`Select ${record.activity_description}`}
                            checked={selected.has(record.id)}
                            onChange={() => toggleSelect(record.id)}
                          />
                        ) : (
                          <Lock size={12} color="var(--text-muted)" />
                        )}
                      </td>
 
                      {/* Expand toggle */}
                      <td>
                        <button
                          aria-label={isExpanded ? 'Collapse row' : 'Expand row'}
                          onClick={() => handleExpand(record)}
                          style={{
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-muted)', padding: '2px',
                            borderRadius: 'var(--r-sm)', display: 'flex',
                          }}
                        >
                          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                      </td>
 
                      {/* Source & Scope */}
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                          <span style={{
                            display: 'inline-flex', alignItems: 'center',
                            padding: '2px 8px', borderRadius: '999px',
                            fontSize: '10px', fontWeight: 600,
                            background: sourcePill.bg, color: sourcePill.color,
                          }}>
                            {sourcePill.label}
                          </span>
                          <span className={`badge badge-scope${record.ghg_scope}`} style={{ fontSize: '9px', padding: '1px 6px' }}>
                            {SCOPE_LABELS[record.ghg_scope]}
                          </span>
                        </div>
                      </td>
 
                      {/* Description, Activity, and Period combined */}
                      <td style={{ maxWidth: '320px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span title={record.activity_description} style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 'var(--text-sm)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {record.activity_description}
                          </span>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                            <span style={{ fontWeight: 500 }}>
                              {parseFloat(record.activity_quantity).toLocaleString()} {record.activity_unit}
                            </span>
                            <span style={{ color: 'var(--text-muted)' }}>·</span>
                            <span>
                              {formatDate(record.reporting_period_start)}
                              {record.reporting_period_end && ` – ${formatDate(record.reporting_period_end)}`}
                            </span>
                          </div>
                        </div>
                      </td>
 
                      {/* CO2e */}
                      <td style={{ fontWeight: 700, whiteSpace: 'nowrap', color: 'var(--text-primary)' }}>
                        {formatCO2(record.co2e_kg)}
                      </td>
 
                      {/* Confidence */}
                      <td>
                        <span className={`badge ${CONFIDENCE_META[record.confidence]?.cls || ''}`}>
                          {record.confidence}
                        </span>
                      </td>
 
                      {/* Status */}
                      <td>
                        <span className={`badge ${STATUS_META[record.review_status]?.cls || ''}`}>
                          {STATUS_META[record.review_status]?.label || record.review_status}
                        </span>
                      </td>
 
                      {/* Actions */}
                      <td>
                        {!record.is_locked ? (
                          <div style={{ display: 'flex', gap: '4px' }}>
                            <ActionBtn
                              icon={CheckCircle} label="Approve" variant="approve"
                              onClick={() => setReviewModal({ id: record.id, action: 'APPROVE' })}
                            />
                            <ActionBtn
                              icon={Flag} label="Flag" variant="flag"
                              onClick={() => { setReviewModal({ id: record.id, action: 'FLAG' }); setReviewNotes(''); }}
                            />
                            <ActionBtn
                              icon={XCircle} label="Reject" variant="reject"
                              onClick={() => { setReviewModal({ id: record.id, action: 'REJECT' }); setReviewNotes(''); }}
                            />
                          </div>
                        ) : (
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Locked</span>
                        )}
                      </td>
                    </tr>
 
                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={8} style={{ padding: 0 }}>
                          <div style={{
                            padding: 'var(--sp-6)',
                            background: '#FAFBFC',
                            borderTop: '1px solid var(--border-light)',
                            borderBottom: '1px solid var(--border-light)',
                          }}>
                            {detailLoading ? (
                              <div style={{ display: 'flex', gap: 'var(--sp-6)' }}>
                                <div style={{ flex: 1 }}>
                                  {[1,2,3,4].map(i => <div key={i} className="skeleton skeleton-text" style={{ marginBottom: 'var(--sp-3)' }} />)}
                                </div>
                                <div style={{ flex: 1 }}>
                                  <div className="skeleton skeleton-chart" style={{ height: '120px' }} />
                                </div>
                              </div>
                            ) : detailData ? (
                              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-8)' }}>
                                {/* Left: Normalized */}
                                <div>
                                  <div style={{
                                    fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-muted)',
                                    textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 'var(--sp-4)',
                                  }}>
                                    Normalized Data
                                  </div>
                                  <div className="detail-grid">
                                    {[
                                      ['Activity', detailData.activity_description],
                                      ['Source ID', detailData.source_identifier || '—'],
                                      ['Normalized', `${parseFloat(detailData.activity_quantity).toLocaleString()} ${detailData.activity_unit}`],
                                      ['Original', `${parseFloat(detailData.original_quantity).toLocaleString()} ${detailData.original_unit}`],
                                      ['Facility', detailData.facility_name || detailData.facility_code || '—'],
                                      ['Country', detailData.country || '—'],
                                    ].map(([label, value]) => (
                                      <div key={label} className="detail-item">
                                        <span className="detail-label">{label}</span>
                                        <span className="detail-value">{value}</span>
                                      </div>
                                    ))}
                                  </div>

                                  {/* Emission factor */}
                                  {detailData.emission_factor_display && (
                                    <div style={{
                                      marginTop: 'var(--sp-4)', padding: 'var(--sp-3)',
                                      background: 'var(--success-bg)', borderRadius: 'var(--r-lg)',
                                      border: '1px solid #BBF7D0',
                                    }}>
                                      <div className="detail-label" style={{ marginBottom: '3px' }}>Emission Factor</div>
                                      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500 }}>
                                        {detailData.emission_factor_display.value} {detailData.emission_factor_display.unit}
                                        <span style={{ color: 'var(--text-muted)', marginLeft: '6px', fontSize: 'var(--text-xs)' }}>
                                          ({detailData.emission_factor_display.source})
                                        </span>
                                      </div>
                                    </div>
                                  )}

                                  {/* Quality flags */}
                                  {detailData.quality_flags?.length > 0 && (
                                    <div style={{ marginTop: 'var(--sp-3)' }}>
                                      <div className="detail-label" style={{ marginBottom: 'var(--sp-2)' }}>Quality Flags</div>
                                      <div className="quality-flags">
                                        {detailData.quality_flags.map((f, i) => (
                                          <span key={i} className="quality-flag">{f.replace(/_/g, ' ')}</span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>

                                {/* Right: Raw source data */}
                                <div>
                                  <div style={{
                                    fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-muted)',
                                    textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 'var(--sp-4)',
                                  }}>
                                    Original Source Data
                                  </div>
                                  {detailData.raw_data ? (
                                    <div style={{
                                      background: 'var(--bg-body)',
                                      border: '1px solid var(--border)',
                                      borderRadius: 'var(--r-lg)',
                                      padding: 'var(--sp-3)',
                                    }}>
                                      {Object.entries(detailData.raw_data).map(([key, value]) => (
                                        <div key={key} style={{
                                          display: 'grid', gridTemplateColumns: '140px 1fr',
                                          gap: 'var(--sp-2)',
                                          padding: '4px 0',
                                          borderBottom: '1px solid var(--border-light)',
                                          fontSize: 'var(--text-xs)',
                                        }}>
                                          <span style={{ color: 'var(--text-muted)', fontFamily: 'monospace' }}>{key}</span>
                                          <span style={{ color: 'var(--text-primary)', wordBreak: 'break-all' }}>{value || '—'}</span>
                                        </div>
                                      ))}
                                    </div>
                                  ) : (
                                    <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Raw data not available</p>
                                  )}

                                  {/* Review info */}
                                  {detailData.reviewed_by_name && (
                                    <div style={{
                                      marginTop: 'var(--sp-4)', padding: 'var(--sp-3)',
                                      background: 'var(--bg-body)', borderRadius: 'var(--r-lg)',
                                      border: '1px solid var(--border-light)',
                                    }}>
                                      <div className="detail-label" style={{ marginBottom: '3px' }}>Reviewed By</div>
                                      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500 }}>
                                        {detailData.reviewed_by_name}
                                      </div>
                                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                                        {formatDate(detailData.reviewed_at)}
                                      </div>
                                      {detailData.review_notes && (
                                        <div style={{
                                          marginTop: 'var(--sp-2)', fontSize: 'var(--text-xs)',
                                          color: 'var(--text-secondary)', fontStyle: 'italic',
                                          padding: 'var(--sp-2)', background: 'var(--bg-surface)',
                                          borderRadius: 'var(--r-sm)', borderLeft: '2px solid var(--border)',
                                        }}>
                                          "{detailData.review_notes}"
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Review Modal */}
      {reviewModal && (
        <div
          className="modal-overlay"
          onClick={() => setReviewModal(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 id="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
                {reviewModal.action === 'APPROVE' && (
                  <><CheckCircle size={18} color="var(--success)" /> Approve record</>
                )}
                {reviewModal.action === 'FLAG' && (
                  <><Flag size={18} color="var(--warning)" /> Flag for review</>
                )}
                {reviewModal.action === 'REJECT' && (
                  <><XCircle size={18} color="var(--danger)" /> Reject record</>
                )}
              </h3>
              <button
                className="modal-close"
                onClick={() => setReviewModal(null)}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {reviewModal.action === 'APPROVE' ? (
              <div style={{
                padding: 'var(--sp-4)',
                background: 'var(--success-bg)',
                borderRadius: 'var(--r-lg)',
                border: '1px solid #BBF7D0',
                fontSize: 'var(--text-sm)',
                color: 'var(--success-text)',
                lineHeight: 'var(--leading-relaxed)',
              }}>
                This record will be <strong>approved and locked for audit</strong>. Once locked, it cannot be modified.
              </div>
            ) : (
              <div className="form-group">
                <label className="form-label" htmlFor="review-notes">
                  Notes <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <textarea
                  id="review-notes"
                  className="form-textarea"
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  placeholder={
                    reviewModal.action === 'FLAG'
                      ? 'Describe what looks suspicious about this record…'
                      : 'Explain why this record is being rejected…'
                  }
                  rows={4}
                  autoFocus
                />
              </div>
            )}

            <div className="modal-footer">
              <button className="btn btn-ghost" onClick={() => setReviewModal(null)}>
                Cancel
              </button>
              <button
                className={`btn ${
                  reviewModal.action === 'APPROVE' ? 'btn-primary'
                  : reviewModal.action === 'FLAG' ? 'btn-warning'
                  : 'btn-danger'
                }`}
                onClick={() => handleReview(reviewModal.id, reviewModal.action)}
                disabled={actionLoading}
              >
                {actionLoading
                  ? 'Processing…'
                  : `Confirm ${reviewModal.action.charAt(0) + reviewModal.action.slice(1).toLowerCase()}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="toast-container" role="status" aria-live="polite">
          <div className={`toast toast-${toast.type}`}>
            {toast.type === 'success'
              ? <CheckCircle size={15} />
              : <XCircle size={15} />}
            {toast.message}
          </div>
        </div>
      )}
    </div>
  );
}
