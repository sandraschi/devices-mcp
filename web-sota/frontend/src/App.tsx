import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { Dashboard } from '@/pages/Dashboard'
import { Cameras } from '@/pages/Cameras'
import { Energy } from '@/pages/Energy'
import { Ring } from '@/pages/Ring'
import { Plex } from '@/pages/Plex'
import { Logs } from '@/pages/Logs'
import { Lighting } from '@/pages/Lighting'
import { Robots } from '@/pages/Robots'
import { Settings } from '@/pages/Settings'
import { Weather } from '@/pages/Weather'
import { Health } from '@/pages/Health'
import { HumanHealth } from '@/pages/HumanHealth'
import { Alarms } from '@/pages/Alarms'
import { Onboarding } from '@/pages/Onboarding'
import { Chat } from '@/pages/Chat'
import { LLMStack } from '@/pages/LLMStack'
import { Placeholder } from '@/pages/Placeholder'
import { McpCapabilities } from '@/pages/McpCapabilities'

function App() {
  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="cameras" element={<Cameras />} />
          <Route path="plex" element={<Plex />} />
          <Route path="energy" element={<Energy />} />
          <Route path="weather" element={<Weather />} />
          <Route path="logs" element={<Logs />} />
          <Route path="lighting" element={<Lighting />} />
          <Route path="robots" element={<Robots />} />
          <Route path="ring" element={<Ring />} />
          <Route path="health" element={<Health />} />
          <Route path="human-health" element={<HumanHealth />} />
          <Route path="alarms" element={<Alarms />} />
          <Route path="onboarding" element={<Onboarding />} />
          <Route path="chat" element={<Chat />} />
          <Route path="llm" element={<LLMStack />} />
          <Route path="mcp-capabilities" element={<McpCapabilities />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Placeholder />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
