// pages/api/nearby.ts
// Fetches nearby GPs, dentists, pharmacies and shops using the Overpass API
// (OpenStreetMap). Free, no API key required.
//
// Overpass docs: https://wiki.openstreetmap.org/wiki/Overpass_API

import type { NextApiRequest, NextApiResponse } from 'next';

export interface NearbyPlace {
  id: string;
  name: string;
  type: 'gp' | 'dentist' | 'pharmacy' | 'supermarket' | 'convenience' | 'gym';
  address: string;
  lat: number;
  lng: number;
  distanceMiles: number;
}

export interface NearbyResponse {
  // False only when every Overpass endpoint failed outright (network/host
  // down) — distinguishes "couldn't fetch" from "fetched fine, nothing
  // nearby" so the UI can offer a retry instead of silently showing empty.
  ok: boolean;
  places: NearbyPlace[];
  summary: {
    radiusMiles: number;
    nearestGP: NearbyPlace | null;
    nearestDentist: NearbyPlace | null;
    nearestPharmacy: NearbyPlace | null;
    supermarketsNearby: number;
    gymsNearby: number;
    convenienceScore: 'well-served' | 'moderate' | 'limited';
    convenienceReason: string;
  };
}

// Three independently-run Overpass instances, deliberately on different
// hosting/network paths (Hetzner, Private.coffee/Austria, OSM France) —
// when one is unreachable (host down, or a network path specifically
// blocking that operator's IPs) a same-host retry just fails the same way,
// so we fall through to a different operator entirely instead.
const OVERPASS_ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
  'https://overpass.openstreetmap.fr/api/interpreter',
];
const RADIUS_MILES = 2;
const RADIUS_METRES = Math.round(RADIUS_MILES * 1609.34);
const ATTEMPTS_PER_ENDPOINT = 1;

// These are shared, rate-limited resources and frequently return 504s
// under load even for small queries — that's the normal cost of using them,
// not a sign something is wrong. One attempt per endpoint before moving to
// the next keeps total latency bounded (3 endpoints, ~30s worst case each)
// while still giving a transient failure on one operator a real chance via
// a completely different one, rather than hammering the same host twice.
async function fetchOverpass(query: string): Promise<any> {
  let lastError: unknown;
  for (const endpoint of OVERPASS_ENDPOINTS) {
    for (let attempt = 1; attempt <= ATTEMPTS_PER_ENDPOINT; attempt++) {
      try {
        // Overpass's Apache front-end 406s Node's default fetch headers (no
        // real User-Agent) and is flaky over compressed responses — Overpass's
        // own usage policy asks for a descriptive User-Agent, so send one.
        const res = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'StreetPeek/1.0 (property research tool; contact via streetpeek app)',
            'Accept-Encoding': 'identity',
          },
          body: `data=${encodeURIComponent(query)}`,
          // Must stay longer than the query's own [timeout:25] below, or we
          // abort a request that Overpass was still legitimately working on.
          signal: AbortSignal.timeout(30000),
        });
        if (res.ok) {
          const json = await res.json();
          // Overpass reports query errors (a malformed filter, or its own
          // internal timeout) with HTTP 200 and a `remark` field, not an
          // error status — treat that as a failed attempt, not zero results,
          // so it gets retried like any other transient failure.
          if (json?.remark || !Array.isArray(json?.elements)) {
            throw new Error(`Overpass reported an error: ${json?.remark ?? 'missing elements array'}`);
          }
          return json;
        }
        lastError = new Error(`Overpass API error: ${res.status}`);
      } catch (err) {
        lastError = err;
      }
      if (attempt < ATTEMPTS_PER_ENDPOINT) {
        await new Promise(r => setTimeout(r, 800 * attempt));
      }
    }
  }
  throw lastError;
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

function classify(tags: Record<string, string>): NearbyPlace['type'] | null {
  // OSM has two parallel tagging schemes for healthcare — the older `amenity=*`
  // and the newer `healthcare=*` — and mappers use one, the other, or both.
  // Checking only one silently drops anything tagged the other way.
  if (tags.amenity === 'doctors' || tags.amenity === 'clinic'
      || tags.healthcare === 'doctor' || tags.healthcare === 'clinic') return 'gp';
  if (tags.amenity === 'dentist' || tags.healthcare === 'dentist') return 'dentist';
  if (tags.amenity === 'pharmacy' || tags.healthcare === 'pharmacy') return 'pharmacy';
  if (tags.shop === 'supermarket') return 'supermarket';
  // Small independent shops get tagged inconsistently — convenience is the
  // "correct" tag but general/grocery/variety_store show up just as often.
  if (tags.shop === 'convenience' || tags.shop === 'general'
      || tags.shop === 'grocery' || tags.shop === 'variety_store') return 'convenience';
  if (tags.leisure === 'fitness_centre' || tags.leisure === 'sports_centre') return 'gym';
  return null;
}

function buildAddress(tags: Record<string, string>): string {
  return [tags['addr:housenumber'] && tags['addr:street']
            ? `${tags['addr:housenumber']} ${tags['addr:street']}`
            : tags['addr:street'],
          tags['addr:city'] || tags['addr:town']]
    .filter(Boolean)
    .join(', ');
}

