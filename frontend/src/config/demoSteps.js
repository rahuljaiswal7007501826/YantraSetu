/**
 * The deterministic SIH walkthrough (Phase 7.7).
 *
 * Each step drives three things when the overlay advances to it:
 *   - `role`  : the console auto-switches to the role that owns this decision
 *   - `path` + `query` : the app navigates to the screen that tells this part
 *   - `body`  : the narration the presenter delivers
 *
 * The story is the product's core loop:
 *   Demand -> Allocation -> Relocation -> Approval -> Route -> Payoff.
 *
 * `action` marks steps where the presenter performs a live click on-screen
 * (approve the move, optimise the route) rather than the overlay doing it -
 * the intelligence stays in the backend engines, the human stays in control.
 */
export const DEMO_STEPS = [
  {
    key: 'intro',
    title: 'The scenario',
    role: 'district_admin',
    path: '/',
    body:
      'A combine-harvester shortage is forming in one cluster while an idle combine sits at another CHC. ' +
      "We'll follow the decision from detection to a prevented shortage - the way YantraSetu makes it.",
  },
  {
    key: 'demand',
    title: '1 · Detect the shortage',
    role: 'district_admin',
    path: '/demand',
    body:
      'The demand engine flags Cluster B: Combine Harvester as CRITICAL - demand far outstrips supply ' +
      '(around 98% shortage probability). This is explainable weighted scoring, not a black box.',
  },
  {
    key: 'allocation',
    title: '2 · Find the best machine',
    role: 'district_admin',
    path: '/allocation',
    query: { cluster: 'Cluster B', type: 'Combine Harvester' },
    body:
      'For a pending farmer request in Cluster B, the allocation engine ranks candidates on seven weighted ' +
      'factors. The best combine is idle at another CHC - so the top candidate is flagged as needing a move.',
  },
  {
    key: 'netbenefit',
    title: '3 · Weigh the move',
    role: 'chc_operator',
    path: '/relocations',
    body:
      'The relocation engine computes NetBenefit: expected revenue at the destination minus revenue lost at ' +
      'the source, minus relocation, operator-time and opportunity costs. Positive net benefit -> it recommends.',
  },
  {
    key: 'approve',
    title: '4 · Operator approves',
    role: 'chc_operator',
    path: '/relocations',
    action: 'Select the pending combine-harvester move to Cluster B and click Approve. It flips to in transit.',
    body:
      'The system never moves a machine on its own. As the CHC operator, you approve the recommended combine ' +
      'relocation. If nothing is pending, use Reset scenario below, then approve it live.',
  },
  {
    key: 'map',
    title: '5 · Machine in transit',
    role: 'district_admin',
    path: '/map',
    body:
      'The live digital-twin map now shows the machine in transit (blue) heading toward the red shortage ' +
      'zone in Cluster B. Every screen updated the moment the operator approved.',
  },
  {
    key: 'route',
    title: '6 · One trip, many farmers',
    role: 'chc_operator',
    path: '/routes',
    // No hardcoded machine id: RoutesPage auto-selects a Combine Harvester, so
    // the demo stays correct after a re-seed (which shifts database ids).
    action: 'Click Optimize route to build the multi-stop plan.',
    body:
      'OR-Tools builds a time-windowed route so the single relocated machine serves several farmers in one ' +
      'trip - minimising travel distance and needless return journeys.',
  },
  {
    key: 'payoff',
    title: '7 · The measurable payoff',
    role: 'district_admin',
    path: '/analytics',
    body:
      'Analytics proves the outcome from live data. Compare Before vs After: relocating one idle machine ' +
      'raised utilisation, cut idle hours, served more farmers and eased the shortage - with net benefit, ' +
      'revenue and cost all shown. That measurable gain is what YantraSetu delivered.',
  },
]
