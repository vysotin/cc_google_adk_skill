# Testing and Evaluation

## Table of Contents
- [Overview](#overview)
- [Test File Format](#test-file-format)
- [Running Evaluations](#running-evaluations)
- [Evaluation Metrics](#evaluation-metrics)
- [Programmatic Testing](#programmatic-testing)
- [Best Practices](#best-practices)

## Overview

ADK evaluation focuses on:
1. **Trajectory** - Did the agent call the right tools in the right order?
2. **Final Response** - Is the output correct and useful?
3. **Safety** - Is the response safe and grounded?

Traditional pass/fail tests are insufficient for LLM agents due to non-deterministic behavior. ADK uses qualitative evaluation of both outputs and execution trajectories.

## Test File Format

Create `<agent_name>.test.json` alongside your agent:

```json
{
  "name": "weather_agent_tests",
  "description": "Tests for weather agent",
  "data": [
    {
      "name": "basic_weather_query",
      "query": "What's the weather in New York?",
      "expected_tool_calls": ["get_weather"],
      "expected_tool_args": {
        "get_weather": { "city": "New York" }
      },
      "reference_answer": "The weather in New York"
    },
    {
      "name": "multi_city",
      "query": "Compare weather in NYC and LA",
      "expected_tool_calls": ["get_weather", "get_weather"],
      "reference_answer": "comparison"
    },
    {
      "name": "no_tool_needed",
      "query": "What tools can you use?",
      "expected_tool_calls": [],
      "reference_answer": "I can check weather"
    }
  ]
}
```

**Fields:**
- `name` - Test case identifier
- `query` - User input to test
- `expected_tool_calls` - List of tool names in expected order
- `expected_tool_args` - Optional: expected arguments per tool
- `reference_answer` - Expected content (partial/semantic match)

## Running Evaluations

### CLI

```bash
# Run specific test file
npx adk eval <path_to_agent_folder> <path_to_test_file.test.json>

# Example
npx adk eval ./my-agent ./my-agent/weather.test.json
```

### Dev UI

```bash
npx @google/adk-devtools web
# Navigate to agent → Tests tab
# Run tests interactively
# Inspect events, state changes, tool calls
```

## Evaluation Metrics

### Built-in Metrics

| Metric | Description |
|--------|-------------|
| `tool_trajectory_avg_score` | Exact match of tool call sequence |
| `response_match_score` | ROUGE-1 similarity to reference |
| `final_response_match_v2` | LLM-judged semantic equivalence |
| `rubric_based_final_response_quality_v1` | Custom quality rubrics |
| `rubric_based_tool_use_quality_v1` | Tool usage assessment |
| `hallucinations_v1` | Groundedness validation |
| `safety_v1` | Harmlessness checking |

### Configuring Metrics

```json
{
  "name": "comprehensive_test",
  "metrics": [
    "tool_trajectory_avg_score",
    "response_match_score",
    "safety_v1"
  ],
  "thresholds": {
    "tool_trajectory_avg_score": 0.9,
    "response_match_score": 0.7
  },
  "data": [...]
}
```

## Programmatic Testing

### With InMemoryRunner

```typescript
import { InMemoryRunner, isFinalResponse } from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';

async function testAgent(query: string, expectedTools: string[]) {
  const runner = new InMemoryRunner({ agent: rootAgent });
  const session = await runner.sessionService.createSession({
    appName: runner.appName,
    userId: 'test-user',
  });

  const toolsCalled: string[] = [];
  let finalResponse = '';

  for await (const event of runner.runAsync({
    userId: session.userId,
    sessionId: session.id,
    newMessage: createUserContent(query),
  })) {
    // Track tool calls
    if (event?.content?.parts) {
      for (const part of event.content.parts) {
        if ('functionCall' in part) {
          toolsCalled.push(part.functionCall.name);
        }
      }
    }
    // Capture final response
    if (isFinalResponse(event)) {
      finalResponse = event.content?.parts?.[0]?.text ?? '';
    }
  }

  // Assert tool trajectory
  console.assert(
    JSON.stringify(toolsCalled) === JSON.stringify(expectedTools),
    `Expected tools ${expectedTools}, got ${toolsCalled}`
  );

  return { toolsCalled, finalResponse };
}

// Run tests
await testAgent('Weather in NYC?', ['get_weather']);
await testAgent('Hello', []);
```

### With Vitest

```typescript
// agent.test.ts
import { describe, it, expect } from 'vitest';
import { InMemoryRunner, isFinalResponse } from '@google/adk';
import { createUserContent } from '@google/genai';
import { rootAgent } from './agent.js';

describe('Weather Agent', () => {
  let runner: InMemoryRunner;

  beforeEach(() => {
    runner = new InMemoryRunner({ agent: rootAgent });
  });

  it('should call get_weather for weather queries', async () => {
    const session = await runner.sessionService.createSession({
      appName: runner.appName,
      userId: 'test',
    });

    const toolsCalled: string[] = [];
    for await (const event of runner.runAsync({
      userId: 'test',
      sessionId: session.id,
      newMessage: createUserContent("What's the weather in Tokyo?"),
    })) {
      for (const part of event?.content?.parts ?? []) {
        if ('functionCall' in part) {
          toolsCalled.push(part.functionCall.name);
        }
      }
    }

    expect(toolsCalled).toContain('get_weather');
  });

  it('should not call tools for greeting', async () => {
    const session = await runner.sessionService.createSession({
      appName: runner.appName,
      userId: 'test',
    });

    const toolsCalled: string[] = [];
    for await (const event of runner.runAsync({
      userId: 'test',
      sessionId: session.id,
      newMessage: createUserContent('Hello!'),
    })) {
      for (const part of event?.content?.parts ?? []) {
        if ('functionCall' in part) {
          toolsCalled.push(part.functionCall.name);
        }
      }
    }

    expect(toolsCalled).toHaveLength(0);
  });
});
```

**Run:** `npx vitest run`

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Agent Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: npm ci
      - run: npx vitest run
      - run: npx adk eval ./my-agent ./my-agent/tests.test.json
```

## Best Practices

1. **Test tool sequences, not just outputs** - Verify the agent reasons correctly
2. **Include edge cases** - Empty inputs, ambiguous queries, invalid data
3. **Test state persistence** - Verify state flows across sequential agents
4. **Use semantic matching** - Exact string matching is too brittle for LLM output
5. **Version test data** - Track test evolution alongside agent changes
6. **Test each orchestration pattern** - Verify sequential, parallel, loop behaviors

### Coverage Checklist

```markdown
- [ ] Happy path for each tool
- [ ] Tool selection with ambiguous input
- [ ] Multi-tool sequences
- [ ] Error recovery (tool failures)
- [ ] Edge cases (empty, null, large inputs)
- [ ] Multi-turn conversations
- [ ] State persistence across turns
- [ ] Parallel agent state isolation
- [ ] Loop agent exit conditions
```
