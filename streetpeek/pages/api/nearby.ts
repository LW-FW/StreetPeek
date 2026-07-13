// pages/api/nearby.ts
// Fetches nearby GPs, dentists, pharmacies and shops using the Overpass API
// (OpenStreetMap). Free, no API key required.
//
// Overpass docs: https://wiki.openstreetmap.org/wiki/Overpass_API

import type { NextApiRequest, NextApiResponse } from 'next';

export interface NearbyPlace {
  id: string;
  name: string;
  type: 'gp' | 'dentist' | 'pharmacy' | 'supermarket' | 'convenience';
  address: string;
  lat: number;
  lng: number;
  distanceMiles: number;
}

export interface NearbyResponse {
  places: NearbyPlace[];
  summary: {
    radiusMiles: number;
    nearestGP: NearbyPlace | null;
    nearestDentist: NearbyPlace | null;
    nearestPharmacy: NearbyPlace | null;
    supermarketsNearby: number;
    convenienceScore: 'well-served' | 'moderate' | 'limited';
    convenienceReason: string;
  };
}

const OVERPASS_ENDPOINT = 'https://overpass-api.de/api/interpreter';
const RADIUS_MILES = 2;
const RADIUS_METRES = Math.round(RADIUS_MILES * 1609.34);
const MAX_ATTEMPTS = 3;

// The public Overpass instance is a shared, rate-limited resource and
// frequently returns 504s under load even for small queries — retrying
// is the normal way to use it, not a sign something is wrong.
async function fetchOverpass(query: string): Promise<any> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      // Overpass's Apache front-end 406s Node's default fetch headers (no
      // real User-Agent) and is flaky over compressed responses — Overpass's
      // own usage policy asks for a descriptive User-Agent, so send one.
      const res = await fetch(OVERPASS_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'User-Agent': 'StreetPeek/1.0 (property research tool; contact via streetpeek app)',
          'Accept-Encoding': 'identity',
        },
        body: `data=${encodeURIComponent(query)}`,
        signal: AbortSignal.timeout(15000),
      });
      if (res.ok) return res.json();
      lastError = new Error(`Overpass API error: ${res.status}`);
    } catch (err) {
      lastError = err;
    }
    if (attempt < MAX_ATTEMPTS) {
      await new Promise(r => setTimeout(r, 800 * attempt));
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
  if (tags.amenity === 'doctors' || tags.amenity === 'clinic') return 'gp';
  if (tags.amenity === 'dentist') return 'dentist';
  if (tags.amenity === 'pharmacy') return 'pharmacy';
  if (tags.shop === 'supermarket') return 'supermarket';
  if (tags.shop === 'convenience') return 'convenience';
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
    'node["amenity"="dentist"]', 'way["amenity"="dentist"]',
    'node["amenity"="pharmacy"]', 'way["amenity"="pharmacy"]',
    'node["shop"="supermarket"]', 'way["shop"="supermarket"]',
    'node["shop"="convenience"]', 'way["shop"="convenience"]',
  ].map(f => `${f}${around};`).join('\n  ');
  return `[out:json][timeout:20];\n(\n  ${filters}\n);\nout center tags;`;
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
    const elements: any[] = data?.elements ?? [];

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

        return {
          id: `${el.type}/${el.id}`,
          name: tags.name || (type === 'gp' ? 'GP surgery' : type === 'dentist' ? 'Dentist' :
                type === 'pharmacy' ? 'Pharmacy' : 'Shop'),
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

    const conv = convenienceSummary(supermarketsNearby, !!nearestGP, !!nearestPharmacy);

    const summary: NearbyResponse['summary'] = {
      radiusMiles: RADIUS_MILES,
      nearestGP,
      nearestDentist,
      nearestPharmacy,
      supermarketsNearby,
      convenienceScore: conv.score,
      convenienceReason: conv.reason,
    };

    return res.status(200).json({ places: deduped, summary });
  } catch (err) {
    console.error('Nearby API error:', err);
    return res.status(200).json({
      places: [],
      summary: {
        radiusMiles: RADIUS_MILES,
        nearestGP: null,
        nearestDentist: null,
        nearestPharmacy: null,
        supermarketsNearby: 0,
        convenienceScore: 'limited',
        convenienceReason: 'Could not load nearby amenities data.',
      },
    });
  }
}
