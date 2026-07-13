// pages/api/schools.ts
// Fetches nearby schools and nurseries using the Get Information About Schools (GIAS) API
// and Ofsted ratings from the Ofsted open data feed.
//
// GIAS API docs: https://get-information-schools.service.gov.uk/glossary
// Free, no API key required.

import type { NextApiRequest, NextApiResponse } from 'next';

export interface School {
  urn: string;
  name: string;
  type: 'primary' | 'secondary' | 'nursery' | 'allthrough' | 'other';
  phase: string;
  address: string;
  postcode: string;
  lat: number;
  lng: number;
  ofstedRating: 1 | 2 | 3 | 4 | null; // 1=Outstanding, 2=Good, 3=Requires Improvement, 4=Inadequate
  ofstedRatingLabel: string;
  numberOfPupils: number | null;
  capacityUtil: number | null; // percentage full
  distanceMiles: number;
  isNursery: boolean;
}

export interface SchoolsResponse {
  schools: School[];
  summary: {
    totalSchools: number;
    totalNurseries: number;
    trafficRisk: 'low' | 'medium' | 'high';
    trafficRiskReason: string;
    within400m: number;
    outstanding: number;
    good: number;
  };
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

function classifyType(phase: string, typeCode: string): School['type'] {
  const p = phase.toLowerCase();
  const t = typeCode.toLowerCase();
  if (t.includes('nursery') || t.includes('early years') || p === 'nursery') return 'nursery';
  if (p === 'primary' || p === 'infant' || p === 'junior' || p === 'middle deemed primary') return 'primary';
  if (p === 'secondary' || p === 'middle deemed secondary' || p === '16 plus') return 'secondary';
  if (p === 'all-through') return 'allthrough';
  return 'other';
}

function ofstedLabel(rating: number | null): string {
  switch (rating) {
    case 1: return 'Outstanding';
    case 2: return 'Good';
    case 3: return 'Requires Improvement';
    case 4: return 'Inadequate';
    default: return 'Not yet inspected';
  }
}

function computeTrafficRisk(schools: School[]): { risk: 'low' | 'medium' | 'high'; reason: string } {
  const within400m = schools.filter(s => s.distanceMiles <= 0.25).length;
  const within800m = schools.filter(s => s.distanceMiles <= 0.5).length;
  const primaryOrSecondaryClose = schools.filter(
    s => s.distanceMiles <= 0.25 && (s.type === 'primary' || s.type === 'secondary')
  ).length;

  if (primaryOrSecondaryClose >= 3 || within400m >= 4) {
    return {
      risk: 'high',
      reason: `${within400m} school${within400m !== 1 ? 's' : ''} within 400m — expect significant traffic Mon–Fri at 8–9am and 3–4pm.`,
    };
  }
  if (primaryOrSecondaryClose >= 1 || within800m >= 3) {
    return {
      risk: 'medium',
      reason: `${within800m} school${within800m !== 1 ? 's' : ''} within 800m — moderate school-run traffic likely on weekday mornings and afternoons.`,
    };
  }
  return {
    risk: 'low',
    reason: 'No schools within 400m. School-run traffic is unlikely to affect this area significantly.',
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { lat, lng } = req.query;

  if (!lat || !lng) {
    return res.status(400).json({ error: 'lat and lng are required' });
  }

  const latitude = parseFloat(lat as string);
  const longitude = parseFloat(lng as string);
  const radiusMetres = 1500; // ~1 mile

  try {
    // GIAS API — search establishments near a point
    // Returns up to 100 establishments within radius
    const giasUrl = new URL('https://get-information-schools.service.gov.uk/api/v1/Establishments/search');
    giasUrl.searchParams.set('lat', latitude.toString());
    giasUrl.searchParams.set('lon', longitude.toString());
    giasUrl.searchParams.set('rad', radiusMetres.toString());
    giasUrl.searchParams.set('limit', '100');
    // Only open establishments
    giasUrl.searchParams.set('statusCode', '1');

    const giasRes = await fetch(giasUrl.toString(), {
      headers: { Accept: 'application/json' },
      // 8 second timeout
      signal: AbortSignal.timeout(8000),
    });

    if (!giasRes.ok) {
      throw new Error(`GIAS API error: ${giasRes.status}`);
    }

    const giasData = await giasRes.json();
    const establishments: any[] = giasData?.Establishments ?? giasData?.establishments ?? [];

    const schools: School[] = establishments
      .map((e: any): School | null => {
        const schoolLat = parseFloat(e.Latitude ?? e.latitude ?? '0');
        const schoolLng = parseFloat(e.Longitude ?? e.longitude ?? '0');

        if (!schoolLat || !schoolLng) return null;

        const dist = distanceMiles(latitude, longitude, schoolLat, schoolLng);
        if (dist > 1.0) return null; // hard cap at 1 mile

        const phaseLabel = e.PhaseOfEducation?.Name ?? e.PhaseOfEducationName ?? '';
        const typeLabel = e.TypeOfEstablishment?.Name ?? e.TypeOfEstablishmentName ?? '';
        const ofstedCode = parseInt(e.OfstedRating?.Code ?? e.OfstedRatingCode ?? '0', 10);
        const ofstedRating = ofstedCode >= 1 && ofstedCode <= 4 ? (ofstedCode as 1 | 2 | 3 | 4) : null;
        const pupils = parseInt(e.NumberOfPupils ?? '0', 10) || null;
        const capacity = parseInt(e.SchoolCapacity ?? '0', 10) || null;
        const capacityUtil = pupils && capacity ? Math.round((pupils / capacity) * 100) : null;
        const type = classifyType(phaseLabel, typeLabel);

        return {
          urn: e.URN?.toString() ?? e.Urn?.toString() ?? '',
          name: e.EstablishmentName ?? e.Name ?? 'Unknown',
          type,
          phase: phaseLabel,
          address: [e.Street, e.Town].filter(Boolean).join(', '),
          postcode: e.Postcode ?? '',
          lat: schoolLat,
          lng: schoolLng,
          ofstedRating,
          ofstedRatingLabel: ofstedLabel(ofstedRating),
          numberOfPupils: pupils,
          capacityUtil,
          distanceMiles: parseFloat(dist.toFixed(2)),
          isNursery: type === 'nursery',
        };
      })
      .filter((s): s is School => s !== null)
      .sort((a, b) => a.distanceMiles - b.distanceMiles);

    const trafficResult = computeTrafficRisk(schools);
    const within400m = schools.filter(s => s.distanceMiles <= 0.25).length;

    const summary: SchoolsResponse['summary'] = {
      totalSchools: schools.filter(s => !s.isNursery).length,
      totalNurseries: schools.filter(s => s.isNursery).length,
      trafficRisk: trafficResult.risk,
      trafficRiskReason: trafficResult.reason,
      within400m,
      outstanding: schools.filter(s => s.ofstedRating === 1).length,
      good: schools.filter(s => s.ofstedRating === 2).length,
    };

    return res.status(200).json({ schools, summary });
  } catch (err) {
    console.error('Schools API error:', err);
    // Return empty rather than erroring the whole page
    return res.status(200).json({
      schools: [],
      summary: {
        totalSchools: 0,
        totalNurseries: 0,
        trafficRisk: 'low',
        trafficRiskReason: 'Could not load school data.',
        within400m: 0,
        outstanding: 0,
        good: 0,
      },
    });
  }
}
