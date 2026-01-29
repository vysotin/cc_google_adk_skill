# Agent Types and Patterns

## Table of Contents
- [LlmAgent](#llmagent)
- [SequentialAgent](#sequentialagent)
- [ParallelAgent](#parallelagent)
- [LoopAgent](#loopagent)
- [Custom Agents](#custom-agents)
- [Agent Hierarchy](#agent-hierarchy)

## LlmAgent

The primary agent type using LLMs for reasoning and tool selection.

```python
from google.adk.agents import Agent

agent = Agent(
    name="researcher",
    model="gemini-2.0-flash",  # or gemini-1.5-pro, gemini-2.0-flash-lite
    instruction="""You are a research assistant.
    - Search for information when asked
    - Summarize findings concisely
    - Cite sources""",
    description="Handles research and information gathering tasks",  # For LLM routing
    tools=[search_web, summarize],
    output_key="research_results"  # Store output in session.state
)
```

**Key parameters:**
- `name` - Unique identifier
- `model` - LLM model ID
- `instruction` - System prompt (supports `{state_key}` templating)
- `description` - Used by parent agents for routing decisions
- `tools` - List of callable tools
- `output_key` - Store final output in `session.state[output_key]`
- `sub_agents` - Child agents for delegation

## SequentialAgent

Executes sub-agents in order. Output of one flows to next via shared state.

```python
from google.adk.agents import SequentialAgent

pipeline = SequentialAgent(
    name="content_pipeline",
    sub_agents=[
        Agent(
            name="researcher",
            instruction="Research the topic. Store findings in state.",
            output_key="research"
        ),
        Agent(
            name="writer",
            instruction="Write article using {research}.",
            output_key="draft"
        ),
        Agent(
            name="editor",
            instruction="Edit and improve {draft}.",
            output_key="final_article"
        )
    ]
)
```

**Use cases:**
- Multi-step content creation
- Data processing pipelines
- Validation chains

## ParallelAgent

Executes all sub-agents concurrently. All share same `session.state`.

```python
from google.adk.agents import ParallelAgent

gatherer = ParallelAgent(
    name="data_gatherer",
    sub_agents=[
        Agent(name="news_agent", output_key="news_data", ...),
        Agent(name="social_agent", output_key="social_data", ...),
        Agent(name="market_agent", output_key="market_data", ...)
    ]
)

# Follow with aggregator
pipeline = SequentialAgent(
    name="analysis_pipeline",
    sub_agents=[
        gatherer,
        Agent(
            name="synthesizer",
            instruction="Combine {news_data}, {social_data}, {market_data}..."
        )
    ]
)
```

**Use cases:**
- Fetching from multiple APIs
- Running independent analyses
- Parallel data collection

## LoopAgent

Repeats sub-agents until condition met or max iterations reached.

```python
from google.adk.agents import LoopAgent

refiner = LoopAgent(
    name="quality_refiner",
    max_iterations=5,
    sub_agents=[
        Agent(
            name="improver",
            instruction="Improve the draft in {current_draft}.",
            output_key="current_draft"
        ),
        Agent(
            name="quality_checker",
            instruction="""Review {current_draft}.
            If quality >= 8/10, call escalate() to exit loop.
            Otherwise, provide improvement suggestions.""",
            tools=[escalate]  # Built-in function to exit loop
        )
    ]
)
```

**Exit conditions:**
1. `max_iterations` reached
2. Sub-agent calls `escalate()` or `transfer_to_agent()`

## Custom Agents

Extend `BaseAgent` for specialized logic:

```python
from google.adk.agents import BaseAgent

class RateLimitedAgent(BaseAgent):
    def __init__(self, name, rate_limit, **kwargs):
        super().__init__(name=name, **kwargs)
        self.rate_limit = rate_limit
        self.call_count = 0

    async def run(self, context):
        if self.call_count >= self.rate_limit:
            return Content(text="Rate limit exceeded")
        self.call_count += 1
        # Custom logic here
        return await super().run(context)
```

## Agent Hierarchy

Agents form parent-child trees via `sub_agents`:

```python
root = Agent(
    name="coordinator",
    sub_agents=[
        Agent(name="specialist_a", ...),
        Agent(name="specialist_b", sub_agents=[
            Agent(name="sub_specialist_1", ...),
            Agent(name="sub_specialist_2", ...)
        ])
    ]
)
```

**Navigation:**
```python
# From child, access parent
agent.parent_agent

# Find any agent by name
root.find_agent("sub_specialist_1")
```

**Rules:**
- Agent instance can only be added as sub-agent once
- Avoid circular references
- Use `description` for LLM routing decisions

## Agent Communication

### Via Shared State
```python
# Agent A writes
ctx.session.state["data"] = result

# Agent B reads (via instruction templating)
instruction="Process the {data}..."
```

### Via LLM Delegation
```python
# Parent routes based on descriptions
coordinator = Agent(
    name="coordinator",
    instruction="Route requests to appropriate specialist.",
    sub_agents=[billing_agent, support_agent]  # LLM picks based on descriptions
)
```

### Via AgentTool
```python
from google.adk.tools import AgentTool

# Explicit tool-based invocation
agent = Agent(
    tools=[AgentTool(agent=specialist_agent)]
)
```

### Via transfer_to_agent()
```python
# Built-in function for explicit handoff
def handle_escalation():
    transfer_to_agent("human_support")
```
