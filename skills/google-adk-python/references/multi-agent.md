# Multi-Agent Orchestration Patterns

## Table of Contents
- [Pattern 1: Coordinator/Dispatcher](#pattern-1-coordinatordispatcher)
- [Pattern 2: Sequential Pipeline](#pattern-2-sequential-pipeline)
- [Pattern 3: Parallel Fan-Out/Gather](#pattern-3-parallel-fan-outgather)
- [Pattern 4: Hierarchical Decomposition](#pattern-4-hierarchical-decomposition)
- [Pattern 5: Generator-Critic](#pattern-5-generator-critic)
- [Pattern 6: Iterative Refinement](#pattern-6-iterative-refinement)
- [Pattern 7: Human-in-the-Loop](#pattern-7-human-in-the-loop)
- [Choosing the Right Pattern](#choosing-the-right-pattern)

## Pattern 1: Coordinator/Dispatcher

Central LlmAgent routes requests to specialized sub-agents based on intent.

```python
billing_agent = Agent(
    name="billing_specialist",
    description="Handles billing, payments, invoices, and subscription questions",
    instruction="You are a billing specialist. Help with payment and invoice issues."
)

support_agent = Agent(
    name="technical_support",
    description="Handles technical issues, bugs, and product questions",
    instruction="You are tech support. Help troubleshoot technical problems."
)

sales_agent = Agent(
    name="sales_specialist",
    description="Handles pricing, upgrades, and new purchases",
    instruction="You are a sales specialist. Help with purchasing decisions."
)

coordinator = Agent(
    name="help_desk",
    model="gemini-2.0-flash",
    instruction="""You are a help desk coordinator.
    Analyze the customer's request and route to the appropriate specialist.
    If unclear, ask clarifying questions before routing.""",
    sub_agents=[billing_agent, support_agent, sales_agent]
)
```

**How it works:** The coordinator's LLM reads sub-agent descriptions and decides which to invoke via `transfer_to_agent()`.

**Best for:** Customer service, multi-domain assistants, triage systems.

## Pattern 2: Sequential Pipeline

Linear workflow where each agent transforms data and passes via state.

```python
from google.adk.agents import SequentialAgent

# Stage 1: Data validation
validator = Agent(
    name="validator",
    instruction="""Validate the input data.
    Check for required fields and format.
    Store validation result in state.""",
    output_key="validation_result"
)

# Stage 2: Processing
processor = Agent(
    name="processor",
    instruction="""Process the validated data from {validation_result}.
    Apply business logic transformations.
    Store processed data in state.""",
    output_key="processed_data"
)

# Stage 3: Report generation
reporter = Agent(
    name="reporter",
    instruction="""Generate a report from {processed_data}.
    Format for the end user.""",
    output_key="final_report"
)

pipeline = SequentialAgent(
    name="data_pipeline",
    sub_agents=[validator, processor, reporter]
)
```

**State flow:**
```
Input → validator → validation_result → processor → processed_data → reporter → final_report
```

**Best for:** ETL pipelines, content workflows, approval chains.

## Pattern 3: Parallel Fan-Out/Gather

Execute independent tasks concurrently, then aggregate results.

```python
from google.adk.agents import ParallelAgent, SequentialAgent

# Fan-out: parallel data collection
collectors = ParallelAgent(
    name="data_collectors",
    sub_agents=[
        Agent(
            name="news_collector",
            instruction="Gather latest news about the topic.",
            tools=[news_api],
            output_key="news_results"
        ),
        Agent(
            name="social_collector",
            instruction="Gather social media sentiment.",
            tools=[social_api],
            output_key="social_results"
        ),
        Agent(
            name="market_collector",
            instruction="Gather market data.",
            tools=[market_api],
            output_key="market_results"
        )
    ]
)

# Gather: synthesize all results
synthesizer = Agent(
    name="synthesizer",
    instruction="""Combine insights from:
    - News: {news_results}
    - Social: {social_results}
    - Market: {market_results}

    Provide a comprehensive analysis.""",
    output_key="final_analysis"
)

# Complete pipeline
analysis_system = SequentialAgent(
    name="market_analyzer",
    sub_agents=[collectors, synthesizer]
)
```

**Best for:** Multi-source research, parallel API calls, distributed analysis.

## Pattern 4: Hierarchical Decomposition

Complex problems broken into sub-problems across agent tree.

```python
# Level 3: Leaf specialists
web_searcher = Agent(name="web_searcher", tools=[google_search], ...)
summarizer = Agent(name="summarizer", ...)

# Level 2: Mid-level coordinators
research_lead = Agent(
    name="research_lead",
    instruction="Coordinate research tasks.",
    sub_agents=[web_searcher, summarizer]
)

writing_lead = Agent(
    name="writing_lead",
    instruction="Coordinate writing tasks.",
    sub_agents=[drafter, editor]
)

# Level 1: Top coordinator
project_manager = Agent(
    name="project_manager",
    instruction="""You manage complex projects.
    Delegate research to research_lead.
    Delegate writing to writing_lead.
    Coordinate their outputs.""",
    sub_agents=[research_lead, writing_lead]
)
```

**Best for:** Complex projects, enterprise workflows, large-scale automation.

## Pattern 5: Generator-Critic

One agent creates, another reviews. Improves quality through feedback.

```python
from google.adk.agents import SequentialAgent

generator = Agent(
    name="draft_writer",
    instruction="""Write a draft based on the requirements.
    Be creative but stay on topic.""",
    output_key="draft"
)

critic = Agent(
    name="quality_reviewer",
    instruction="""Review the draft: {draft}

    Evaluate:
    1. Accuracy - Are facts correct?
    2. Clarity - Is it easy to understand?
    3. Completeness - Does it cover all requirements?

    Provide specific feedback and a quality score (1-10).
    If score >= 8, approve. Otherwise, list improvements needed.""",
    output_key="review"
)

review_pipeline = SequentialAgent(
    name="content_review",
    sub_agents=[generator, critic]
)
```

**Best for:** Content creation, code review, document verification.

## Pattern 6: Iterative Refinement

Loop until quality threshold or max iterations.

```python
from google.adk.agents import LoopAgent, SequentialAgent

def check_quality(ctx) -> dict:
    """Check if quality meets threshold."""
    review = ctx.session.state.get("review", {})
    if review.get("score", 0) >= 8:
        return {"action": "escalate", "reason": "Quality threshold met"}
    return {"action": "continue"}

refiner = Agent(
    name="refiner",
    instruction="""Improve the draft based on feedback: {review}
    Address each point of criticism.""",
    output_key="draft"
)

reviewer = Agent(
    name="reviewer",
    instruction="""Review the draft: {draft}
    Score 1-10 and provide feedback.""",
    output_key="review",
    tools=[check_quality]  # Can trigger escalation
)

refinement_loop = LoopAgent(
    name="quality_loop",
    max_iterations=5,
    sub_agents=[refiner, reviewer]
)

# Full system with initial draft
system = SequentialAgent(
    name="writing_system",
    sub_agents=[
        Agent(name="initial_drafter", output_key="draft", ...),
        refinement_loop
    ]
)
```

**Best for:** Quality improvement, optimization, convergence problems.

## Pattern 7: Human-in-the-Loop

Pause for human approval at critical points.

```python
def request_approval(ctx, action: str, details: str) -> dict:
    """Request human approval for an action."""
    # In practice, this would integrate with your approval system
    ctx.session.state["pending_approval"] = {
        "action": action,
        "details": details,
        "status": "pending"
    }
    return {"status": "awaiting_approval"}

agent = Agent(
    name="cautious_agent",
    instruction="""Before taking irreversible actions (delete, send, publish):
    1. Summarize what you're about to do
    2. Call request_approval() with details
    3. Wait for approval before proceeding""",
    tools=[request_approval, delete_file, send_email]
)
```

**Integration patterns:**
- Callbacks that pause execution
- State flags checked between steps
- External approval service integration

## Choosing the Right Pattern

| Pattern | Use When | Complexity |
|---------|----------|------------|
| Coordinator | Multi-domain routing | Low |
| Sequential | Ordered dependencies | Low |
| Parallel | Independent tasks | Medium |
| Hierarchical | Complex decomposition | High |
| Generator-Critic | Quality matters | Medium |
| Iterative | Convergence needed | Medium |
| Human-in-the-Loop | Risk mitigation | Medium |

**Combining patterns:**
```python
# Coordinator → Sequential → Parallel
coordinator = Agent(
    sub_agents=[
        SequentialAgent(sub_agents=[
            ParallelAgent(sub_agents=[...]),
            aggregator
        ]),
        simple_agent
    ]
)
```

**Start simple:** Begin with single agent, add orchestration only when needed.
