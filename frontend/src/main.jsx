/**
 * ==============================================================================
 * CALYX FRONTEND: REACT 18 APPLICATION ENTRYPOINT
 * ==============================================================================
 * File: frontend/src/main.jsx
 * ==============================================================================
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
