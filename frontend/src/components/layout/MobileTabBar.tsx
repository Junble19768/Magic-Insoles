import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import type { ReactElement } from 'react'

interface NavItem {
  to: string
  label: string
}

const MAIN_ITEMS: readonly NavItem[] = [
  { to: '/dashboard', label: 'DashBoard' },
  { to: '/activity', label: '运动情况' },
  { to: '/gait', label: '步态分析' },
  { to: '/gps', label: 'GPS轨迹' },
  { to: '/report', label: '运动报告' },
]

const MORE_ITEMS: readonly NavItem[] = [
  { to: '/realtime', label: '实时监测' },
  { to: '/balance', label: '平衡评估' },
]

export function MobileTabBar(): ReactElement {
  const [showMore, setShowMore] = useState(false)

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="主导航">
        {MAIN_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `mobile-tab-bar__item${isActive ? ' mobile-tab-bar__item--active' : ''}`
            }
          >
            {item.label}
          </NavLink>
        ))}
        <button
          type="button"
          className={`mobile-tab-bar__item${showMore ? ' mobile-tab-bar__item--active' : ''}`}
          onClick={() => setShowMore((prev) => !prev)}
        >
          更多
        </button>
      </nav>

      {showMore ? (
        <div className="mobile-more-menu">
          {MORE_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `mobile-more-menu__item${isActive ? ' mobile-more-menu__item--active' : ''}`
              }
              onClick={() => setShowMore(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      ) : null}
    </>
  )
}
