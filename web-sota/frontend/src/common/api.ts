export interface CapabilitiesResponse {
  status: string;
  server?: {
    name: string;
    version: string;
    fastmcp: string;
  };
  tool_surface?: {
    total: number;
    portmanteau_count: number;
    atomic_count: number;
    portmanteau_tools: string[];
    atomic_tools: string[];
  };
  features?: {
    sampling: boolean;
    agentic_workflows: boolean;
    prompts: boolean;
    resources: boolean;
    skills: boolean;
  };
  inventory?: {
    workflow_tools: string[];
    sampling_indicator_tools?: string[];
    prompt_names: string[];
    resource_uris: string[];
    skill_uris: string[];
  };
  runtime?: {
    transport: string;
    surface_mode: string;
    tool_mode_env?: string;
  };
  timestamp?: string;
  error?: string;
}

export async function getCapabilities(): Promise<CapabilitiesResponse> {
  const r = await fetch('/api/capabilities');
  if (!r.ok) {
    throw new Error(`Capabilities request failed: ${r.status}`);
  }
  return r.json();
}
