import { Outlet } from 'react-router-dom';
import { AppSidebar } from './AppSidebar';

export function Layout() {
  return (
    <div className='min-h-screen bg-slate-50 dark:bg-slate-950'>
      <AppSidebar />
      <main className='min-h-screen pl-64'>
        <div className='min-h-screen overflow-y-auto overflow-x-hidden p-6'>
          <Outlet />
        </div>
      </main>
    </div>
  );
}
