# Tool Development Guide

## Table of Contents
- [FunctionTool with Zod](#functiontool-with-zod)
- [LongRunningFunctionTool](#longrunningfunctiontool)
- [Built-in Tools](#built-in-tools)
- [MCP Tools](#mcp-tools)
- [OpenAPI Tools](#openapi-tools)
- [Tool Best Practices](#tool-best-practices)

## FunctionTool with Zod

Define tools with `FunctionTool`, using Zod for type-safe parameter schemas.

### Basic Tool

```typescript
import { FunctionTool, LlmAgent } from '@google/adk';
import { z } from 'zod';

const getStockPrice = new FunctionTool({
  name: 'get_stock_price',
  description: 'Get the current price of a stock.',
  parameters: z.object({
    ticker: z.string().describe('Stock ticker symbol (e.g., GOOGL, AAPL)'),
  }),
  execute: async ({ ticker }) => {
    const price = (Math.random() * 1000).toFixed(2);
    return { ticker, price: `$${price}` };
  },
});

const agent = new LlmAgent({
  name: 'stock_agent',
  model: 'gemini-2.5-flash',
  instruction: 'You can get stock prices.',
  tools: [getStockPrice],
});
```

### Complex Parameters

```typescript
const searchProducts = new FunctionTool({
  name: 'search_products',
  description: 'Search the product catalog.',
  parameters: z.object({
    query: z.string().describe('Search terms (e.g., "wireless headphones")'),
    category: z.enum(['electronics', 'clothing', 'home'])
      .optional()
      .describe('Category filter'),
    maxResults: z.number()
      .min(1).max(50)
      .default(10)
      .describe('Maximum results to return'),
    inStock: z.boolean()
      .optional()
      .describe('Filter to in-stock items only'),
  }),
  execute: async ({ query, category, maxResults, inStock }) => {
    // Implementation
    return { results: [], total: 0 };
  },
});
```

### Tool with ToolContext

Access session state and agent context within a tool:

```typescript
import { FunctionTool, ToolContext } from '@google/adk';
import { z } from 'zod';

const savePreference = new FunctionTool({
  name: 'save_preference',
  description: 'Save a user preference.',
  parameters: z.object({
    key: z.string().describe('Preference key'),
    value: z.string().describe('Preference value'),
  }),
  execute: async ({ key, value }, context: ToolContext) => {
    context.state.set(`user:pref_${key}`, value);
    return { status: 'saved', key, value };
  },
});
```

### Return Value Handling

Return a `Record<string, unknown>` for structured responses. Other return types are auto-wrapped into `{ result: <value> }`.

```typescript
// Good: structured object
execute: async ({ city }) => {
  return { city, temp: 72, unit: 'F', condition: 'sunny' };
}

// Also works: string (auto-wrapped to { result: "..." })
execute: async ({ city }) => {
  return `Temperature in ${city} is 72F`;
}
```

## LongRunningFunctionTool

For operations requiring user approval or external confirmation.

```typescript
import { LongRunningFunctionTool } from '@google/adk';
import { z } from 'zod';

const askForApproval = new LongRunningFunctionTool({
  name: 'ask_for_approval',
  description: 'Request approval for a reimbursement.',
  parameters: z.object({
    purpose: z.string().describe('Purpose of the reimbursement'),
    amount: z.number().describe('Amount to reimburse'),
  }),
  execute: async ({ purpose, amount }) => {
    // Initial execution - returns pending status
    return {
      status: 'pending',
      message: `Approval requested: ${purpose} for $${amount}`,
    };
  },
});
```

Use with `SecurityPlugin` and `BasePolicyEngine` for human-in-the-loop patterns:

```typescript
import { BasePolicyEngine, SecurityPlugin, LlmAgent } from '@google/adk';

class ApprovalPolicy extends BasePolicyEngine {
  async evaluate(toolCall: any) {
    return PolicyOutcome.CONFIRM; // Force user confirmation
  }
}

const agent = new LlmAgent({
  name: 'expense_agent',
  model: 'gemini-2.5-flash',
  tools: [askForApproval],
  plugins: [new SecurityPlugin({ policyEngine: new ApprovalPolicy() })],
});
```

## Built-in Tools

### Google Search

```typescript
import { LlmAgent, GOOGLE_SEARCH } from '@google/adk';

const agent = new LlmAgent({
  name: 'search_agent',
  model: 'gemini-2.5-flash',
  instruction: 'Search the web for information.',
  tools: [GOOGLE_SEARCH],
});
```

### Code Execution

```typescript
import { LlmAgent, CODE_EXECUTION } from '@google/adk';

const agent = new LlmAgent({
  name: 'coder',
  model: 'gemini-2.5-flash',
  tools: [CODE_EXECUTION],  // Sandboxed code execution
});
```

**Note:** Some built-in tools cannot be combined with other tools in the same agent. Check documentation for specific constraints.

## MCP Tools

Connect Model Context Protocol servers as tool providers.

### Local MCP Server

```typescript
import { MCPToolset } from '@google/adk';

const mcpTools = await MCPToolset.fromServer({
  command: 'npx',
  args: ['-y', '@anthropic/mcp-server-filesystem', '/path/to/dir'],
});

const agent = new LlmAgent({
  name: 'file_agent',
  model: 'gemini-2.5-flash',
  tools: [mcpTools],
});
```

### Remote MCP Server (SSE)

```typescript
const mcpTools = await MCPToolset.fromSSE('http://mcp-server:8080/sse');
```

## OpenAPI Tools

Generate tools from OpenAPI specifications.

```typescript
import { OpenAPIToolset } from '@google/adk';

// From URL
const apiTools = await OpenAPIToolset.fromUrl(
  'https://api.example.com/openapi.json',
  { auth: { apiKey: 'xxx' } }
);

// From file
const apiTools = await OpenAPIToolset.fromFile('./api_spec.yaml');

const agent = new LlmAgent({
  name: 'api_agent',
  model: 'gemini-2.5-flash',
  tools: [apiTools],
});
```

## Tool Best Practices

### 1. Always Use `.describe()` on Zod Fields

The LLM reads Zod descriptions to understand parameters:

```typescript
// Good
z.object({
  city: z.string().describe('City name like "New York" or "London"'),
  unit: z.enum(['celsius', 'fahrenheit']).describe('Temperature unit'),
})

// Bad - LLM has no context about what these parameters mean
z.object({
  city: z.string(),
  unit: z.enum(['celsius', 'fahrenheit']),
})
```

### 2. Write Clear Tool Descriptions

```typescript
// Good
new FunctionTool({
  name: 'delete_user_account',
  description: 'Permanently delete a user account and all associated data. This action cannot be undone.',
  // ...
});

// Bad
new FunctionTool({
  name: 'delete',
  description: 'Delete something.',
  // ...
});
```

### 3. Return Structured Objects

```typescript
// Good: clear structure helps LLM interpret results
return {
  status: 'success',
  data: { temperature: 72, unit: 'F' },
  source: 'weather-api',
};

// Bad: unstructured string
return 'The temperature is 72F';
```

### 4. Handle Errors in Return Values

```typescript
execute: async ({ url }) => {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return { status: 'error', message: `HTTP ${response.status}` };
    }
    return { status: 'success', data: await response.json() };
  } catch (error) {
    return { status: 'error', message: String(error) };
  }
},
```
