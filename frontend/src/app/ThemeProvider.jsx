import { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react'

const ThemeContext = createContext(null)
export const useTheme = () => useContext(ThemeContext)

const STORAGE_KEY = 'fiq-theme'

function systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function resolve(mode) {
  return mode === 'system' ? (systemPrefersDark() ? 'dark' : 'light') : mode
}

function applyResolvedTheme(resolved) {
  document.documentElement.classList.toggle('dark', resolved === 'dark')
}

/**
 * Resolution order: saved preference (localStorage, and eventually
 * user.preferences.theme once Settings exists server-side) -> system -> light.
 * index.html has a blocking inline script that mirrors this logic so there is
 * no flash of the wrong theme before React mounts.
 */
export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => localStorage.getItem(STORAGE_KEY) || 'system')
  const [resolved, setResolved] = useState(() => resolve(mode))

  useEffect(() => {
    const next = resolve(mode)
    setResolved(next)
    applyResolvedTheme(next)
    localStorage.setItem(STORAGE_KEY, mode)
  }, [mode])

  useEffect(() => {
    if (mode !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => {
      const next = resolve('system')
      setResolved(next)
      applyResolvedTheme(next)
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [mode])

  const cycle = useCallback(() => {
    setMode((m) => (m === 'light' ? 'dark' : m === 'dark' ? 'system' : 'light'))
  }, [])

  const value = useMemo(
    () => ({ mode, resolvedTheme: resolved, setMode, cycle }),
    [mode, resolved, cycle]
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
