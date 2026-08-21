import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export const runtime = 'nodejs';
export const dynamic = 'force-static';
export const revalidate = 3600; // 1 hour ISR

export async function GET() {
  try {
    const filePath = path.join(process.cwd(), 'public', 'data', 'delhi_current_grid.json');
    
    if (!fs.existsSync(filePath)) {
      // Fallback if data hasn't been generated yet
      return NextResponse.json(
        { error: 'Grid data snapshot is being generated. Please retry shortly.' },
        { status: 503 }
      );
    }

    const fileContent = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(fileContent);

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=3600, stale-while-revalidate=86400',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      { error: 'Failed to read grid telemetry', details: error.message },
      { status: 500 }
    );
  }
}
