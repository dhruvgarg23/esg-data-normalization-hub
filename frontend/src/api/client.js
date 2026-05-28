const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

class ApiClient {
  constructor() {
    this.token = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  setTokens(access, refresh) {
    this.token = access;
    this.refreshToken = refresh;
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  }

  clearTokens() {
    this.token = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  isAuthenticated() {
    return !!this.token;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = { ...options.headers };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && this.refreshToken) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        headers['Authorization'] = `Bearer ${this.token}`;
        const retryResponse = await fetch(url, { ...options, headers });
        if (!retryResponse.ok) {
          const error = await retryResponse.json().catch(() => ({}));
          throw new Error(error.detail || error.error || `Request failed: ${retryResponse.status}`);
        }
        return retryResponse.json();
      }
      this.clearTokens();
      window.location.href = '/';
      throw new Error('Session expired');
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.error || JSON.stringify(error) || `Request failed: ${response.status}`);
    }

    if (response.status === 204) return null;
    return response.json();
  }

  async tryRefresh() {
    try {
      const response = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: this.refreshToken }),
      });
      if (response.ok) {
        const data = await response.json();
        this.setTokens(data.access, this.refreshToken);
        return true;
      }
    } catch (e) {
      // ignore
    }
    return false;
  }


  async login(username, password) {
    const data = await this.request('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    this.setTokens(data.access, data.refresh);
    return data;
  }

  async getCurrentUser() {
    return this.request('/core/me/');
  }



  async uploadFile(file, sourceType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('source_type', sourceType);
    return this.request('/ingestion/upload/', {
      method: 'POST',
      body: formData,
    });
  }

  async getJobs(page = 1) {
    return this.request(`/ingestion/jobs/?page=${page}`);
  }

  async getJobErrors(jobId) {
    return this.request(`/ingestion/jobs/${jobId}/errors/`);
  }



  async getEmissions(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.append(k, v);
    });
    return this.request(`/emissions/records/?${query.toString()}`);
  }

  async getEmissionDetail(id) {
    return this.request(`/emissions/records/${id}/`);
  }

  async reviewRecord(id, action, notes = '') {
    return this.request(`/emissions/records/${id}/review/`, {
      method: 'PATCH',
      body: JSON.stringify({ action, notes }),
    });
  }

  async bulkApprove(recordIds) {
    return this.request('/emissions/bulk-approve/', {
      method: 'POST',
      body: JSON.stringify({ record_ids: recordIds }),
    });
  }

  async getStats() {
    return this.request('/emissions/stats/');
  }

  async getAuditLog(recordId = null) {
    const params = recordId ? `?record_id=${recordId}` : '';
    return this.request(`/review/audit-log/${params}`);
  }
}

export const api = new ApiClient();
export default api;
