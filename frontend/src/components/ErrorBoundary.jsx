/**
 * ==============================================================================
 * CALYX FRONTEND: REACT ERROR BOUNDARY
 * ==============================================================================
 * File: frontend/src/components/ErrorBoundary.jsx
 * Purpose:
 *   Catches unhandled runtime JavaScript rendering errors, preventing the
 *   application from unmounting into a blank white screen.
 * ==============================================================================
 */

import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Calyx UI Error Caught by Boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-slate-900 border border-rose-500/30 rounded-2xl p-6 shadow-2xl text-center space-y-4">
            <div className="w-12 h-12 rounded-xl bg-rose-500/20 text-rose-400 mx-auto flex items-center justify-center font-bold text-xl">
              !
            </div>
            <h2 className="text-xl font-bold">Something went wrong while rendering</h2>
            <p className="text-xs text-slate-400 font-mono bg-slate-950 p-3 rounded-lg text-left overflow-auto max-h-32">
              {this.state.error?.message || 'Unknown render error'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false });
                window.location.reload();
              }}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/25"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
