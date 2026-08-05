// src/components/EnvironmentAlertBanner.tsx
'use client';

import { useEffect, useState, useCallback } from 'react';

const POLL_INTERVAL_MS = 60_000; // 1 minute

interface EnvStatus {
  aqi: number | null;
  temperature_celsius: number;
  rainfall_mm_hr: number;
  wind_speed_kmh: number;
  threshold_breached: boolean;
  current_condition: string;
  dominant_trigger: 'rainfall' | 'aqi' | 'heat' | null;
  policy_id: string;
}

type BannerState = 'loading' | 'normal' | 'warning' | 'error' | 'hidden';

interface Props {
  lat: number;
  lon: number;
  policyId?: string;
}

// ── Trigger label map ────────────────────────────────────────────────────────
const TRIGGER_LABELS: Record<string, string> = {
  rainfall: 'Sustained Rainfall >35 mm/hr',
  aqi:      'Air Quality Index >300 NAQI',
  heat:     'Extreme Heat >44°C',
};

export default function EnvironmentAlertBanner({ lat, lon, policyId = '' }: Props) {
  const [status, setStatus] = useState<EnvStatus | null>(null);
  const [bannerState, setBannerState] = useState<BannerState>('loading');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        lat: String(lat),
        lon: String(lon),
        policy_id: policyId,
      });
      const res = await fetch(`/api/environment/status?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: EnvStatus = await res.json();
      setStatus(data);
      setBannerState(data.threshold_breached ? 'warning' : 'normal');
      setLastUpdated(new Date());
      // Re-show if conditions change to warning even after dismiss
      if (data.threshold_breached) setDismissed(false);
    } catch (err) {
      console.warn('[GigGuard] Environment status fetch failed:', err);
      setBannerState('error');
    }
  }, [lat, lon, policyId]);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchStatus]);

  // Don't render anything until first fetch completes
  if (bannerState === 'loading') return null;
  if (dismissed && bannerState !== 'warning') return null;

  // ── Variant styles ───────────────────────────────────────────────────────
  const variants = {
    normal: {
      wrapper: 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300',
      icon: '✅',
      dismissible: false,
    },
    warning: {
      wrapper: 'bg-red-50 dark:bg-red-950/40 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300',
      icon: '⚠️',
      dismissible: true,
    },
    error: {
      wrapper: 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300',
      icon: '📡',
      dismissible: true,
    },
  };

  const v = variants[bannerState as keyof typeof variants] ?? variants.normal;

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div
      role={bannerState === 'warning' ? 'alert' : 'status'}
      aria-live={bannerState === 'warning' ? 'assertive' : 'polite'}
      className={`
        relative flex items-start gap-3 rounded-xl border px-4 py-3 text-sm
        transition-all duration-300 ease-in-out
        ${v.wrapper}
      `}
    >
      {/* Icon */}
      <span className="mt-0.5 shrink-0 text-base" aria-hidden="true">
        {v.icon}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {bannerState === 'warning' && status && (
          <>
            <p className="font-semibold">
              Policy Threshold Reached
              {status.dominant_trigger && ` — ${TRIGGER_LABELS[status.dominant_trigger]}`}
            </p>
            <p className="mt-0.5 opacity-90">
              Auto-payout is being processed for policy{' '}
              <span className="font-mono font-medium">{status.policy_id || 'active'}</span>.
              No action required.
            </p>
          </>
        )}

        {bannerState === 'normal' && status && (
          <p className="font-medium">
            Conditions Normal
            {' — '}
            Temp: <strong>{status.temperature_celsius}°C</strong>
            {' · '}
            Rain: <strong>{status.rainfall_mm_hr} mm/hr</strong>
            {' · '}
            Wind: <strong>{status.wind_speed_kmh} km/h</strong>
            {status.aqi != null && (
              <>{' · '}AQI: <strong>{status.aqi}</strong></>
            )}
            {' · '}
            {status.current_condition}
          </p>
        )}

        {bannerState === 'error' && (
          <p className="font-medium">
            Unable to fetch live conditions. Your policy monitoring continues in the background.
          </p>
        )}

        {/* Last updated timestamp */}
        {lastUpdated && (
          <p className="mt-1 text-xs opacity-60">
            Last updated: {lastUpdated.toLocaleTimeString()} · refreshes every 60s
          </p>
        )}
      </div>

      {/* Dismiss button */}
      {v.dismissible && (
        <button
          onClick={() => setDismissed(true)}
          aria-label="Dismiss alert"
          className="shrink-0 rounded-lg p-1 opacity-60 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-current transition-opacity"
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"/>
          </svg>
        </button>
      )}
    </div>
  );
}