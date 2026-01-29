# Callbacks, State, and Guardrails

## Table of Contents
- [Callback Overview](#callback-overview)
- [Before Agent Callback](#before-agent-callback)
- [After Agent Callback](#after-agent-callback)
- [Before Model Callback](#before-model-callback)
- [After Model Callback](#after-model-callback)
- [Before/After Tool Callbacks](#beforeafter-tool-callbacks)
- [State Management](#state-management)
- [Session Management](#session-management)

## Callback Overview

Callbacks hook into an agent's execution at predefined checkpoints. They receive a `CallbackContext` and control flow via return values.

```
Before Agent → Before Model → [LLM Call] → After Model → Before Tool → [Tool Call] → After Tool → After Agent
```

**Return values:**
- `undefined` - Allow default behavior to proceed
- Return a specific object - Override and skip that step

```typescript
const agent = new LlmAgent({
  name: 'guarded_agent',
  model: 'gemini-2.5-flash',
  instruction: '...',
  beforeAgentCallback: checkIfAgentShouldRun,
  afterAgentCallback: modifyOutputAfterAgent,
  beforeModelCallback: simpleBeforeModelModifier,
  afterModelCallback: inspectModelResponse,
  beforeToolCallback: validateToolCall,
  afterToolCallback: transformToolResult,
});
```

## Before Agent Callback

Called before the agent processes a request. Return `Content` to skip agent logic entirely.

```typescript
import { CallbackContext } from '@google/adk';
import type { Content } from '@google/genai';

function checkIfAgentShouldRun(
  callbackContext: CallbackContext
): Content | undefined {
  const agentName = callbackContext.agentName;
  const currentState = callbackContext.state;

  console.log(`[Callback] Entering agent: ${agentName}`);

  if (currentState.get('skip_llm_agent') === true) {
    console.log(`[Callback] Skipping agent ${agentName}`);
    return {
      parts: [{ text: `Agent ${agentName} skipped due to state condition.` }],
      role: 'model',
    };
  }

  return undefined; // Proceed normally
}
```

## After Agent Callback

Called after the agent finishes. Return `Content` to replace agent output.

```typescript
function modifyOutputAfterAgent(context: CallbackContext): Content | undefined {
  const agentName = context.agentName;

  if (context.state.get('add_concluding_note') === true) {
    return {
      parts: [{ text: 'Concluding note added by callback.' }],
      role: 'model',
    };
  }

  return undefined; // Use original output
}
```

## Before Model Callback

Called before the LLM is invoked. Can modify the request or block the call entirely.

```typescript
function simpleBeforeModelModifier({
  context,
  request,
}: {
  context: CallbackContext;
  request: any;
}): any | undefined {
  console.log(`[Callback] Before model call for: ${context.agentName}`);

  // Inspect last user message
  const lastUserMessage = request.contents?.at(-1)?.parts?.[0]?.text ?? '';

  // Modify system instruction
  const modifiedConfig = JSON.parse(JSON.stringify(request.config));
  const originalInstruction =
    modifiedConfig.systemInstruction?.parts?.[0]?.text ?? '';
  modifiedConfig.systemInstruction = {
    role: 'system',
    parts: [{ text: `[Modified] ${originalInstruction}` }],
  };
  request.config = modifiedConfig;

  // Block if keyword detected
  if (lastUserMessage.toUpperCase().includes('BLOCK')) {
    return {
      content: {
        role: 'model',
        parts: [{ text: 'LLM call blocked by callback.' }],
      },
    };
  }

  return undefined; // Proceed with (possibly modified) request
}
```

## After Model Callback

Inspect or modify the LLM response.

```typescript
function inspectModelResponse({
  context,
  response,
}: {
  context: CallbackContext;
  response: any;
}): any | undefined {
  // Log response for monitoring
  console.log(`Model response for ${context.agentName}:`, response);

  // Optionally modify or replace response
  return undefined; // Use original response
}
```

## Before/After Tool Callbacks

Control tool execution.

```typescript
function validateToolCall({
  context,
  toolCall,
}: {
  context: CallbackContext;
  toolCall: any;
}): Record<string, unknown> | undefined {
  // Block dangerous operations
  if (toolCall.name === 'delete_file') {
    return { status: 'blocked', reason: 'Deletions require approval' };
  }
  return undefined; // Proceed with tool call
}

function transformToolResult({
  context,
  toolCall,
  result,
}: {
  context: CallbackContext;
  toolCall: any;
  result: any;
}): Record<string, unknown> | undefined {
  // Log or transform tool results
  context.state.set('temp:last_tool', toolCall.name);
  return undefined; // Use original result
}
```

## State Management

### State Prefixes

| Prefix | Scope | Persistence |
|--------|-------|-------------|
| (none) | Current session | Session lifetime |
| `user:` | Per user, all sessions | Across sessions |
| `app:` | Global, all users | Application-wide |
| `temp:` | Current invocation only | Discarded after invocation |

### Reading State

**In instructions (template injection):**
```typescript
const agent = new LlmAgent({
  instruction: 'The user prefers {user:language}. Topic is {topic}.',
  // {user:language} reads state['user:language']
});
```

**In callbacks/tools:**
```typescript
function myCallback(context: CallbackContext) {
  const lang = context.state.get('user:language', 'en');
  const count = context.state.get('counter', 0);
}
```

### Writing State

**Method 1: `outputKey` (recommended for agent output)**
```typescript
const agent = new LlmAgent({
  outputKey: 'draft', // Agent's text response → state['draft']
});
```

**Method 2: `CallbackContext.state` (recommended for callbacks/tools)**
```typescript
function myCallback(context: CallbackContext) {
  context.state.set('counter', 1);
  context.state.set('user:preference', 'dark');
  context.state.set('temp:scratch', 'temporary');
}
```

**Method 3: EventActions `stateDelta`**
```typescript
import { createEventActions, createEvent } from '@google/adk';

const stateChanges = {
  task_status: 'active',
  'user:login_count': 5,
  'temp:needs_validation': true,
};

const actions = createEventActions({ stateDelta: stateChanges });
const event = createEvent({
  invocationId: 'inv_1',
  author: 'system',
  actions,
  timestamp: Date.now(),
});

await sessionService.appendEvent({ session, event });
```

**Never** modify session state directly on a retrieved session object. Always use `CallbackContext.state`, `outputKey`, or `EventActions`.

## Session Management

### InMemorySessionService

For development and testing. Data lost on restart.

```typescript
import { InMemorySessionService } from '@google/adk';

const sessionService = new InMemorySessionService();

// Create session with initial state
const session = await sessionService.createSession({
  appName: 'my_app',
  userId: 'user-1',
  state: { initial_key: 'initial_value' },
});

console.log(session.id);        // Auto-generated UUID
console.log(session.appName);   // 'my_app'
console.log(session.userId);    // 'user-1'
console.log(session.state);     // { initial_key: 'initial_value' }
console.log(session.events);    // []

// Delete session
await sessionService.deleteSession({
  appName: session.appName,
  userId: session.userId,
  sessionId: session.id,
});
```

### InMemoryRunner

Convenience runner with built-in InMemorySessionService.

```typescript
import { InMemoryRunner, stringifyContent } from '@google/adk';
import { createUserContent } from '@google/genai';

const runner = new InMemoryRunner({ agent: rootAgent });

const session = await runner.sessionService.createSession({
  appName: runner.appName,
  userId: 'test-user',
});

const userMessage = createUserContent('What is the weather in Tokyo?');

for await (const event of runner.runAsync({
  userId: session.userId,
  sessionId: session.id,
  newMessage: userMessage,
})) {
  if (event?.content?.parts?.length) {
    console.log(stringifyContent(event));
  }
}
```

For production, use database-backed session services (Firestore, etc.).
