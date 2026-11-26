/**
 * ==============================================================================
 * CALYX FRONTEND: TOP NAVIGATION COMPONENT
 * ==============================================================================
 * File: frontend/src/components/Navbar.jsx
 * Purpose:
 *   Provides top navigation branding, active tab switching, live Gateway health
 *   indicator dot, user role badge (Candidate vs Recruiter), and auth buttons.
 * ==============================================================================
 */

import React from 'react';

export default function Navbar({
  activeTab,
  setActiveTab,
  currentUser,
  onOpenAuth,
  onLogout,
  gatewayOnline,
}) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Left: Brand Logo & Tagline */}
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('candidate')}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center font-black text-xl text-white shadow-lg shadow-indigo-500/25">
            C
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-xl tracking-tight text-white">CALYX</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Agentic Mesh
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Autonomous AI Smart Hiring Platform</p>
          </div>
        </div>

        {/* Center: Navigation Tabs with Role-Based Access Control */}
        <nav className="flex items-center space-x-1 sm:space-x-2 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('candidate')}
            className={`px-3 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'candidate'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : currentUser?.role === 'recruiter'
                ? 'text-slate-500 hover:text-slate-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>Candidate Portal</span>
            {currentUser?.role === 'recruiter' && (
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.2 rounded text-slate-400">Locked</span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('recruiter')}
            className={`px-3 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-all flex items-center space-x-1.5 ${
              activeTab === 'recruiter'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : currentUser?.role === 'candidate'
                ? 'text-slate-500 hover:text-slate-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            <span>Recruiter Portal</span>
            {currentUser?.role === 'candidate' && (
              <span className="text-[10px] bg-slate-800 px-1.5 py-0.2 rounded text-slate-400">Locked</span>
            )}
          </button>

          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-3 py-1.5 text-xs sm:text-sm font-medium rounded-lg transition-all ${
              activeTab === 'analytics'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Observability & Metrics
          </button>
        </nav>

        {/* Right: Gateway Status & Auth Profile */}
        <div className="flex items-center space-x-3">
          {/* Microservices Gateway Connection Dot */}
          <div
            className="flex items-center space-x-1.5 text-xs px-2.5 py-1 rounded-lg bg-slate-800/60 border border-slate-700/50"
            title={gatewayOnline ? 'Connected to API Gateway (Port 8000)' : 'API Gateway Unreachable'}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                gatewayOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-300 hidden md:inline">
              {gatewayOnline ? 'Gateway UP' : 'Gateway OFF'}
            </span>
          </div>

          {/* User Authentication Status */}
          {currentUser ? (
            <div className="flex items-center space-x-2">
              <div className="text-right hidden sm:block">
                <p className="text-xs font-semibold text-white leading-tight">{currentUser.full_name || currentUser.email}</p>
                <p className="text-[10px] text-indigo-400 capitalize font-medium">{currentUser.role}</p>
              </div>
              <button
                onClick={onLogout}
                className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-400 border border-slate-700 hover:border-rose-500/30 transition-all"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="text-xs sm:text-sm font-semibold px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/25 transition-all"
            >
              Sign In
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
