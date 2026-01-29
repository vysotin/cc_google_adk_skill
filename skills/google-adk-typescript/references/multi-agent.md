# Multi-Agent Orchestration Patterns

## Table of Contents
- [Pattern 1: Coordinator/Dispatcher](#pattern-1-coordinatordispatcher)
- [Pattern 2: Sequential Pipeline](#pattern-2-sequential-pipeline)
- [Pattern 3: Parallel Fan-Out/Gather](#pattern-3-parallel-fan-outgather)
- [Pattern 4: Hierarchical Decomposition](#pattern-4-hierarchical-decomposition)
- [Pattern 5: Generator-Critic](#pattern-5-generator-critic)
- [Pattern 6: Iterative Refinement](#pattern-6-iterative-refinement)
- [Choosing the Right Pattern](#choosing-the-right-pattern)

## Pattern 1: Coordinator/Dispatcher

Central LlmAgent routes requests to specialists based on their `description`.

```typescript
import { LlmAgent } from '@google/adk';

const billingAgent = new LlmAgent({
  name: 'billing_specialist',
  model: 'gemini-2.5-flash',
  description: 'Handles billing, payments, invoices, and subscriptions',
  instruction: 'You are a billing specialist. Help with payment and invoice issues.',
});

const supportAgent = new LlmAgent({
  name: 'technical_support',
  model: 'gemini-2.5-flash',
  description: 'Handles technical issues, bugs, and product questions',
  instruction: 'You are tech support. Help troubleshoot technical problems.',
});

export const rootAgent = new LlmAgent({
  name: 'help_desk',
  model: 'gemini-2.5-flash',
  instruction: `You are a help desk coordinator.
    Analyze the request and route to the appropriate specialist.`,
  subAgents: [billingAgent, supportAgent],
});
```

The coordinator LLM reads sub-agent descriptions and invokes `transfer_to_agent()`.

## Pattern 2: Sequential Pipeline

Ordered workflow with state passing via `outputKey` and `{template}`.

```typescript
import { LlmAgent, SequentialAgent } from '@google/adk';

const validator = new LlmAgent({
  name: 'Validator',
  model: 'gemini-2.5-flash',
  instruction: 'Validate the input data. Report issues.',
  outputKey: 'validation_result',
});

const processor = new LlmAgent({
  name: 'Processor',
  model: 'gemini-2.5-flash',
  instruction: 'Process the validated data: {validation_result}',
  outputKey: 'processed_data',
});

const reporter = new LlmAgent({
  name: 'Reporter',
  model: 'gemini-2.5-flash',
  instruction: 'Generate a report from: {processed_data}',
  outputKey: 'final_report',
});

export const rootAgent = new SequentialAgent({
  name: 'DataPipeline',
  subAgents: [validator, processor, reporter],
});
```

## Pattern 3: Parallel Fan-Out/Gather

Concurrent execution followed by aggregation.

```typescript
import { LlmAgent, ParallelAgent, SequentialAgent, GOOGLE_SEARCH } from '@google/adk';

const collectors = new ParallelAgent({
  name: 'DataCollectors',
  subAgents: [
    new LlmAgent({
      name: 'NewsCollector',
      model: 'gemini-2.5-flash',
      instruction: 'Gather latest news about the topic.',
      tools: [GOOGLE_SEARCH],
      outputKey: 'news_results',
    }),
    new LlmAgent({
      name: 'MarketCollector',
      model: 'gemini-2.5-flash',
      instruction: 'Gather market data about the topic.',
      tools: [GOOGLE_SEARCH],
      outputKey: 'market_results',
    }),
  ],
});

const synthesizer = new LlmAgent({
  name: 'Synthesizer',
  model: 'gemini-2.5-flash',
  instruction: `Combine insights:
    - News: {news_results}
    - Market: {market_results}
    Provide comprehensive analysis.`,
});

export const rootAgent = new SequentialAgent({
  name: 'AnalysisPipeline',
  subAgents: [collectors, synthesizer],
});
```

**Critical:** Each parallel sub-agent must write to a unique `outputKey` to avoid race conditions.

## Pattern 4: Hierarchical Decomposition

Multi-level agent tree for complex problems.

```typescript
const researchLead = new LlmAgent({
  name: 'ResearchLead',
  model: 'gemini-2.5-flash',
  instruction: 'Coordinate research tasks.',
  subAgents: [webSearcher, summarizer],
});

const writingLead = new LlmAgent({
  name: 'WritingLead',
  model: 'gemini-2.5-flash',
  instruction: 'Coordinate writing tasks.',
  subAgents: [drafter, editor],
});

export const rootAgent = new LlmAgent({
  name: 'ProjectManager',
  model: 'gemini-2.5-flash',
  instruction: `Manage complex projects.
    Delegate research to ResearchLead.
    Delegate writing to WritingLead.`,
  subAgents: [researchLead, writingLead],
});
```

## Pattern 5: Generator-Critic

One agent creates, another reviews.

```typescript
import { LlmAgent, SequentialAgent } from '@google/adk';

const generator = new LlmAgent({
  name: 'DraftWriter',
  model: 'gemini-2.5-flash',
  instruction: 'Write a draft based on the requirements.',
  outputKey: 'draft',
});

const critic = new LlmAgent({
  name: 'QualityReviewer',
  model: 'gemini-2.5-flash',
  instruction: `Review the draft: {draft}
    Score 1-10 on accuracy, clarity, completeness.
    If score >= 8, approve. Otherwise list improvements.`,
  outputKey: 'review',
});

export const rootAgent = new SequentialAgent({
  name: 'ContentReview',
  subAgents: [generator, critic],
});
```

## Pattern 6: Iterative Refinement

Loop until quality threshold or max iterations.

```typescript
import { LlmAgent, LoopAgent, SequentialAgent } from '@google/adk';

const refiner = new LlmAgent({
  name: 'Refiner',
  model: 'gemini-2.5-flash',
  instruction: `Improve the draft based on feedback:
    Draft: {draft}
    Feedback: {review}`,
  outputKey: 'draft',
});

const reviewer = new LlmAgent({
  name: 'Reviewer',
  model: 'gemini-2.5-flash',
  instruction: `Review: {draft}
    Score 1-10 and provide feedback.
    If score >= 8, signal escalation to exit.`,
  outputKey: 'review',
});

const refinementLoop = new LoopAgent({
  name: 'QualityLoop',
  subAgents: [refiner, reviewer],
  maxIterations: 5,
});

export const rootAgent = new SequentialAgent({
  name: 'WritingSystem',
  subAgents: [
    new LlmAgent({
      name: 'InitialDrafter',
      model: 'gemini-2.5-flash',
      instruction: 'Write a first draft.',
      outputKey: 'draft',
    }),
    refinementLoop,
  ],
});
```

## Choosing the Right Pattern

| Pattern | Use When | Complexity |
|---------|----------|------------|
| Coordinator | Multi-domain routing | Low |
| Sequential | Ordered dependencies | Low |
| Parallel | Independent tasks | Medium |
| Hierarchical | Complex decomposition | High |
| Generator-Critic | Quality matters | Medium |
| Iterative | Convergence needed | Medium |

**Combining patterns:**
```typescript
const root = new SequentialAgent({
  subAgents: [
    new ParallelAgent({ subAgents: [agentA, agentB] }),
    new LlmAgent({ instruction: 'Aggregate {result_a} and {result_b}...' }),
  ],
});
```

**Start simple:** A single LlmAgent is often sufficient. Add orchestration only when needed.
