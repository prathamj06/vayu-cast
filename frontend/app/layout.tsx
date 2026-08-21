import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'VAYU — Urban Air Quality Intelligence Platform | NCT Delhi',
  description: 'Real-time 72-hour hyperlocal air quality forecast and health advisory intelligence for the National Capital Territory of Delhi, powered by XGBoost, Uber H3 WebGL meshes, and Gemini AI.',
  keywords: ['AQI', 'Delhi', 'Air Quality', 'XGBoost', 'DeckGL', 'MapLibre', 'Gemini AI', 'CPCB'],
  authors: [{ name: 'VayuCast Engineering Team' }],
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="stylesheet"
          href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"
        />
      </head>
      <body className="bg-[#080c14] text-slate-100 antialiased h-screen w-screen overflow-hidden">
        {children}
      </body>
    </html>
  );
}
