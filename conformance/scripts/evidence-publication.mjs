#!/usr/bin/env node
// A failed model evaluation can be conclusive; a failed control/endpoint cannot.
// Keep this predicate separate from model compliance and test its negative cases.
import { readFileSync } from 'node:fs';

function counts(value) {
  return value && ['passCount', 'totalRuns', 'runsErrored'].every(k => Number.isInteger(value[k]) && value[k] >= 0)
    && value.totalRuns > 0 && value.passCount <= value.totalRuns && value.runsErrored === 0;
}
function conclusive(doc) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return false;
  const controls = doc.controlManifest;
  if (!controls || !['judgeControl', 'behavioralControl', 'judgePositiveControl'].every(k => counts(controls[k]))) return false;
  if (controls.judgeControl.passed !== false || controls.behavioralControl.passed !== false || controls.judgePositiveControl.passed !== true) return false;
  const profiles = Object.values(doc.perProfile ?? {});
  if (!profiles.length || !profiles.every(axes => Object.keys(axes).length > 0 && Object.values(axes).every(counts))) return false;
  const doctrine = doc.doctrineManifests;
  return Array.isArray(doctrine) && doctrine.every(m => m.runsErrored === 0 && Array.isArray(m.perCase) && m.perCase.every(counts));
}
try {
  console.log(conclusive(JSON.parse(readFileSync(process.argv[2], 'utf8'))) ? 'true' : 'false');
} catch {
  console.error('evidence-publication: unreadable or malformed evidence');
  process.exitCode = 1;
}
