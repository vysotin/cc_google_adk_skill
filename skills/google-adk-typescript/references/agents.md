# Agent Types and Patterns

## Table of Contents
- [LlmAgent](#llmagent)
- [SequentialAgent](#sequentialagent)
- [ParallelAgent](#parallelagent)
- [LoopAgent](#loopagent)
- [Custom Agents (BaseAgent)](#custom-agents-baseagent)
- [Agent Hierarchy and Communication](#agent-hierarchy-and-communication)

## LlmAgent

The primary agent type. Uses an LLM for reasoning, tool selection, and delegation.

```typescript
import { LlmAgent, GOOGLE_SEARCH } from '@google/adk';

const agent = new LlmAgent({
  name: 'researcher',
  model: 'gemini-2.5-flash',
  instruction: `You are a research assistant.
    - Search for information when asked
    - Summarize findings concisely
    - Cite sources`,
  description: 'Handles research and information gathering tasks',
  tools: [GOOGLE_SEARCH],
  outputKey: 'research_results',
});
```

**Key properties:**
- `name` - Unique identifier (required)
- `model` - LLM model ID (required)
- `instruction` - System prompt; supports `{state_key}` templating
- `description` - Used by parent agents for LLM routing decisions
- `tools` - Array of tool instances
- `outputKey` - Store final text output in `session.state[outputKey]`
- `subAgents` - Child agents for delegation

**Dynamic instructions:**
```typescript
import { ReadonlyContext } from '@google/adk';

function dynamicInstruction(context: ReadonlyContext): string {
  return `User language is ${context.state.get('user:language', 'en')}. Respond accordingly.`;
}

const agent = new LlmAgent({
  name: 'dynamic_agent',
  model: 'gemini-2.5-flash',
  instruction: dynamicInstruction,
});
```

## SequentialAgent

Executes sub-agents in order. Shares `InvocationContext` and `session.state` between steps.

```typescript
import { LlmAgent, SequentialAgent } from '@google/adk';

const codeWriter = new LlmAgent({
  name: 'CodeWriterAgent',
  model: 'gemini-2.5-flash',
  instruction: `Write Python code based on the user's request.
Output only the code block.`,
  description: 'Writes initial code.',
  outputKey: 'generated_code',
});

const codeReviewer = new LlmAgent({
  name: 'CodeReviewerAgent',
  model: 'gemini-2.5-flash',
  instruction: `Review this code:
\`\`\`
{generated_code}
\`\`\`
Provide feedback as a bulleted list.`,
  description: 'Reviews code and provides feedback.',
  outputKey: 'review_comments',
});

const codeRefactorer = new LlmAgent({
  name: 'CodeRefactorerAgent',
  model: 'gemini-2.5-flash',
  instruction: `Refactor based on review:
Code: {generated_code}
Comments: {review_comments}`,
  description: 'Refactors code based on review.',
  outputKey: 'refactored_code',
});

export const rootAgent = new SequentialAgent({
  name: 'CodePipelineAgent',
  subAgents: [codeWriter, codeReviewer, codeRefactorer],
  description: 'Sequential code writing, reviewing, and refactoring.',
});
```

**State flow:** `outputKey` writes → `{template}` reads.

## ParallelAgent

Executes all sub-agents concurrently. Each runs in its own execution branch.

```typescript
import { LlmAgent, ParallelAgent, SequentialAgent, GOOGLE_SEARCH } from '@google/adk';

const researcher1 = new LlmAgent({
  name: 'EnergyResearcher',
  model: 'gemini-2.5-flash',
  instruction: 'Research renewable energy advancements. Summarize in 1-2 sentences.',
  tools: [GOOGLE_SEARCH],
  outputKey: 'energy_result',
});

const researcher2 = new LlmAgent({
  name: 'EVResearcher',
  model: 'gemini-2.5-flash',
  instruction: 'Research electric vehicle technology. Summarize in 1-2 sentences.',
  tools: [GOOGLE_SEARCH],
  outputKey: 'ev_result',
});

const parallelResearch = new ParallelAgent({
  name: 'ParallelResearch',
  subAgents: [researcher1, researcher2],
});

const synthesizer = new LlmAgent({
  name: 'Synthesizer',
  model: 'gemini-2.5-flash',
  instruction: `Combine findings:
  - Energy: {energy_result}
  - EV: {ev_result}
  Write a unified report.`,
});

// Fan-out then gather
export const rootAgent = new SequentialAgent({
  name: 'ResearchPipeline',
  subAgents: [parallelResearch, synthesizer],
});
```

**Important:** Each parallel sub-agent must write to a **unique** `outputKey` to prevent race conditions.

## LoopAgent

Repeats sub-agents until `maxIterations` or an agent signals escalation.

```typescript
import { LlmAgent, LoopAgent, SequentialAgent } from '@google/adk';

const improver = new LlmAgent({
  name: 'Improver',
  model: 'gemini-2.5-flash',
  instruction: 'Improve the draft: {current_draft}. Apply the feedback: {feedback}.',
  outputKey: 'current_draft',
});

const critic = new LlmAgent({
  name: 'Critic',
  model: 'gemini-2.5-flash',
  instruction: `Review {current_draft}. Score 1-10.
If score >= 8, signal escalation to exit the loop.
Otherwise provide feedback.`,
  outputKey: 'feedback',
});

const refinementLoop = new LoopAgent({
  name: 'QualityLoop',
  subAgents: [improver, critic],
  maxIterations: 5,
});

export const rootAgent = new SequentialAgent({
  name: 'WritingSystem',
  subAgents: [
    new LlmAgent({
      name: 'InitialDrafter',
      instruction: 'Write a first draft on the topic.',
      outputKey: 'current_draft',
      model: 'gemini-2.5-flash',
    }),
    refinementLoop,
  ],
});
```

**Exit conditions:** `maxIterations` reached, or a sub-agent sets `escalate=true` in `EventActions`.

## Custom Agents (BaseAgent)

Extend `BaseAgent` and implement `runAsyncImpl` for custom orchestration.

```typescript
import {
  BaseAgent,
  LlmAgent,
  LoopAgent,
  SequentialAgent,
  InvocationContext,
  Event,
} from '@google/adk';

class StoryFlowAgent extends BaseAgent {
  private storyGenerator: LlmAgent;
  private loopAgent: LoopAgent;
  private postProcessing: SequentialAgent;

  constructor(
    name: string,
    storyGenerator: LlmAgent,
    critic: LlmAgent,
    reviser: LlmAgent,
    grammarCheck: LlmAgent,
    toneCheck: LlmAgent
  ) {
    const loopAgent = new LoopAgent({
      name: 'CriticReviserLoop',
      subAgents: [critic, reviser],
      maxIterations: 2,
    });

    const postProcessing = new SequentialAgent({
      name: 'PostProcessing',
      subAgents: [grammarCheck, toneCheck],
    });

    super({
      name,
      subAgents: [storyGenerator, loopAgent, postProcessing],
    });

    this.storyGenerator = storyGenerator;
    this.loopAgent = loopAgent;
    this.postProcessing = postProcessing;
  }

  async *runAsyncImpl(ctx: InvocationContext): AsyncGenerator<Event> {
    // Stage 1: Generate
    for await (const event of this.storyGenerator.runAsync(ctx)) {
      yield event;
    }

    if (!ctx.session.state['current_story']) return;

    // Stage 2: Critic-Reviser Loop
    for await (const event of this.loopAgent.runAsync(ctx)) {
      yield event;
    }

    // Stage 3: Post-processing
    for await (const event of this.postProcessing.runAsync(ctx)) {
      yield event;
    }

    // Stage 4: Conditional logic
    const tone = ctx.session.state['tone_check_result'] as string;
    if (tone === 'negative') {
      for await (const event of this.storyGenerator.runAsync(ctx)) {
        yield event;
      }
    }
  }

  async *runLiveImpl(ctx: InvocationContext): AsyncGenerator<Event> {
    yield* this.runAsyncImpl(ctx);
  }
}
```

**Key pattern:** Use `async*` generators. Invoke sub-agents via `agent.runAsync(ctx)` and `yield` their events.

## Agent Hierarchy and Communication

### Sub-Agent Routing (LLM-driven)

```typescript
const coordinator = new LlmAgent({
  name: 'coordinator',
  model: 'gemini-2.5-flash',
  instruction: 'Route requests to the appropriate specialist.',
  subAgents: [billingAgent, supportAgent],
  // LLM picks sub-agent based on their `description` fields
});
```

### State-Based Communication

```typescript
// Agent A writes via outputKey
const agentA = new LlmAgent({ outputKey: 'result_a', ... });

// Agent B reads via instruction template
const agentB = new LlmAgent({ instruction: 'Use {result_a}...', ... });
```

### Rules

- An agent instance can only be added as a sub-agent **once**
- Avoid circular references
- Use descriptive `description` fields for LLM routing
- Navigate with `agent.parentAgent` and `agent.findAgent('name')`
