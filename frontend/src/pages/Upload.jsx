import { useState, useRef } from 'react';
import { Upload as UploadIcon, FileText, CheckCircle, XCircle, AlertTriangle, Flame, Zap, Plane } from 'lucide-react';
import api from '../api/client';

const SOURCE_OPTIONS = [
  { value: 'SAP_FUEL', label: 'SAP Fuel & Procurement', icon: Flame, desc: 'ALV CSV export from SAP (ME2M/ME2N)' },
  { value: 'UTILITY_ELECTRICITY', label: 'Utility Electricity', icon: Zap, desc: 'Portal CSV from utility provider' },
  { value: 'TRAVEL', label: 'Corporate Travel', icon: Plane, desc: 'Concur-style expense report CSV' },
];

export default function Upload() {
  const [sourceType, setSourceType] = useState('');
  const [file, setFile] = useState(null);
  const [dragover, setDragover] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragover(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleUpload = async () => {
    if (!file || !sourceType) return;
    setUploading(true);
    setError('');
    setResult(null);

    try {
      const data = await api.uploadFile(file, sourceType);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setSourceType('');
    setResult(null);
    setError('');
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="animate-slide-up">
      <div className="page-header">
        <h2>Upload Data</h2>
        <p>Ingest emissions data from SAP, utility providers, or travel platforms</p>
      </div>

      {/* Step 1: Source Selection */}
      <div className="card" style={{ marginBottom: 'var(--sp-6)' }}>
        <div style={{ marginBottom: 'var(--sp-5)' }}>
          <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
            Step 1: Choose data source
          </h3>
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--sp-3)',
        }}>
          {SOURCE_OPTIONS.map(({ value, label, icon: Icon, desc }) => (
            <button
              key={value}
              onClick={() => setSourceType(value)}
              style={{
                cursor: 'pointer',
                textAlign: 'left',
                padding: 'var(--sp-4)',
                borderRadius: 'var(--r-lg)',
                border: sourceType === value
                  ? '2px solid var(--brand)'
                  : '1px solid var(--border)',
                background: sourceType === value
                  ? 'var(--brand-light)'
                  : 'var(--bg-surface)',
                transition: 'all 150ms ease',
                fontFamily: 'var(--font)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-1)' }}>
                <Icon size={16} color={sourceType === value ? 'var(--brand-dark)' : 'var(--text-muted)'} />
                <span style={{
                  fontWeight: 600,
                  fontSize: 'var(--text-sm)',
                  color: sourceType === value ? 'var(--brand-text)' : 'var(--text-primary)',
                }}>{label}</span>
              </div>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', margin: 0, lineHeight: 1.4 }}>{desc}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Step 2: File Upload */}
      <div className="card" style={{ marginBottom: 'var(--sp-6)' }}>
        <div style={{ marginBottom: 'var(--sp-5)' }}>
          <h3 style={{ fontSize: 'var(--text-md)', fontWeight: 600, color: 'var(--text-primary)' }}>
            Step 2: Upload data
          </h3>
        </div>

        <div
          className={`upload-zone ${dragover ? 'dragover' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
          onDragLeave={() => setDragover(false)}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload file"
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click(); }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.txt,.tsv"
            style={{ display: 'none' }}
            onChange={(e) => setFile(e.target.files[0])}
          />
          <div className="upload-zone-icon">
            <UploadIcon size={24} />
          </div>
          {file ? (
            <>
              <h3 style={{ color: 'var(--brand-dark)' }}>
                <FileText size={14} style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                {file.name}
              </h3>
              <p>{(file.size / 1024).toFixed(1)} KB · Click to change</p>
            </>
          ) : (
            <>
              <h3>Upload data <span style={{ color: 'var(--danger)' }}>*</span></h3>
              <p>Drop CSV file here or click to browse · Max 10MB</p>
            </>
          )}
        </div>
      </div>

      {/* Upload Action */}
      <div style={{ display: 'flex', gap: 'var(--sp-3)', alignItems: 'center' }}>
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={!file || !sourceType || uploading}
          style={{ padding: '10px 28px' }}
        >
          {uploading ? (
            <>
              <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
              Processing…
            </>
          ) : (
            <>
              <UploadIcon size={15} />
              Upload & Process
            </>
          )}
        </button>

        {(file || result || error) && (
          <button className="btn btn-ghost" onClick={resetForm}>
            Reset
          </button>
        )}
      </div>

      {/* Error State */}
      {error && (
        <div className="card" style={{
          marginTop: 'var(--sp-6)',
          borderColor: '#FECACA',
          background: 'var(--danger-bg)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
            <XCircle size={18} color="var(--danger)" />
            <strong style={{ color: 'var(--danger-text)', fontSize: 'var(--text-sm)' }}>Upload Failed</strong>
          </div>
          <p style={{ marginTop: 'var(--sp-2)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            {error}
          </p>
        </div>
      )}

      {/* Success Result */}
      {result && (
        <div className="card" style={{ marginTop: 'var(--sp-6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)', marginBottom: 'var(--sp-5)' }}>
            <CheckCircle size={18} color="var(--success)" />
            <strong style={{ fontSize: 'var(--text-md)', color: 'var(--text-primary)' }}>Upload Complete</strong>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--sp-4)' }}>
            <div style={{
              textAlign: 'center', padding: 'var(--sp-4)',
              background: 'var(--bg-body)', borderRadius: 'var(--r-lg)',
            }}>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800, color: 'var(--text-primary)' }}>{result.total_rows}</div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>Total Rows</div>
            </div>
            <div style={{
              textAlign: 'center', padding: 'var(--sp-4)',
              background: 'var(--success-bg)', borderRadius: 'var(--r-lg)',
            }}>
              <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800, color: 'var(--success-text)' }}>
                {result.success_rows}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>Processed</div>
            </div>
            <div style={{
              textAlign: 'center', padding: 'var(--sp-4)',
              background: result.error_rows > 0 ? 'var(--danger-bg)' : 'var(--bg-body)',
              borderRadius: 'var(--r-lg)',
            }}>
              <div style={{
                fontSize: 'var(--text-2xl)', fontWeight: 800,
                color: result.error_rows > 0 ? 'var(--danger-text)' : 'var(--text-muted)',
              }}>
                {result.error_rows}
              </div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>Errors</div>
            </div>
          </div>

          {/* Progress */}
          <div style={{ marginTop: 'var(--sp-5)' }}>
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{
                  width: `${result.total_rows ? (result.success_rows / result.total_rows * 100) : 0}%`,
                  background: result.error_rows > 0 ? 'var(--warning)' : 'var(--brand)',
                }}
              />
            </div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 'var(--sp-1)' }}>
              {result.total_rows ? Math.round(result.success_rows / result.total_rows * 100) : 0}% success rate
            </p>
          </div>

          {/* Error Details */}
          {result.error_log && result.error_log.length > 0 && (
            <div style={{ marginTop: 'var(--sp-6)' }}>
              <h4 style={{
                display: 'flex', alignItems: 'center', gap: 'var(--sp-2)',
                marginBottom: 'var(--sp-3)', fontSize: 'var(--text-sm)', fontWeight: 600,
              }}>
                <AlertTriangle size={14} color="var(--warning)" />
                Error Details
              </h4>
              <div style={{
                maxHeight: '200px', overflow: 'auto',
                background: 'var(--bg-body)', borderRadius: 'var(--r-lg)',
                padding: 'var(--sp-3)', border: '1px solid var(--border-light)',
              }}>
                {result.error_log.map((err, i) => (
                  <div key={i} style={{
                    fontSize: 'var(--text-xs)', padding: '4px 0',
                    borderBottom: '1px solid var(--border-light)',
                    color: 'var(--text-secondary)',
                  }}>
                    <strong style={{ color: 'var(--text-primary)' }}>Row {err.row}:</strong>{' '}
                    {err.errors.join('; ')}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
