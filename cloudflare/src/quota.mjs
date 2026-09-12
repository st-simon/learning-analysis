// Pure transition is reused by the SQLite object and tested with a controlled clock.
export function acquireQuota(previous, requestId, now) {
  const day = new Date(now).toISOString().slice(0, 10);
  const state = previous || {day, attempts: 0, lease: null, until: 0};
  if (state.lease && state.until > now) return {state, result: {allowed: false, code: 'BUSY'}};
  const attempts = state.day === day ? state.attempts : 0;
  if (attempts >= 10) return {state, result: {allowed: false, code: 'DAILY_LIMIT'}};
  return {state: {day, attempts: attempts + 1, lease: requestId, until: now + 60_000}, result: {allowed: true}};
}

export function releaseQuota(state, requestId) {
  return state?.lease === requestId ? {...state, lease: null, until: 0} : state;
}
