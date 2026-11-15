import { Link } from '@tanstack/react-router';
import { ArrowUpRight, Orbit } from 'lucide-react';
export function Header({ dark = false, compactBrand = false }: { dark?: boolean; compactBrand?: boolean }) {
  return <header className={`site-header ${dark ? 'dark-header' : ''}`}>
    {!compactBrand && <Link to="/" className="brand" aria-label="firesync home" title="firesync"><Orbit aria-hidden="true" /><span>firesync<span className="brand-period">.</span></span></Link>}
    <nav aria-label="Main navigation"><Link to="/explore" activeProps={{ className: 'nav-active' }}>Explore</Link><Link to="/method" activeProps={{ className: 'nav-active' }}>Method</Link><Link to="/data" activeProps={{ className: 'nav-active' }}>Data</Link></nav>
    <a className="firms-link" href="https://firms.modaps.eosdis.nasa.gov/" target="_blank" rel="noreferrer">NASA FIRMS <ArrowUpRight size={13} /></a>
  </header>;
}
export function Footer() { return <footer className="site-footer"><Link to="/" className="footer-brand">firesync.</Link><span>Data: NASA FIRMS. We acknowledge the use of data and imagery from LANCE FIRMS operated by NASA's Earth Science Data and Information System (ESDIS).</span><Link to="/method">Method</Link><Link to="/data">Data & credits</Link><span>NASA Space Apps · 2026</span></footer>; }