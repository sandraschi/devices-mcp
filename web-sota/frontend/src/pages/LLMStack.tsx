import { Navigate } from 'react-router-dom';

/** Local LLM setup lives under Settings → Local LLM. */
export function LLMStack() {
  return <Navigate to='/settings#local-llm' replace />;
}
