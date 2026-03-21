/* ════════════════════════════════════════════════════════════════
   CHAT STATUS API — GET /api/chat/status
   Returns whether the LLM API key is configured
   ════════════════════════════════════════════════════════════════ */

import { isLLMConfigured } from '@/app/lib/config';

export async function GET() {
  return Response.json({ configured: isLLMConfigured() });
}
