import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { Footer } from '@/components/firesync/Shell';
import { MapOpening } from '@/components/firesync/MapOpening';
import { Explorer } from '@/components/firesync/Explorer';
import { useEffect, useState } from 'react';
import type { AreaSelection } from '@/components/firesync/AreaMap';
import earthAsset from '@/assets/earth-fast.jpg.asset.json';

export const Route = createFileRoute('/')({ head: () => ({ links: [{ rel: 'preload', as: 'image', href: earthAsset.url, fetchPriority: 'high', crossOrigin: 'anonymous' }], meta: [{ title: 'firesync — Two satellites. One fire history.' }, { name: 'description', content: 'Explore a harmonized record of fire detections since 2003. Compare recent activity with what is typical for a place and season.' }, { property: 'og:title', content: 'firesync — Two satellites. One fire history.' }, { property: 'og:description', content: 'A scientific atlas of monthly fire detections, seasonal patterns and recent activity.' }, { property: 'og:type', content: 'website' }, { name: 'twitter:card', content: 'summary_large_image' }] }), component: Index });
function Index() {
  const [selection, setSelection] = useState<AreaSelection | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    // A fresh opening starts with the globe; in-page record links still work afterwards.
    void navigate({ to: '/', hash: '', replace: true, resetScroll: true }).then(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  }, [navigate]);
  return <><MapOpening selection={selection} onSelect={setSelection} /><Explorer selection={selection} onSelect={setSelection} hideMap /><Footer /></>;
}