function overpassQuery(lat: number, lng: number): string {
  const around = `(around:${RADIUS_METRES},${lat},${lng})`;
  const filters = [
    'node["amenity"="doctors"]', 'way["amenity"="doctors"]',
    'node["amenity"="clinic"]', 'way["amenity"="clinic"]',
    'node["healthcare"="doctor"]', 'way["healthcare"="doctor"]',
    'node["healthcare"="clinic"]', 'way["healthcare"="clinic"]',
    'node["amenity"="dentist"]', 'way["amenity"="dentist"]',
    'node["healthcare"="dentist"]', 'way["healthcare"="dentist"]',
    'node["amenity"="pharmacy"]', 'way["amenity"="pharmacy"]',
    'node["healthcare"="pharmacy"]', 'way["healthcare"="pharmacy"]',
    'node["shop"="supermarket"]', 'way["shop"="supermarket"]',
    'node["shop"="convenience"]', 'way["shop"="convenience"]',
    'node["shop"="general"]', 'way["shop"="general"]',
    'node["shop"="grocery"]', 'way["shop"="grocery"]',
    'node["shop"="variety_store"]', 'way["shop"="variety_store"]',
    'node["leisure"="fitness_centre"]', 'way["leisure"="fitness_centre"]',
    'node["leisure"="sports_centre"]', 'way["leisure"="sports_centre"]',
  ].map(f => `${f}${around};`).join('\n  ');
  return `[out:json][timeout:25];\n(\n  ${filters}\n);\nout center tags;`;
}

function convenienceSummary(supermarkets: number, hasGP: boolean, hasPharmacy: boolean):
  { score: NearbyResponse['summary']['convenienceScore']; reason: string } {
  if (supermarkets >= 2 && hasPharmacy) {
    return {
      score: 'well-served',
      reason: `${supermarkets} supermarkets and a pharmacy within ${RADIUS_MILES} miles — day-to-day essentials are within easy reach.`,
    };
  }
  if (supermarkets >= 1 || hasPharmacy || hasGP) {
    return {
      score: 'moderate',
      reason: 'Some essentials nearby, but you may need to travel further for a full shop or GP registration.',
    };
  }
  return {
    score: 'limited',
    reason: `No supermarket, pharmacy or GP found within ${RADIUS_MILES} miles — likely car-dependent for day-to-day needs.`,
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { lat, lng } = req.query;

  if (!lat || !lng) {
    return res.status(400).json({ error: 'lat and lng are required' });
  }

  const latitude = parseFloat(lat as string);
  const longitude = parseFloat(lng as string);

  try {
    const query = overpassQuery(latitude, longitude);
    const data = await fetchOverpass(query);
    const elements: any[] = data.elements;

    const places: NearbyPlace[] = elements
      .map((el): NearbyPlace | null => {
        const tags = el.tags ?? {};
        const type = classify(tags);
        if (!type) return null;

        const placeLat = el.lat ?? el.center?.lat;
        const placeLng = el.lon ?? el.center?.lon;
        if (!placeLat || !placeLng) return null;

        const dist = distanceMiles(latitude, longitude, placeLat, placeLng);
        if (dist > RADIUS_MILES) return null;

        const defaultNames: Record<NearbyPlace['type'], string> = {
          gp: 'GP surgery', dentist: 'Dentist', pharmacy: 'Pharmacy',
          supermarket: 'Supermarket', convenience: 'Shop', gym: 'Gym / leisure centre',
        };

        return {
          id: `${el.type}/${el.id}`,
          name: tags.name || defaultNames[type],
          type,
          address: buildAddress(tags),
          lat: placeLat,
          lng: placeLng,
          distanceMiles: parseFloat(dist.toFixed(2)),
        };
      })
      .filter((p): p is NearbyPlace => p !== null)
      .sort((a, b) => a.distanceMiles - b.distanceMiles);

    // OSM sometimes maps the same physical building as both a node and a way
    // (e.g. a point for the shop plus an outline for the building) — those
    // are within a few metres of each other and should collapse into one
    // entry. A ~11m grid (4 decimal places) catches that without merging
    // genuinely separate branches of the same chain further down the street.
    const seen = new Set<string>();
    const deduped = places.filter(p => {
      const key = `${p.type}:${p.name}:${Math.round(p.lat * 10000)}:${Math.round(p.lng * 10000)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    const nearestOf = (type: NearbyPlace['type']) => deduped.find(p => p.type === type) ?? null;
    const nearestGP = nearestOf('gp');
    const nearestDentist = nearestOf('dentist');
    const nearestPharmacy = nearestOf('pharmacy');
    const supermarketsNearby = deduped.filter(p => p.type === 'supermarket').length;
    const gymsNearby = deduped.filter(p => p.type === 'gym').length;

    const conv = convenienceSummary(supermarketsNearby, !!nearestGP, !!nearestPharmacy);

    const summary: NearbyResponse['summary'] = {
      radiusMiles: RADIUS_MILES,
      nearestGP,
      nearestDentist,
      nearestPharmacy,
      supermarketsNearby,
      gymsNearby,
      convenienceScore: conv.score,
      convenienceReason: conv.reason,
    };

    return res.status(200).json({ ok: true, places: deduped, summary });
  } catch (err) {
    console.error('Nearby API error:', err);
    return res.status(200).json({
      ok: false,
      places: [],
      summary: {
        radiusMiles: RADIUS_MILES,
        nearestGP: null,
        nearestDentist: null,
        nearestPharmacy: null,
        supermarketsNearby: 0,
        gymsNearby: 0,
        convenienceScore: 'limited',
        convenienceReason: 'Could not load nearby amenities data.',
      },
    });
  }
}
