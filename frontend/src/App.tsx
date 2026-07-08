import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useIsPc } from '@/hooks/useMediaQuery'
import { preloadBoundaryAssets } from '@/viz/boundary'
import { PcSidebar } from '@/components/layout/PcSidebar'
import { MobileTabBar } from '@/components/layout/MobileTabBar'
import { DashboardPage } from '@/pages/DashboardPage'
import { ActivityPage } from '@/pages/ActivityPage'
import { GaitPage } from '@/pages/GaitPage'
import { GpsPage } from '@/pages/GpsPage'
import { RealtimePage } from '@/pages/RealtimePage'
import { ReportPage } from '@/pages/ReportPage'
import { BalancePage } from '@/pages/BalancePage'

export default function App() {
  const isPc = useIsPc()

  useEffect(() => {
    void preloadBoundaryAssets()
  }, [])

  return (
    <div className="app-shell">
      {isPc ? <PcSidebar /> : null}

      <main className={`app-shell__content${isPc ? ' app-shell__content--pc' : ''}`}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/gait" element={<GaitPage />} />
          <Route path="/gps" element={<GpsPage />} />
          <Route path="/report" element={<ReportPage />} />
          <Route path="/realtime" element={<RealtimePage />} />
          <Route path="/balance" element={<BalancePage />} />
        </Routes>
      </main>

      {!isPc ? <MobileTabBar /> : null}
    </div>
  )
}
