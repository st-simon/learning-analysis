import {DurableObject} from 'cloudflare:workers';
import {acquireQuota, releaseQuota} from './quota.mjs';

export class ArticleQuota extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    ctx.storage.sql.exec('CREATE TABLE IF NOT EXISTS flows (id TEXT PRIMARY KEY, binding TEXT NOT NULL, phase TEXT NOT NULL, payload TEXT NOT NULL, expires INTEGER NOT NULL)');
  }
  async createFlow(id, binding, phase, payload) {
    return this.ctx.storage.transactionSync(() => {
      this.ctx.storage.sql.exec('DELETE FROM flows WHERE expires < ?',Date.now());
      const {n}=this.ctx.storage.sql.exec('SELECT COUNT(*) AS n FROM flows').one();
      if (n>=16) return false;
      this.ctx.storage.sql.exec('INSERT INTO flows VALUES (?,?,?,?,?)',id,binding,phase,JSON.stringify(payload),Date.now()+600000);
      return true;
    });
  }
  async takeFlow(id, binding, phase) {
    return this.ctx.storage.transactionSync(() => {
      const rows=this.ctx.storage.sql.exec('SELECT * FROM flows WHERE id=? AND binding=? AND phase=? AND expires>=?',id,binding,phase,Date.now()).toArray();
      if (!rows.length) return null;
      this.ctx.storage.sql.exec('DELETE FROM flows WHERE id=?',id);
      return JSON.parse(rows[0].payload);
    });
  }
  async acquire(requestId) {
    return this.ctx.storage.transactionSync(() => {
      const previous = this.ctx.storage.kv.get('counter');
      const {state, result} = acquireQuota(previous, requestId, Date.now());
      this.ctx.storage.kv.put('counter', state);
      return result;
    });
  }
  async release(requestId) {
    this.ctx.storage.transactionSync(() => {
      const state = this.ctx.storage.kv.get('counter');
      if (state) this.ctx.storage.kv.put('counter', releaseQuota(state, requestId));
    });
  }
}
