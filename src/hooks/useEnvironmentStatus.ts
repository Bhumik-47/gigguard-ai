// src/hooks/useEnvironmentStatus.ts
'use client';

import { useState, useEffect, useCallback } from 'react';

interface EnvStatus {
  aqi: number | null;
  temperature_celsius: number;
  rainfall_mm_hr: number;
  threshold_breached: boolean;
  current_condition: string;
  dominant_trigger: string | null;
}

interface UseEnvironmentStatusOptions {
  lat: number;
  lon: number;
  policyId?: string;
  pollIntervalMs?: number;
  enabled?: boolean;
}

export function useEnvironmentStatus({
  lat,
  lon,
  policyId = '',
  pollIntervalMs = 60_000,
  enabled = true,
}: UseEnvironmentStatusOptions) {
  const [data, setData] = useState<EnvStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetch_ = useCallback(async () => {
    if (!enabled) return;
    try {
      const params = new URLSearchParams({ lat: String(lat), lon: String(lon), policy_id: policyId });
      const res = await fetch(`/api/environment/status?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
    } finally {
      setIsLoading(false);
    }
  }, [lat, lon, policyId, enabled]);

  useEffect(() => {
    fetch_();
    if (!enabled) return;
    const id = setInterval(fetch_, pollIntervalMs);
    return () => clearInterval(id);
  }, [fetch_, pollIntervalMs, enabled]);

  return { data, isLoading, error, refetch: fetch_ };
}