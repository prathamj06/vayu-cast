import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';
export const revalidate = 3600; // 1 hour ISR

const REMOTE_DATA_BRANCH_URL = 'https://raw.githubusercontent.com/prathamj06/vayu-cast/data/delhi_current_grid.json';

export async function GET() {
  try {
    // 1. Try fetching latest live single-commit snapshot from GitHub 'data' branch
    try {
      const response = await fetch(REMOTE_DATA_BRANCH_URL, {
        next: { revalidate: 3600 },
        headers: { 'User-Agent': 'VayuCast-Edge-Service' },
      });

      if (response.ok) {
        const remoteData = await response.json();
        return NextResponse.json(remoteData, {
          headers: {
            'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
            'Access-Control-Allow-Origin': '*',
          },
        });
      }
    } catch (fetchErr) {
      console.warn('Could not fetch from remote data branch, falling back to local snapshot:', fetchErr);
    }

    // 2. Fallback to local pre-compiled static snapshot
    const filePath = path.join(process.cwd(), 'public', 'data', 'delhi_current_grid.json');
    if (fs.existsSync(filePath)) {
      const fileContent = fs.readFileSync(filePath, 'utf-8');
      const localData = JSON.parse(fileContent);

      return NextResponse.json(localData, {
        headers: {
          'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    return NextResponse.json(
      { error: 'Grid data snapshot is being initialized. Please retry shortly.' },
      { status: 503 }
    );
  } catch (error: any) {
    return NextResponse.json(
      { error: 'Failed to read grid telemetry', details: error.message },
      { status: 500 }
    );
  }
}
