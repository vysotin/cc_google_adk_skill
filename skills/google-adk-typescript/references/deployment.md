# Deployment

## Table of Contents
- [Express Backend](#express-backend)
- [Hono Backend](#hono-backend)
- [Cloud Run Deployment](#cloud-run-deployment)
- [Docker Container](#docker-container)
- [Production Checklist](#production-checklist)

## Express Backend

Production API server using Express.

```typescript
import express from 'express';
import cors from 'cors';
import {
  InMemoryRunner,
  isFinalResponse,
  stringifyContent,
} from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';

const app = express();
app.use(express.json());
app.use(cors({ origin: 'http://localhost:3000' }));

const runner = new InMemoryRunner({ agent: rootAgent });

interface ChatRequest {
  message: string;
  sessionId: string;
  userId?: string;
}

async function getOrCreateSession(userId: string, sessionId: string) {
  const existing = await runner.sessionService.getSession({
    appName: runner.appName,
    userId,
    sessionId,
  });
  if (existing) return existing;
  return runner.sessionService.createSession({
    appName: runner.appName,
    userId,
  });
}

app.post('/chat', async (req, res) => {
  const { message, sessionId, userId = 'default' } = req.body as ChatRequest;

  const session = await getOrCreateSession(userId, sessionId);

  const events = [];
  for await (const event of runner.runAsync({
    userId,
    sessionId: session.id,
    newMessage: createUserContent(message),
  })) {
    if (isFinalResponse(event)) {
      events.push({
        type: 'response',
        content: stringifyContent(event),
      });
    }
  }

  res.json({ events });
});

// SSE streaming endpoint
app.get('/chat/stream', async (req, res) => {
  const { message, sessionId, userId = 'default' } = req.query as Record<string, string>;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const session = await getOrCreateSession(userId, sessionId);

  for await (const event of runner.runAsync({
    userId,
    sessionId: session.id,
    newMessage: createUserContent(message),
  })) {
    if (event?.content?.parts?.length) {
      res.write(`data: ${JSON.stringify(event)}\n\n`);
    }
  }

  res.write('data: [DONE]\n\n');
  res.end();
});

app.get('/health', (_req, res) => res.json({ status: 'healthy' }));

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
```

**Note:** `createUserContent` comes from `@google/genai`, not `@google/adk`. Use `.js` extension in imports for ESM module resolution.

**Dependencies:** `npm install express cors @google/adk @google/genai`

## Hono Backend

Lightweight, fast alternative to Express. Runs on Node.js, Bun, Deno, and edge runtimes.

```typescript
import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { streamSSE } from 'hono/streaming';
import {
  InMemoryRunner,
  isFinalResponse,
  stringifyContent,
} from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';

const app = new Hono();
app.use('/*', cors());

const runner = new InMemoryRunner({ agent: rootAgent });

app.post('/chat', async (c) => {
  const { message, sessionId, userId = 'default' } = await c.req.json();

  let session = await runner.sessionService.getSession({
    appName: runner.appName, userId, sessionId,
  });
  if (!session) {
    session = await runner.sessionService.createSession({
      appName: runner.appName, userId,
    });
  }

  const events = [];
  for await (const event of runner.runAsync({
    userId,
    sessionId: session.id,
    newMessage: createUserContent(message),
  })) {
    if (isFinalResponse(event)) {
      events.push({ type: 'response', content: stringifyContent(event) });
    }
  }

  return c.json({ events });
});

app.get('/chat/stream', (c) => {
  const message = c.req.query('message') ?? '';
  const sessionId = c.req.query('sessionId') ?? '';
  const userId = c.req.query('userId') ?? 'default';

  return streamSSE(c, async (stream) => {
    let session;
    try {
      session = await runner.sessionService.getSession({
        appName: runner.appName, userId, sessionId,
      });
    } catch {
      session = await runner.sessionService.createSession({
        appName: runner.appName, userId, sessionId,
      });
    }

    for await (const event of runner.runAsync({
      userId,
      sessionId: session.id,
      newMessage: createUserContent(message),
    })) {
      if (event?.content?.parts?.length) {
        await stream.writeSSE({ data: JSON.stringify(event) });
      }
    }

    await stream.writeSSE({ data: '[DONE]' });
  });
});

app.get('/health', (c) => c.json({ status: 'healthy' }));

export default app;
```

**Run with Node.js:** Add `serve` from `@hono/node-server`:
```typescript
import { serve } from '@hono/node-server';
serve({ fetch: app.fetch, port: 8080 });
```

**Dependencies:** `npm install hono @hono/node-server @google/adk`

## Cloud Run Deployment

### ADK CLI Deploy

```bash
# Deploy directly from agent directory
npx adk deploy cloud_run ./my-agent \
  --project my-gcp-project \
  --region us-central1

# With options
npx adk deploy cloud_run ./my-agent \
  --project my-gcp-project \
  --region us-central1 \
  --port 8000 \
  --with_ui  # Include dev UI (not for production)
```

### Manual Deployment with Dockerfile

**Dockerfile (multi-stage build):**
```dockerfile
FROM node:20-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npx tsc

FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/dist ./dist

EXPOSE 8080

CMD ["node", "dist/server.js"]
```

**Note:** A multi-stage build is required because `tsc` needs `typescript` (a devDependency). The builder stage compiles, then the production stage only includes runtime dependencies.

**Deploy:**
```bash
gcloud run deploy my-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_API_KEY=${GOOGLE_GENAI_API_KEY}"
```

### Cloud Build

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/my-agent', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/my-agent']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'my-agent'
      - '--image'
      - 'gcr.io/$PROJECT_ID/my-agent'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'

images:
  - 'gcr.io/$PROJECT_ID/my-agent'
```

## Docker Container

### docker-compose.yaml

```yaml
version: '3.8'
services:
  agent:
    build: .
    ports:
      - "8080:8080"
    environment:
      - GOOGLE_GENAI_API_KEY=${GOOGLE_GENAI_API_KEY}
      - NODE_ENV=production

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### package.json Scripts

```json
{
  "scripts": {
    "build": "tsc",
    "start": "node dist/server.js",
    "dev": "npx @google/adk-devtools web",
    "eval": "npx adk eval . ./tests.test.json",
    "deploy": "gcloud run deploy my-agent --source . --region us-central1"
  }
}
```

## Production Checklist

### Pre-Deployment

- [ ] **Session persistence** - Use database-backed SessionService, not InMemory
- [ ] **API keys** - Use Secret Manager, not environment variables
- [ ] **Rate limiting** - Protect against abuse
- [ ] **Input validation** - Sanitize user inputs before passing to agent
- [ ] **Error handling** - Wrap runner calls in try/catch
- [ ] **CORS** - Restrict origins to your frontend domains

### Security

- [ ] **Authentication** - Verify user identity before agent access
- [ ] **Authorization** - Check permissions per tool/agent
- [ ] **Audit logging** - Log all agent actions and tool calls
- [ ] **PII handling** - Redact sensitive data in logs
- [ ] **SecurityPlugin** - Use for tool approval workflows

### Reliability

- [ ] **Health checks** - `/health` endpoint for load balancers
- [ ] **Graceful shutdown** - Handle SIGTERM for Cloud Run
- [ ] **Timeouts** - Set appropriate limits on agent runs
- [ ] **Error responses** - Return structured error JSON

### Monitoring

- [ ] **Structured logging** - JSON logs with request IDs
- [ ] **Metrics** - Track latency, error rate, tool usage
- [ ] **Tracing** - Correlate requests across services
- [ ] **Alerting** - On error spikes or latency degradation
