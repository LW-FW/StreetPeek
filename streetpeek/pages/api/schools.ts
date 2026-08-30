// pages/api/schools.ts
// Serves nearby schools and nurseries from the local datasets built by
// education_scraper.py (data/schools.json, data/nurseries.json — GIAS +
// Ofsted, England only). No live external API call: unlike nearby.ts's
// Overpass lookups, this is a radius query against a dataset refreshed
// out-of-band (monthly, see education_scraper.py's docstring).

import type { NextApiRequest, NextApiResponse } from 'next';
import fs from 'fs';
import path from 'path';

export type RatingFramework = 'report-card' | 'legacy' | 'ungraded-only' | 'none';

export interface SchoolRating {
  framework: RatingFramework;
  categories?: Record<string, string>; // report-card only — 5-word scale per category
  legacyGrade?: 1 | 2 | 3 | 4; // legacy only — 1=Outstanding..4=Inadequate
  inspectionDate: string | null;
  lastInspectionDate: string | null;
  // True when legacyGrade came from Ofsted reaffirming a prior grade during
  // an ungraded monitoring visit ("School remains Good") rather than a
  // fresh full inspection — still the school's real, current published
  // rating, just via a different mechanism.
  confirmedByMonitoringVisit?: boolean;
  // ungraded-only only — the visit's outcome text (e.g. "Standards
  // maintained"), kept for cases where it doesn't state a specific grade.
  ungradedOutcome?: string | null;
}

export interface SchoolResult {
  id: string;
  urn: string;
  name: string;
  phase: string;
  establishmentType: string;
  typeGroup: string;
  ageRange: { low: number | null; high: number | null };
  gender: string | null;
  religiousCharacter: string | null;
  capacity: number | null;
  pupilsOnRoll: number | null;
  address: string;
  postcode: string;
  lat: number;
  lng: number;
  distanceMiles: number;
  rating: SchoolRating;
}

export interface NurseryResult {
  id: string;
  providerUrn: string;
  name: string;
  providerSubtype: string | null;
  places: number | null;
  address: string;
  postcode: string;
  lat: number;
  lng: number;
  distanceMiles: number;
  rating: { grade: 1 | 2 | 3 | 4 | null; inspectionDate: string | null };
}

export interface EducationResponse {
  schools: SchoolResult[];
  nurseries: NurseryResult[];
  summary: {
    radiusMiles: number;
    nearestPrimary: SchoolResult | null;
    nearestSecondary: SchoolResult | null;
    nearestNursery: NurseryResult | null;
    primaryCount: number;
    secondaryCount: number;
    nurseryCount: number;
  };
  dataAsOf: string | null;
}

const DEFAULT_RADIUS_MILES = 2;
const PRIMARY_PHASES = new Set(['Primary', 'Middle deemed primary']);
const SECONDARY_PHASES = new Set(['Secondary', 'Middle deemed secondary', '16 plus']);

function findDataDir(): string {
  // API routes run with cwd = the streetpeek/ package dir; the pipeline
  // writes to a repo-root data/ dir one level up. Falling back to cwd/data
  // covers being invoked from the repo root instead.
  const candidates = [
    path.join(process.cwd(), '..', 'data'),
    path.join(process.cwd(), 'data'),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, 'schools.json'))) return dir;
  }
  throw new Error('Could not locate data/schools.json — run education_scraper.py first');
}

let cache: { schools: any[]; nurseries: any[]; dataAsOf: string | null } | null = null;

function loadData() {
  if (cache) return cache;
  const dir = findDataDir();
  const schools = JSON.parse(fs.readFileSync(path.join(dir, 'schools.json'), 'utf-8'));
  const nurseries = JSON.parse(fs.readFileSync(path.join(dir, 'nurseries.json'), 'utf-8'));
  let dataAsOf: string | null = null;
  try {
    const manifest = JSON.parse(fs.readFileSync(path.join(dir, 'education_manifest.json'), 'utf-8'));
    dataAsOf = manifest.generatedAt ?? null;
  } catch {
    // manifest is informational only
  }
  cache = { schools, nurseries, dataAsOf };
  return cache;
}

function distanceMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3958.8;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export default async function handler(req: NextApiRequest, res: NextApiResponse<EducationResponse | { error: string }>) {
  const { lat, lng, radiusMiles: radiusParam } = req.query;

  if (!lat || !lng) {
    return res.status(400).json({ error: 'lat and lng are required' });
  }

  const latitude = parseFloat(lat as string);
  const longitude = parseFloat(lng as string);
  const radiusMiles = radiusParam ? parseFloat(radiusParam as string) : DEFAULT_RADIUS_MILES;

  const { schools: allSchools, nurseries: allNurseries, dataAsOf } = loadData();

  const schools: SchoolResult[] = allSchools
    .map((s: any): SchoolResult => ({ ...s, distanceMiles: distanceMiles(latitude, longitude, s.lat, s.lng) }))
    .filter((s: SchoolResult) => s.distanceMiles <= radiusMiles)
    .sort((a: SchoolResult, b: SchoolResult) => a.distanceMiles - b.distanceMiles)
    .map((s: SchoolResult) => ({ ...s, distanceMiles: parseFloat(s.distanceMiles.toFixed(2)) }));

  const nurseries: NurseryResult[] = allNurseries
    .map((n: any): NurseryResult => ({ ...n, distanceMiles: distanceMiles(latitude, longitude, n.lat, n.lng) }))
    .filter((n: NurseryResult) => n.distanceMiles <= radiusMiles)
    .sort((a: NurseryResult, b: NurseryResult) => a.distanceMiles - b.distanceMiles)
    .map((n: NurseryResult) => ({ ...n, distanceMiles: parseFloat(n.distanceMiles.toFixed(2)) }));

  const nearestOfPhase = (phases: Set<string>) => schools.find(s => phases.has(s.phase)) ?? null;

  const summary: EducationResponse['summary'] = {
    radiusMiles,
    nearestPrimary: nearestOfPhase(PRIMARY_PHASES),
    nearestSecondary: nearestOfPhase(SECONDARY_PHASES),
    nearestNursery: nurseries[0] ?? null,
    primaryCount: schools.filter(s => PRIMARY_PHASES.has(s.phase)).length,
    secondaryCount: schools.filter(s => SECONDARY_PHASES.has(s.phase)).length,
    nurseryCount: nurseries.length,
  };

  return res.status(200).json({ schools, nurseries, summary, dataAsOf });
}
