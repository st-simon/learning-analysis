import {test} from 'node:test';
import assert from 'node:assert/strict';
import {acquireQuota, releaseQuota} from '../src/quota.mjs';

test('eleventh attempt rejected with state surviving reconstructed callers', () => {
  let state;
  const now = Date.parse('2026-09-13T12:00:00Z');
  for (let i=0;i<10;i++) {
    const outcome=acquireQuota(structuredClone(state),String(i),now);
    assert.equal(outcome.result.allowed,true);
    state=releaseQuota(outcome.state,String(i));
  }
  assert.equal(acquireQuota(state,'11',now).result.code,'DAILY_LIMIT');
  assert.equal(acquireQuota(state,'tomorrow',now+86400000).state.attempts,1);
});
test('busy rejection does not consume attempt; expired lease recovers', () => {
  const a=acquireQuota(undefined,'first',1000);
  const b=acquireQuota(a.state,'second',1001);
  assert.equal(b.result.code,'BUSY');
  assert.equal(b.state.attempts,1);
  assert.equal(releaseQuota(a.state,'wrong').lease,'first');
  assert.equal(acquireQuota(a.state,'new',61000).result.allowed,true);
});
test('midnight cannot clear a still-active lease', () => {
  const now=Date.parse('2026-09-13T23:59:59Z');
  const a=acquireQuota(undefined,'first',now);
  assert.equal(acquireQuota(a.state,'second',now+2000).result.code,'BUSY');
});
