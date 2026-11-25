/**
 * ==============================================================================
 * CALYX FRONTEND: CENTRALIZED API CLIENT LAYER
 * ==============================================================================
 * File: frontend/src/api.js
 * Purpose:
 *   Handles all network communication between the React frontend UI and the
 *   Calyx Unified API Gateway (Port 8000).
 *   
 * Features:
 *   1. Automatic JWT token injection from localStorage.
 *   2. Base URL fallback (defaults to http://127.0.0.1:8000 or relative /api/v1).
 *   3. Transparent error handling with user-friendly messages.
 *   4. Full support for JSON payloads and multipart/form-data file uploads.
 * ==============================================================================
 */

// Base API URL pointing to the Calyx Unified API Gateway
// In development, if VITE_API_URL is unset, default to the gateway port 8000
export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

/**
 * Retrieves the stored JWT access token from localStorage.
 */
export function getAuthToken() {
  return localStorage.getItem('calyx_token') || '';
}

/**
 * Stores the JWT access token and user information in localStorage.
 */
export function setAuthSession(token, user) {
  localStorage.setItem('calyx_token', token);
  localStorage.setItem('calyx_user', JSON.stringify(user));
}

/**
 * Clears the stored JWT token and user info (Logout).
 */
export function clearAuthSession() {
  localStorage.removeItem('calyx_token');
  localStorage.removeItem('calyx_user');
}

/**
 * Retrieves the currently logged in user profile from localStorage.
 */
export function getCurrentUser() {
  const userStr = localStorage.getItem('calyx_user');
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch (e) {
    return null;
  }
}

/**
 * Core HTTP fetch wrapper with authorization header injection and error handling.
 */
async function request(endpoint, options = {}) {
  // Read JWT token
  const token = getAuthToken();

  // Prepare standard headers
  const headers = {
    ...options.headers,
  };

  // If the payload is not FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject Bearer token if available
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Construct full request URL
  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Parse JSON response body
    const data = await response.json().catch(() => ({}));

    // If HTTP status is not 2xx, throw structured error
    if (!response.ok) {
      const errorMessage = data?.error?.message || data?.detail || `HTTP Error ${response.status}`;
      const err = new Error(errorMessage);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    console.error(`API Call failed to ${endpoint}:`, error);
    throw error;
  }
}

// ==============================================================================
// 1. AUTHENTICATION & IDENTITY (Auth Service - Port 8001 via Gateway)
// ==============================================================================
export const authApi = {
  // Register a new candidate or recruiter
  register: (payload) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Login with email and password
  login: (payload) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Get current user profile using JWT token
  getProfile: () => request('/auth/profile', { method: 'GET' }),
};

// ==============================================================================
// 2. JOB REQUISITION & APPLICATIONS (Job Service - Port 8002 via Gateway)
// ==============================================================================
export const jobApi = {
  // List all open jobs with optional search filters
  getJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/jobs/?${query}`, { method: 'GET' });
  },

  // Get single job details
  getJobById: (jobId) => request(`/jobs/${jobId}`, { method: 'GET' }),

  // Create a new job requisition (Recruiter/Admin only)
  createJob: (jobData) =>
    request('/jobs/', {
      method: 'POST',
      body: JSON.stringify(jobData),
    }),

  // Submit candidate application
  applyForJob: (applicationData) =>
    request('/jobs/applications', {
      method: 'POST',
      body: JSON.stringify(applicationData),
    }),

  // Get applications for a specific job (Recruiter view)
  getJobApplications: (jobId) => request(`/jobs/${jobId}/applications`, { method: 'GET' }),
};

// ==============================================================================
// 3. RESUME PARSING & VECTOR SEARCH (Resume Service - Port 8003 via Gateway)
// ==============================================================================
export const resumeApi = {
  // Upload resume as raw text or file
  uploadResumeText: (payload) =>
    request('/resumes/upload', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Get resume by ID
  getResumeById: (resumeId) => request(`/resumes/${resumeId}`, { method: 'GET' }),

  // Semantic vector search over candidate resumes
  vectorSearch: (searchParams) =>
    request('/resumes/search', {
      method: 'POST',
      body: JSON.stringify(searchParams),
    }),
};

// ==============================================================================
// 4. AUTONOMOUS AGENTIC AI SCREENING (Agent Service - Port 8004 via Gateway)
// ==============================================================================
export const agentApi = {
  // Trigger 4-agent evaluation pipeline for an applicant
  evaluateApplication: (payload) =>
    request('/agent/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Retrieve transparent reasoning trace from Redis
  getReasoningTrace: (taskId) => request(`/agent/trace/${taskId}`, { method: 'GET' }),
};

// ==============================================================================
// 5. RECRUITMENT ANALYTICS & OBSERVABILITY (Analytics & Gateway Services)
// ==============================================================================
export const analyticsApi = {
  // Get recruitment pipeline conversion funnels and overview stats
  getOverview: () => request('/analytics/overview', { method: 'GET' }),

  // Get score distribution histogram for a job
  getJobScoreDistribution: (jobId) => request(`/analytics/job/${jobId}/scores`, { method: 'GET' }),

  // Get aggregate live health and Circuit Breaker states for all 5 microservices
  getSystemHealth: () => request('/system/health', { method: 'GET' }),
};
