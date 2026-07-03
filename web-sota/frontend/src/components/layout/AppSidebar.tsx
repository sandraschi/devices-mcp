import { cn } from '@/lib/utils';
import {
  Activity,
  Bell,
  Bot,
  CloudRain,
  FileText,
  Flame,
  Heart,
  LayoutDashboard,
  Lightbulb,
  MessageCircle,
  Moon,
  Play,
  Puzzle,
  Rocket,
  Settings,
  Shield,
  Sun,
  Video,
  Zap,
} from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/cameras', label: 'Cameras', icon: Video },
  { to: '/plex', label: 'Plex Media', icon: Play },
  { to: '/energy', label: 'Energy', icon: Zap },
  { to: '/weather', label: 'Weather', icon: CloudRain },
  { to: '/logs', label: 'Log Management', icon: FileText },
  { to: '/lighting', label: 'Lighting', icon: Lightbulb },
  { to: '/robots', label: 'Robots', icon: Bot },
  { to: '/ring', label: 'Ring Doorbell', icon: Bell },
  { to: '/sensor-health', label: 'Sensor Health', icon: Activity },
  { to: '/nest', label: 'Nest Protect', icon: Flame },
  { to: '/health', label: 'Status', icon: Activity },
  { to: '/human-health', label: 'Human Health', icon: Heart },
  { to: '/alarms', label: 'Alarms', icon: Shield },
  { to: '/onboarding', label: 'Onboarding', icon: Rocket },
  { to: '/chat', label: 'Chat', icon: MessageCircle },
  { to: '/mcp-capabilities', label: 'MCP Capabilities', icon: Puzzle },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function AppSidebar() {
  const location = useLocation();

  return (
    <aside className='fixed left-0 top-0 z-40 h-screen w-64 border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950'>
      <div className='flex h-full flex-col'>
        <div className='flex h-14 items-center border-b border-slate-200 px-4 dark:border-slate-800'>
          <span className='text-lg font-semibold'>Devices MCP</span>
        </div>
        <nav className='flex-1 space-y-0.5 overflow-y-auto p-2'>
          {nav.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                location.pathname === to || (to !== '/' && location.pathname.startsWith(to))
                  ? 'bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-50'
                  : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-50',
              )}
            >
              <Icon className='h-5 w-5 shrink-0' />
              {label}
            </Link>
          ))}
        </nav>
        <div className='flex items-center justify-center border-t border-slate-200 p-3 dark:border-slate-800'>
          <button
            type='button'
            onClick={() => {
              const html = document.documentElement;
              html.classList.toggle('dark');
              localStorage.setItem('theme', html.classList.contains('dark') ? 'dark' : 'light');
            }}
            className='flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-50'
            aria-label='Toggle dark mode'
          >
            <Sun className='h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0' />
            <Moon className='absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100' />
            <span className='hidden dark:inline'>Dark</span>
            <span className='dark:hidden'>Light</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
