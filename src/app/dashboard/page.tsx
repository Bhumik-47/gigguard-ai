// src/app/dashboard/page.tsx — add the banner near the top of the page content
import EnvironmentAlertBanner from '@/components/EnvironmentAlertBanner';

// Inside your dashboard JSX, above the main content grid:
export default function DashboardPage() {
  // Pull worker lat/lon and policyId from your existing data fetch / session
  const workerLat = 12.9716;   // replace with actual value from worker profile
  const workerLon = 77.5946;
  const activePolicyId = 'POL-001'; // replace with actual from session/API

  return (
    <main className="p-6 space-y-6">
      {/* Environment Alert Banner — shows at top of dashboard */}
      <EnvironmentAlertBanner
        lat={workerLat}
        lon={workerLon}
        policyId={activePolicyId}
      />

      {/* ... rest of existing dashboard content ... */}
    </main>
  );
}