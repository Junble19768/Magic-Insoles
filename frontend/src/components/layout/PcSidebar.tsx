import { NavLink } from 'react-router-dom'
import type { ReactElement } from 'react'

interface NavItem {
  to: string
  label: string
  icon: string
}

const NAV_ITEMS: readonly NavItem[] = [
  { to: '/dashboard', label: 'DashBoard', icon: '◉' },
  { to: '/activity', label: '运动情况', icon: '▤' },
  { to: '/gait', label: '步态分析', icon: '◎' },
  { to: '/gps', label: 'GPS 轨迹', icon: '⌖' },
  { to: '/report', label: '运动报告', icon: '📋' },
]

export function PcSidebar(): ReactElement {
  return (
    <aside className="pc-sidebar">
      <div className="pc-sidebar__brand">Magic Insoles</div>
      <nav className="pc-sidebar__nav" aria-label="主导航">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `pc-sidebar__item${isActive ? ' pc-sidebar__item--active' : ''}`
            }
          >
            <span className="pc-sidebar__icon" aria-hidden="true">
              {item.icon}
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
