import { createContext, useContext, useMemo, useState } from 'react'

const DemoContext = createContext(null)

/**
 * DemoProvider - skeleton for the Phase 7.7 guided walkthrough.
 *
 * It only holds run state (active + current step) for now, so the "Run Demo"
 * button in the top bar has somewhere to dispatch to. The actual choreography
 * over the pipeline screens is wired up later.
 */
export function DemoProvider({ children }) {
  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)

  const value = useMemo(
    () => ({
      active,
      step,
      start: () => {
        setActive(true)
        setStep(0)
      },
      stop: () => setActive(false),
      next: () => setStep((s) => s + 1),
      goTo: (s) => setStep(s),
    }),
    [active, step],
  )

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

export function useDemo() {
  const ctx = useContext(DemoContext)
  if (!ctx) throw new Error('useDemo must be used within a DemoProvider')
  return ctx
}
