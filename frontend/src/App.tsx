import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { RealtimePage } from '@/pages/RealtimePage'
import { ReportPage } from '@/pages/ReportPage'

function AppLayout() {
  return (
    <div className="app-shell">
      <main className="app-shell__content">
        <Routes>
          <Route path="/" element={<Navigate to="/realtime" replace />} />
          <Route path="/realtime" element={<RealtimePage />} />
          <Route path="/report" element={<ReportPage />} />
        </Routes>
      </main>

      <nav className="tab-nav" aria-label="主导航">
        <NavLink to="/realtime" className={({ isActive }) => (isActive ? 'active' : '')}>
          实时
        </NavLink>
        <NavLink to="/report" className={({ isActive }) => (isActive ? 'active' : '')}>
          报告
        </NavLink>
      </nav>
    </div>
  )
}

export default function App() {
  return <AppLayout />
}
