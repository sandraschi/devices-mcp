import { useLocation } from 'react-router-dom';

export function Placeholder() {
  const loc = useLocation();
  const name = loc.pathname.slice(1) || 'Page';
  return (
    <div className='space-y-6'>
      <h1 className='text-2xl font-bold tracking-tight'>
        {name ? name.replace(/\//g, ' · ') : 'Page'}
      </h1>
      <p className='text-slate-500'>This page is not implemented yet in the React app.</p>
    </div>
  );
}
