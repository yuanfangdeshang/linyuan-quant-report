// Ordered, connection-local deltas. Arrays can append without resending their history.
export function diffState(before, after, path = [], changes = []) {
  if (Object.is(before, after)) return changes;
  const objects = before !== null && after !== null && typeof before === 'object' && typeof after === 'object';
  if (!objects || Array.isArray(before) !== Array.isArray(after)) {
    changes.push([path, after]); return changes;
  }
  for (const key of Object.keys(before)) if (!Object.hasOwn(after, key)) changes.push([[...path, key]]);
  for (const key of Object.keys(after)) diffState(before[key], after[key], [...path, key], changes);
  if (Array.isArray(after) && before.length !== after.length) changes.push([[...path, 'length'], after.length]);
  return changes;
}
export function applyStatePatch(state, changes) {
  // Clone only touched branches: retained UI references stay immutable.
  let result = state;
  const copied = new Set();
  for (const [path, value] of changes) {
    if (!path.length) { result = value; continue; }
    if (path.some(key => ['__proto__', 'prototype', 'constructor'].includes(key))) throw Error('Invalid state path');
    if (!copied.has(result)) { result = Array.isArray(result) ? [...result] : {...result}; copied.add(result); }
    let target = result;
    for (const key of path.slice(0, -1)) {
      if (!copied.has(target[key])) { target[key] = Array.isArray(target[key]) ? [...target[key]] : {...target[key]}; copied.add(target[key]); }
      target = target[key];
    }
    const key = path.at(-1);
    if (value === undefined) delete target[key]; else target[key] = value;
  }
  return result;
}
