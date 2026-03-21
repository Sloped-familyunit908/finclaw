/* ════════════════════════════════════════════════════════════════
   CHAT API — POST /api/chat
   Streaming proxy to any OpenAI-compatible LLM API
   ════════════════════════════════════════════════════════════════ */

import { NextRequest } from 'next/server';
import { getConfig } from '@/app/lib/config';

const SYSTEM_PROMPT = `You are FinClaw AI, a professional financial research assistant.
You help users analyze stocks, compare investments, and understand markets.

Rules:
- Be concise and data-driven
- Never predict specific prices or guarantee returns
- Always disclaim that this is not financial advice
- Use professional tone, no emoji
- If asked about a specific stock, provide technical and fundamental analysis
- Format numbers properly ($, %, etc.)
- When comparing assets, use structured formats
- Cite data sources when possible

Available context:
- The user is using the FinClaw quantitative research platform
- They may reference stocks, crypto, or Chinese A-share markets`;

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export async function POST(req: NextRequest) {
  const apiKey = process.env.FINCLAW_LLM_API_KEY;

  if (!apiKey) {
    return Response.json(
      {
        error: 'llm_not_configured',
        message: 'Add FINCLAW_LLM_API_KEY to .env.local to enable AI chat.',
      },
      { status: 403 }
    );
  }

  let messages: ChatMessage[];
  try {
    const body = await req.json();
    messages = body.messages;
    if (!Array.isArray(messages) || messages.length === 0) {
      return Response.json(
        { error: 'invalid_request', message: 'messages array is required.' },
        { status: 400 }
      );
    }
  } catch {
    return Response.json(
      { error: 'invalid_request', message: 'Invalid JSON body.' },
      { status: 400 }
    );
  }

  const config = getConfig();
  const baseUrl = config.llm?.baseUrl || 'https://api.openai.com/v1';
  const model = config.llm?.model || 'gpt-4o-mini';

  try {
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [{ role: 'system', content: SYSTEM_PROMPT }, ...messages],
        stream: true,
      }),
    });

    if (!response.ok) {
      const status = response.status;
      let detail = '';
      try {
        const errBody = await response.text();
        detail = errBody.slice(0, 200);
      } catch {
        // ignore parse error
      }

      if (status === 401) {
        return Response.json(
          { error: 'invalid_api_key', message: 'The configured API key is invalid.' },
          { status: 401 }
        );
      }
      if (status === 429) {
        return Response.json(
          { error: 'rate_limited', message: 'API rate limit exceeded. Please wait a moment.' },
          { status: 429 }
        );
      }

      return Response.json(
        { error: 'upstream_error', message: `LLM API returned ${status}: ${detail}` },
        { status: 502 }
      );
    }

    // Stream the upstream SSE body directly to the client
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : 'Unknown error connecting to LLM API';
    return Response.json(
      { error: 'network_error', message },
      { status: 502 }
    );
  }
}
