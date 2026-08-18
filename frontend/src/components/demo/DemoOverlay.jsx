import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, ChevronLeft, ChevronRight, RotateCcw, Sparkles, X } from 'lucide-react'

import { DEMO_STEPS } from '../../config/demoSteps'
import { useDemo } from '../../context/DemoContext'
import { useRole } from '../../context/RoleContext'
import { useDemoReset } from '../../hooks/useDemoReset'
import Button from '../ui/Button'

/**
 * DemoOverlay - the floating presenter panel for the guided walkthrough.
 *
 * It does NOT block the page (no backdrop): the presenter still clicks Approve
 * and Optimise live on the real screens. Advancing a step auto-navigates and
 * auto-switches role; exiting restores the role the user started from.
 */
export default function DemoOverlay() {
  const { active, step, next, goTo, stop } = useDemo()
  const { role, setRole } = useRole()
  const navigate = useNavigate()
  const reset = useDemoReset()

  const prevActiveRef = useRef(false)
  const originalRoleRef = useRef(null)

  const idx = Math.min(step, DEMO_STEPS.length - 1)
  const current = DEMO_STEPS[idx]
  const isLast = idx >= DEMO_STEPS.length - 1

  // Drive navigation + role on every step change; capture/restore role on the
  // active edges. role is intentionally not a dependency - we don't want a
  // manual role switch mid-demo to re-navigate.
  useEffect(() => {
    if (!active) {
      if (prevActiveRef.current && originalRoleRef.current) {
        setRole(originalRoleRef.current)
        originalRoleRef.current = null
      }
      prevActiveRef.current = false
      return
    }
    if (!prevActiveRef.current) {
      originalRoleRef.current = role // pre-demo role, captured before we switch
      prevActiveRef.current = true
    }
    const s = DEMO_STEPS[idx]
    if (!s) return
    if (s.role && s.role !== role) setRole(s.role)
    navigate(s.query ? `${s.path}?${new URLSearchParams(s.query)}` : s.path)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, idx])

  if (!active) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center p-3 sm:p-4">
      <div className="pointer-events-auto w-full max-w-2xl rounded-2xl border border-slate-200 bg-white shadow-2xl ring-1 ring-black/5">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-2.5">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
            <Sparkles size={13} /> Demo mode
          </span>
          <span className="text-xs text-slate-400">
            Step {idx + 1} of {DEMO_STEPS.length}
          </span>
          <button
            onClick={stop}
            className="ml-auto rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            aria-label="Exit demo"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="px-4 py-3">
          <div className="mb-2 flex items-center gap-1.5">
            {DEMO_STEPS.map((s, i) => (
              <button
                key={s.key}
                onClick={() => goTo(i)}
                title={s.title}
                className={`h-1.5 rounded-full transition-all ${
                  i === idx ? 'w-6 bg-emerald-500' : 'w-3 bg-slate-200 hover:bg-slate-300'
                }`}
              />
            ))}
          </div>

          <h3 className="text-sm font-semibold text-slate-900">{current.title}</h3>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">{current.body}</p>

          {current.action && (
            <p className="mt-2.5 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
              <span>
                <span className="font-semibold">Do this now: </span>
                {current.action}
              </span>
            </p>
          )}

          {reset.isSuccess && (
            <p className="mt-2 text-xs text-emerald-600">Scenario reset to baseline.</p>
          )}
          {reset.isError && (
            <p className="mt-2 text-xs text-red-600">{reset.error?.message || 'Reset failed.'}</p>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-2 border-t border-slate-100 px-4 py-2.5">
          <button
            onClick={() => reset.mutate()}
            disabled={reset.isPending}
            className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 disabled:opacity-60"
            title="Rewind the relocation so you can approve it live again"
          >
            <RotateCcw size={14} className={reset.isPending ? 'animate-spin' : ''} />
            {reset.isPending ? 'Resetting...' : 'Reset scenario'}
          </button>

          <div className="ml-auto flex items-center gap-2">
            <Button variant="secondary" onClick={() => goTo(Math.max(0, idx - 1))} disabled={idx === 0}>
              <ChevronLeft size={16} /> Back
            </Button>
            {isLast ? (
              <Button onClick={stop}>Finish</Button>
            ) : (
              <Button onClick={next}>
                Next <ChevronRight size={16} />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
