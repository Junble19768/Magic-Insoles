import { useCallback, useEffect, useState } from 'react'

/**
 * Reactive media query hook. Returns true when the viewport matches the given query.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches)

  const handleChange = useCallback((event: MediaQueryListEvent) => {
    setMatches(event.matches)
  }, [])

  useEffect(() => {
    const mql = window.matchMedia(query)
    setMatches(mql.matches)
    mql.addEventListener('change', handleChange)
    return () => mql.removeEventListener('change', handleChange)
  }, [query, handleChange])

  return matches
}

/** True when viewport width >= 768px (PC layout). */
export function useIsPc(): boolean {
  return useMediaQuery('(min-width: 768px)')
}
