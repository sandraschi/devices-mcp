import { Layout } from '@/components/layout/Layout';
import { Alarms } from '@/pages/Alarms';
import { Cameras } from '@/pages/Cameras';
import { Chat } from '@/pages/Chat';
import { Dashboard } from '@/pages/Dashboard';
import { Energy } from '@/pages/Energy';
import { Health } from '@/pages/Health';
import { HumanHealth } from '@/pages/HumanHealth';
import { LLMStack } from '@/pages/LLMStack';
import { Lighting } from '@/pages/Lighting';
import { Logs } from '@/pages/Logs';
import { McpCapabilities } from '@/pages/McpCapabilities';
import { Nest } from '@/pages/Nest';
import { Onboarding } from '@/pages/Onboarding';
import { Placeholder } from '@/pages/Placeholder';
import { Plex } from '@/pages/Plex';
import { Ring } from '@/pages/Ring';
import { Robots } from '@/pages/Robots';
import { Settings } from '@/pages/Settings';
import { Shelly } from '@/pages/Shelly';
import { Weather } from '@/pages/Weather';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter basename='/app'>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path='cameras' element={<Cameras />} />
          <Route path='plex' element={<Plex />} />
          <Route path='energy' element={<Energy />} />
          <Route path='weather' element={<Weather />} />
          <Route path='logs' element={<Logs />} />
          <Route path='lighting' element={<Lighting />} />
          <Route path='robots' element={<Robots />} />
          <Route path='ring' element={<Ring />} />
          <Route path='nest' element={<Nest />} />
          <Route path='shelly' element={<Shelly />} />
          <Route path='health' element={<Health />} />
          <Route path='human-health' element={<HumanHealth />} />
          <Route path='alarms' element={<Alarms />} />
          <Route path='onboarding' element={<Onboarding />} />
          <Route path='chat' element={<Chat />} />
          <Route path='llm' element={<LLMStack />} />
          <Route path='mcp-capabilities' element={<McpCapabilities />} />
          <Route path='settings' element={<Settings />} />
          <Route path='*' element={<Placeholder />} />
        </Route>
        <Route path='*' element={<Navigate to='/' replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
