#!/usr/bin/env node
// A failed model evaluation can be conclusive; a failed control/endpoint cannot.
// Keep this predicate separate from model compliance and test its negative cases.
import { readFileSync } from 'node:fs';

function counts(value) {
  return value && ['passCount', 'totalRuns', 'runsErrored'].every(k => Number.isInteger(value[k]) && value[k] >= 0)
    && value.totalRuns > 0 && value.passCount <= value.totalRuns && value.runsErrored === 0;
}
function same(actual, expected) {
  return Array.isArray(expected) && expected.length > 0 && actual.length === expected.length
    && new Set(actual).size === actual.length && actual.every(k => expected.includes(k));
}
function conclusive(doc, expected) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) return false;
  const controls = doc.controlManifest;
  if (!controls || !['judgeControl', 'behavioralControl', 'judgePositiveControl'].every(k => counts(controls[k]))) return false;
  if (controls.judgeControl.passed !== false || controls.behavioralControl.passed !== false || controls.judgePositiveControl.passed !== true) return false;
  if (!expected || !same(Object.keys(doc.perProfile ?? {}), Object.keys(expected.perProfile ?? {}))) return false;
  if (!Object.entries(doc.perProfile).every(([profile, axes]) => axes && same(Object.keys(axes), expected.perProfile[profile]))) return false;
  const profiles = Object.values(doc.perProfile ?? {});
  if (!profiles.length || !profiles.every(axes => Object.keys(axes).length > 0 && Object.values(axes).every(counts))) return false;
  const doctrine = doc.doctrineManifests;
  return Array.isArray(doctrine) && same(doctrine.map(m => m.manifest), Object.keys(expected.doctrineManifests ?? {}))
    && doctrine.every(m => m.runsErrored === 0 && Array.isArray(m.perCase)
      && same(m.perCase.map(c => c.ruleId), expected.doctrineManifests[m.manifest]) && m.perCase.every(counts));
}
try {
  console.log(conclusive(JSON.parse(readFileSync(process.argv[2], 'utf8')), JSON.parse(readFileSync(process.argv[3], 'utf8'))) ? 'true' : 'false');
} catch {
  console.error('evidence-publication: unreadable or malformed evidence');
  process.exitCode = 1;
}
