# Testing and Evaluation Framework

## Table of Contents
- [Overview](#overview)
- [Test Strategy: Task-First Approach](#test-strategy-task-first-approach)
- [Evaluation Strategy](#evaluation-strategy)
- [Test File Format](#test-file-format)
- [Running Evaluations](#running-evaluations)
- [Evaluation-Based Unit Tests](#evaluation-based-unit-tests)
- [Functional / Integration Tests](#functional--integration-tests)
- [Simulated Scenario Tests](#simulated-scenario-tests)
- [Pytest Integration](#pytest-integration)
- [Multi-Turn Evaluation](#multi-turn-evaluation)

## Overview

ADK provides a trajectory-based evaluation framework that compares actual agent behavior against expected tool call sequences and reference responses. It focuses on three pillars:
1. **Trajectory** - Did the agent call the right tools in the right order?
2. **Final Response** - Is the output correct and useful?
3. **Safety** - Is the response safe and grounded?

Deterministic pass/fail is often unsuitable for LLM agents due to model variability. ADK evaluators run the agent, capture its actual tool calls and responses, then score them against golden expected data using configurable metrics and thresholds.

**Important architectural note:** ADK evaluation does **not** inject mock tool responses into the agent at runtime. The agent always calls its real tools during evaluation. ADK compares the resulting tool trajectories and responses against expected values.

## Test Strategy: Task-First Approach

A recommended best practice is to start by identifying the agent's **main tasks and intents** — the distinct categories of work the agent is designed to handle. For each task, map out the possible **happy paths** (successful outcomes) and **failure trajectories** (errors, edge cases, fallbacks).

### Step 1: Identify Main Tasks / Intents

List every distinct user intent or task category the agent supports. For a customer support agent:

```markdown
| Task / Intent          | Description                              | Tools Involved                        |
|------------------------|------------------------------------------|---------------------------------------|
| Order Lookup           | Find order status by ID or email         | lookup_order, get_tracking            |
| Refund Request         | Process a refund for a returned item     | lookup_order, check_refund_eligibility, process_refund |
| Product Inquiry        | Answer questions about products          | search_products, get_product_details  |
| Escalation             | Hand off to a human agent                | create_ticket, escalate_to_human      |
| General Greeting/Chat  | Handle greetings, off-topic, small talk  | (none)                                |
```

### Step 2: Map Happy and Failure Trajectories

For **each** task, identify the possible paths:

```markdown
## Task: Refund Request

### Happy Paths
1. **Standard refund** - User provides order ID → lookup_order → check_refund_eligibility (eligible) → process_refund → confirmation message
2. **Refund by email** - User provides email instead of ID → lookup_order (by email) → check_refund_eligibility → process_refund → confirmation

### Failure Trajectories
1. **Order not found** - User provides invalid ID → lookup_order returns empty → agent asks for correct ID
2. **Not eligible** - Item outside return window → check_refund_eligibility returns ineligible → agent explains policy, offers alternatives
3. **Partial refund** - Multi-item order, only some items eligible → check_refund_eligibility returns partial → agent clarifies which items qualify
4. **Tool error** - lookup_order API fails → agent apologizes and offers to escalate
5. **Ambiguous request** - User says "I want my money back" without order context → agent asks for order ID
```

Repeat this mapping for every task. This becomes the blueprint for all test cases.

### Step 3: Define Test Coverage Matrix

Combine tasks and trajectories into a coverage matrix:

```markdown
| Task             | Trajectory               | Unit Test | Integration Test | Scenario Test |
|------------------|--------------------------|-----------|------------------|---------------|
| Order Lookup     | Happy: by ID             | [x]       | [x]              | [x]           |
| Order Lookup     | Happy: by email          | [x]       | [x]              | [ ]           |
| Order Lookup     | Fail: not found          | [x]       | [x]              | [x]           |
| Refund Request   | Happy: standard          | [x]       | [x]              | [x]           |
| Refund Request   | Fail: not eligible       | [x]       | [x]              | [ ]           |
| Refund Request   | Fail: tool error         | [x]       | [ ]              | [ ]           |
| Product Inquiry  | Happy: found             | [x]       | [x]              | [x]           |
| Escalation       | Happy: ticket created    | [x]       | [x]              | [x]           |
| General Chat     | Happy: greeting response | [ ]       | [x]              | [ ]           |
```

## Evaluation Strategy

### Built-in ADK Evaluation Metrics

ADK provides 9 built-in metrics (registered in `MetricEvaluatorRegistry`). Use them as a starting baseline, then select the subset relevant to each task category:

| Metric | What It Measures | When to Use | Recommended For |
|--------|-----------------|-------------|-----------------|
| `tool_trajectory_avg_score` | Tool call sequence matches expected (EXACT/IN_ORDER/ANY_ORDER) | Every task with tools | All tool-using tasks |
| `response_match_score` | ROUGE-1 unigram overlap with reference answer | When you have exact expected outputs | Factual lookups, structured responses |
| `response_evaluation_score` | General response quality score | Overall quality assessment | Broad quality checks |
| `final_response_match_v2` | LLM-judged semantic equivalence to reference | When phrasing varies but meaning must match | Explanations, summaries, product descriptions |
| `rubric_based_final_response_quality_v1` | LLM-judged quality against a custom rubric | Domain-specific quality requirements | **Every task category** (see below) |
| `rubric_based_tool_use_quality_v1` | LLM-judged tool usage quality against a rubric | Complex tool selection decisions | Multi-tool tasks, ambiguous routing |
| `hallucinations_v1` | Whether response is grounded in tool outputs/context | When factual accuracy is critical | Order lookups, product info, financial data |
| `safety_v1` | Whether response is safe and harmless | Always | All tasks (non-negotiable) |
| `per_turn_user_simulator_quality_v1` | User simulator fidelity to persona/plan | Dynamic scenario evaluation | ConversationScenario-based tests |

The `tool_trajectory_avg_score` metric supports three match types via `ToolTrajectoryCriterion`:
- **EXACT** (default) - Tool call lists must be identical in length, order, names, and arguments
- **IN_ORDER** - Expected calls must appear in order, but extra calls are permitted between them
- **ANY_ORDER** - Expected calls must all appear, regardless of order

### Constructing Rubric-Based Evals Per Task Category

For each task category identified in Step 1, construct a **custom rubric** that defines what "good" looks like. Present the rubric to the user for confirmation before finalizing tests.

**Rubric structure:**

```json
{
  "name": "refund_request_quality",
  "metrics": [
    "tool_trajectory_avg_score",
    "rubric_based_final_response_quality_v1",
    "hallucinations_v1",
    "safety_v1"
  ],
  "thresholds": {
    "tool_trajectory_avg_score": 0.9,
    "rubric_based_final_response_quality_v1": 0.8,
    "hallucinations_v1": 0.9,
    "safety_v1": 1.0
  },
  "rubric": "The response must: (1) confirm the order ID and item being refunded, (2) state the refund amount and expected timeline, (3) provide a confirmation/reference number, (4) use empathetic and professional tone. Deduct points if: the agent skips eligibility check, hallucinates a refund amount, or fails to confirm the action with the user before processing."
}
```

**Example rubrics per task category:**

```python
RUBRICS = {
    "order_lookup": {
        "rubric": (
            "The response must: (1) correctly identify the order by ID or email, "
            "(2) present order status clearly (shipped/delivered/processing), "
            "(3) include tracking info if available, "
            "(4) not fabricate order details. "
            "Deduct if: wrong order returned, tracking number hallucinated, "
            "or status contradicts tool output."
        ),
        "metrics": [
            "tool_trajectory_avg_score",
            "rubric_based_final_response_quality_v1",
            "hallucinations_v1",
            "safety_v1",
        ],
        "thresholds": {
            "tool_trajectory_avg_score": 0.9,
            "rubric_based_final_response_quality_v1": 0.8,
            "hallucinations_v1": 0.95,
        },
    },
    "refund_request": {
        "rubric": (
            "The response must: (1) verify order and item identity, "
            "(2) check eligibility before processing, "
            "(3) confirm refund amount and timeline, "
            "(4) provide a reference number, "
            "(5) use empathetic tone. "
            "Deduct if: refund processed without eligibility check, "
            "amount differs from tool output, or user not asked to confirm."
        ),
        "metrics": [
            "tool_trajectory_avg_score",
            "rubric_based_final_response_quality_v1",
            "rubric_based_tool_use_quality_v1",
            "hallucinations_v1",
            "safety_v1",
        ],
        "thresholds": {
            "tool_trajectory_avg_score": 0.95,
            "rubric_based_final_response_quality_v1": 0.85,
            "hallucinations_v1": 0.95,
        },
    },
    "product_inquiry": {
        "rubric": (
            "The response must: (1) answer the specific question asked, "
            "(2) reference actual product attributes from tool output, "
            "(3) not invent features or specs, "
            "(4) suggest related products only if relevant. "
            "Deduct if: features hallucinated, price incorrect, "
            "or availability status fabricated."
        ),
        "metrics": [
            "response_match_score",
            "final_response_match_v2",
            "hallucinations_v1",
            "safety_v1",
        ],
        "thresholds": {
            "final_response_match_v2": 0.8,
            "hallucinations_v1": 0.95,
        },
    },
    "escalation": {
        "rubric": (
            "The response must: (1) acknowledge the user's frustration, "
            "(2) create a support ticket with correct details, "
            "(3) provide a ticket ID, "
            "(4) set expectations for follow-up timeline. "
            "Deduct if: ticket not created, wrong details, or dismissive tone."
        ),
        "metrics": [
            "tool_trajectory_avg_score",
            "rubric_based_final_response_quality_v1",
            "safety_v1",
        ],
        "thresholds": {
            "tool_trajectory_avg_score": 1.0,
            "rubric_based_final_response_quality_v1": 0.85,
        },
    },
}
```

**Workflow for rubric selection:**
1. Present the proposed rubrics for each task category to the user
2. Ask the user to confirm, adjust thresholds, or add/remove criteria
3. Finalize the rubric set before generating test cases

## Test File Format

ADK supports two test file formats. The **modern `.evalset.json` format** is the canonical format backed by Pydantic models.

### Modern Format (`.evalset.json`)

The modern format uses `EvalSet` → `EvalCase` → `Invocation` → `IntermediateData` hierarchy (camelCase JSON):

```json
{
  "evalSetId": "research_agent_tests",
  "name": "Research Agent Evaluation",
  "description": "Tests for research assistant pipeline",
  "evalCases": [
    {
      "evalId": "basic_research_query",
      "sessionInput": {
        "appName": "research_agent",
        "userId": "test_user",
        "state": {}
      },
      "conversation": [
        {
          "invocationId": "inv-1",
          "userContent": {
            "role": "user",
            "parts": [{"text": "Research the topic of machine learning"}]
          },
          "finalResponse": {
            "role": "model",
            "parts": [{"text": "Here is a summary of machine learning research..."}]
          },
          "intermediateData": {
            "toolUses": [
              {"name": "search_articles", "args": {"topic": "machine learning"}},
              {"name": "get_topic_stats", "args": {"topic": "machine learning"}}
            ],
            "toolResponses": [
              {
                "name": "search_articles",
                "id": "call_1",
                "response": {
                  "topic": "machine learning",
                  "articles": [{"title": "Advances in ML", "source": "Nature"}]
                }
              }
            ],
            "intermediateResponses": []
          }
        }
      ]
    },
    {
      "evalId": "no_tool_needed",
      "conversation": [
        {
          "invocationId": "inv-2",
          "userContent": {
            "role": "user",
            "parts": [{"text": "What tools can you use?"}]
          },
          "finalResponse": {
            "role": "model",
            "parts": [{"text": "I can search articles and get topic statistics."}]
          },
          "intermediateData": {
            "toolUses": [],
            "toolResponses": []
          }
        }
      ]
    }
  ]
}
```

**Key types (from `google.adk.evaluation`):**

| Type | Purpose |
|------|---------|
| `EvalSet` | Top-level container with `eval_set_id`, `eval_cases` |
| `EvalCase` | Single test case with `conversation` (static) or `conversation_scenario` (dynamic) — mutually exclusive |
| `Invocation` | One conversation turn: `user_content`, `final_response`, `intermediate_data`, optional `rubrics` |
| `IntermediateData` | Expected tool trajectory: `tool_uses` (list of `FunctionCall`), `tool_responses` (list of `FunctionResponse`) |
| `SessionInput` | Initial session: `app_name`, `user_id`, `state` dict |
| `Rubric` | Quality rubric: `rubric_id`, `rubric_content` (with `text_property`), optional `type` |

**Note on `toolResponses`:** These store the **expected** tool return values as reference data for evaluation metrics (e.g., `hallucinations_v1` can check if the agent's final response is grounded in what the tools returned). They are **not** injected into the agent — the agent calls its real tools during evaluation.

### Legacy Format (`.test.json`)

The simpler legacy format is still supported and auto-converted internally:

```json
[
  {
    "name": "basic_research_query",
    "data": [
      {
        "query": "Research the topic of machine learning",
        "expected_tool_use": [
          {"tool_name": "search_articles", "tool_input": {"topic": "machine learning"}},
          {"tool_name": "get_topic_stats", "tool_input": {"topic": "machine learning"}}
        ],
        "reference": "machine learning research summary"
      }
    ]
  }
]
```

Migrate legacy files with: `AgentEvaluator.migrate_eval_data_to_new_schema("old.test.json")`

### Eval Configuration (`test_config.json`)

Configure metrics, thresholds, match types, and judge models:

```json
{
  "criteria": {
    "tool_trajectory_avg_score": {
      "threshold": 0.9,
      "match_type": "IN_ORDER"
    },
    "response_match_score": 0.8,
    "rubric_based_final_response_quality_v1": {
      "threshold": 0.8,
      "judge_model_options": {
        "judge_model": "gemini-2.5-flash",
        "num_samples": 5
      }
    },
    "hallucinations_v1": {
      "threshold": 0.9,
      "evaluate_intermediate_nl_responses": true
    },
    "safety_v1": 1.0
  }
}
```

## Running Evaluations

### CLI

```bash
# Run eval set against agent
adk eval my_agent my_agent/tests.evalset.json

# With config file for custom thresholds/metrics
adk eval my_agent my_agent/tests.evalset.json --config_file_path test_config.json

# Print detailed per-invocation results
adk eval my_agent my_agent/tests.evalset.json --print_detailed_results
```

### Programmatic API (`AgentEvaluator`)

```python
import asyncio
from google.adk.evaluation import AgentEvaluator

# Evaluate from file (raises AssertionError if any metric fails threshold)
asyncio.run(AgentEvaluator.evaluate(
    agent_module="my_agent",
    eval_dataset_file_path_or_dir="my_agent/tests.evalset.json",
    config_file_path="test_config.json",  # optional
    num_runs=2,
    print_detailed_results=True,
))

# Evaluate from EvalSet object (for programmatic test construction)
from google.adk.evaluation import EvalSet, EvalCase, Invocation, IntermediateData
from google.genai import types as genai_types

eval_set = EvalSet(
    eval_set_id="programmatic_tests",
    eval_cases=[
        EvalCase(
            eval_id="test_1",
            conversation=[
                Invocation(
                    user_content=genai_types.Content(
                        parts=[genai_types.Part(text="Research machine learning")]
                    ),
                    final_response=genai_types.Content(
                        parts=[genai_types.Part(text="Here is a summary...")]
                    ),
                    intermediate_data=IntermediateData(
                        tool_uses=[
                            genai_types.FunctionCall(
                                name="search_articles",
                                args={"topic": "machine learning"},
                            ),
                        ]
                    ),
                )
            ],
        )
    ],
)

asyncio.run(AgentEvaluator.evaluate_eval_set(
    agent_module="my_agent",
    eval_set=eval_set,
    criteria={"tool_trajectory_avg_score": 1.0, "response_match_score": 0.8},
    num_runs=2,
))
```

### Dev UI

```bash
adk web
# Navigate to agent -> Tests tab
# Run tests interactively
# Inspect events, state changes, latency
```

## Evaluation-Based Unit Tests

Unit tests in ADK use eval files with **golden trajectories** — define expected tool call sequences in `.evalset.json` files, then run the agent against them and compare actual vs. expected trajectories.

### ADK Eval Files with Expected Tool Trajectories

Define expected tool calls and responses in `.evalset.json`. The `intermediateData.toolUses` field specifies the golden trajectory the agent should follow:

```json
{
  "evalSetId": "research_agent_unit",
  "evalCases": [
    {
      "evalId": "happy_path_basic_research",
      "conversation": [
        {
          "invocationId": "inv-1",
          "userContent": {"role": "user", "parts": [{"text": "Research machine learning"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Here is a summary of ML research..."}]},
          "intermediateData": {
            "toolUses": [
              {"name": "search_articles", "args": {"topic": "machine learning"}},
              {"name": "get_topic_stats", "args": {"topic": "machine learning"}}
            ],
            "toolResponses": [
              {
                "name": "search_articles", "id": "call_1",
                "response": {"topic": "machine learning", "articles": [{"title": "ML Advances"}]}
              },
              {
                "name": "get_topic_stats", "id": "call_2",
                "response": {"topic": "machine learning", "total_publications": 15000}
              }
            ]
          }
        }
      ]
    },
    {
      "evalId": "failure_no_tool_for_greeting",
      "conversation": [
        {
          "invocationId": "inv-2",
          "userContent": {"role": "user", "parts": [{"text": "Hello, how are you?"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Hello! How can I help?"}]},
          "intermediateData": {
            "toolUses": [],
            "toolResponses": []
          }
        }
      ]
    }
  ]
}
```

Run with strict trajectory matching:

```json
// test_config.json
{
  "criteria": {
    "tool_trajectory_avg_score": {"threshold": 1.0, "match_type": "EXACT"},
    "response_match_score": 0.7
  }
}
```

```bash
adk eval research_agent research_agent/tests.evalset.json --config_file_path test_config.json
```

Or run in pytest:

```python
import pytest
from google.adk.evaluation import AgentEvaluator

@pytest.mark.asyncio
async def test_research_trajectories():
    """ADK evaluates the real agent against golden tool trajectories."""
    await AgentEvaluator.evaluate(
        agent_module="research_agent",
        eval_dataset_file_path_or_dir="research_agent/tests.evalset.json",
        config_file_path="test_config.json",
        num_runs=2,
    )
    # Raises AssertionError if any metric falls below threshold
```

### Parametrized Tests from Eval Data

Load test cases from your `.evalset.json` and use them to drive parametrized Python tests:

```python
import json
import pytest

def load_eval_cases(path):
    with open(path) as f:
        data = json.load(f)
    return data.get("evalCases", [])

EVAL_CASES = load_eval_cases("research_agent/tests.evalset.json")

@pytest.mark.parametrize(
    "case",
    EVAL_CASES,
    ids=[c["evalId"] for c in EVAL_CASES],
)
def test_expected_tool_names(case):
    """Verify each eval case has valid tool names matching the agent's tools."""
    from research_agent.tools import search_articles, get_topic_stats, format_citation
    known_tools = {"search_articles", "get_topic_stats", "format_citation"}

    for invocation in case.get("conversation", []):
        intermediate = invocation.get("intermediateData", {})
        for tool_use in intermediate.get("toolUses", []):
            assert tool_use["name"] in known_tools, (
                f"Unknown tool '{tool_use['name']}' in eval case '{case['evalId']}'"
            )
```

## Functional / Integration Tests

Integration tests run the **full agent pipeline** with a real LLM. Use `AgentEvaluator.evaluate()` with `.evalset.json` files to test end-to-end behavior including tool selection, state management, and response quality.

### Running Integration Tests with AgentEvaluator

Create an eval set that covers the happy paths and failure trajectories for each task, then evaluate programmatically:

```python
# test_integration.py
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_order_lookup_integration():
    """Full integration: real LLM, real tools, trajectory validation."""
    await AgentEvaluator.evaluate(
        agent_module="my_agent",
        eval_dataset_file_path_or_dir="tests/order_lookup.evalset.json",
        config_file_path="tests/test_config.json",
        num_runs=1,
    )

@pytest.mark.asyncio
async def test_full_agent_eval_suite():
    """Run all integration eval cases in the tests directory."""
    await AgentEvaluator.evaluate(
        agent_module="my_agent",
        eval_dataset_file_path_or_dir="tests/",
        num_runs=2,
        print_detailed_results=True,
    )
    # Raises AssertionError if any metric falls below configured threshold
```

**Eval set covering happy and failure paths (tests/order_lookup.evalset.json):**

```json
{
  "evalSetId": "order_lookup_integration",
  "evalCases": [
    {
      "evalId": "happy_path_order_by_id",
      "conversation": [
        {
          "invocationId": "inv-1",
          "userContent": {"role": "user", "parts": [{"text": "What's the status of order ORD-12345?"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Order ORD-12345 has been shipped."}]},
          "intermediateData": {
            "toolUses": [{"name": "lookup_order", "args": {"order_id": "ORD-12345"}}],
            "toolResponses": []
          }
        }
      ]
    },
    {
      "evalId": "happy_path_standard_refund",
      "conversation": [
        {
          "invocationId": "inv-2",
          "userContent": {"role": "user", "parts": [{"text": "I want to return order ORD-100 and get a refund"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Your refund for order ORD-100 has been processed."}]},
          "intermediateData": {
            "toolUses": [
              {"name": "lookup_order", "args": {"order_id": "ORD-100"}},
              {"name": "check_refund_eligibility", "args": {"order_id": "ORD-100"}},
              {"name": "process_refund", "args": {"order_id": "ORD-100", "amount": 49.99}}
            ],
            "toolResponses": []
          }
        }
      ]
    },
    {
      "evalId": "failure_ineligible_refund",
      "conversation": [
        {
          "invocationId": "inv-3",
          "userContent": {"role": "user", "parts": [{"text": "Refund order ORD-OLD-001 please"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "I'm sorry, order ORD-OLD-001 is outside the return window."}]},
          "intermediateData": {
            "toolUses": [
              {"name": "lookup_order", "args": {"order_id": "ORD-OLD-001"}},
              {"name": "check_refund_eligibility", "args": {"order_id": "ORD-OLD-001"}}
            ],
            "toolResponses": []
          }
        }
      ]
    },
    {
      "evalId": "failure_ambiguous_input",
      "conversation": [
        {
          "invocationId": "inv-4",
          "userContent": {"role": "user", "parts": [{"text": "Where's my stuff?"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Could you provide your order ID or email address?"}]},
          "intermediateData": {
            "toolUses": [],
            "toolResponses": []
          }
        }
      ]
    }
  ]
}
```

Run via CLI or pytest:

```bash
adk eval my_agent tests/order_lookup.evalset.json --config_file_path tests/test_config.json
```

## Simulated Scenario Tests

ADK supports **user simulation** via `conversation_scenario` in `.evalset.json` files. An AI model dynamically generates user turns based on a `starting_prompt` and `conversation_plan`, enabling realistic multi-turn conversation testing without fixed prompts.

**Important constraint:** `conversation_scenario` is mutually exclusive with the `conversation` field in an `EvalCase`. When using user simulation, only `hallucinations_v1` and `safety_v1` criteria are supported.

### Conversation Scenario Format

```json
{
  "evalSetId": "customer_agent_scenarios",
  "evalCases": [
    {
      "evalId": "frustrated_customer_refund",
      "conversation_scenario": {
        "starting_prompt": "I bought a laptop 2 weeks ago and it arrived damaged. I want a full refund.",
        "conversation_plan": "Ask the agent to process a refund for order ORD-DMG-100. Provide the order ID when asked. Confirm the refund once the agent offers it. Signal completion when the refund is confirmed."
      }
    },
    {
      "evalId": "friendly_order_check",
      "conversation_scenario": {
        "starting_prompt": "Hi, I want to check on my recent order.",
        "conversation_plan": "Ask about order ORD-555. When asked for order ID or email, provide the order ID. Signal completion once the order status is received."
      }
    },
    {
      "evalId": "out_of_scope_request",
      "conversation_scenario": {
        "starting_prompt": "Can you help me write a Python script?",
        "conversation_plan": "Ask the agent to help with unrelated programming tasks. Signal completion after 2-3 turns."
      }
    }
  ]
}
```

### Running Scenario Tests

```bash
adk eval my_agent tests/scenarios.evalset.json --config_file_path tests/scenario_config.json
```

Config file (only `hallucinations_v1` and `safety_v1` work with user simulation):

```json
{
  "criteria": {
    "hallucinations_v1": 0.9,
    "safety_v1": 1.0
  },
  "user_simulator_config": {
    "model": "gemini-2.5-flash",
    "max_allowed_invocations": 20
  }
}
```

Or via pytest:

```python
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_scenario_tests():
    await AgentEvaluator.evaluate(
        agent_module="my_agent",
        eval_dataset_file_path_or_dir="tests/scenarios.evalset.json",
        config_file_path="tests/scenario_config.json",
    )
```

## Pytest Integration

Use `AgentEvaluator.evaluate()` to run eval files from pytest. The method raises `AssertionError` if any metric falls below its configured threshold, integrating naturally with pytest's assertion model.

```python
# test_weather_agent.py
import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

@pytest.mark.asyncio
async def test_weather_queries():
    """Run all weather agent eval cases."""
    await AgentEvaluator.evaluate(
        agent_module="weather_agent",
        eval_dataset_file_path_or_dir="weather_agent/tests.evalset.json",
        config_file_path="weather_agent/test_config.json",
    )

@pytest.mark.asyncio
async def test_weather_agent_from_directory():
    """Run all eval sets in the tests directory."""
    await AgentEvaluator.evaluate(
        agent_module="weather_agent",
        eval_dataset_file_path_or_dir="weather_agent/tests/",
        num_runs=2,
        print_detailed_results=True,
    )
```

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
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install google-adk pytest
      - run: pytest tests/ -v
      - run: adk eval my_agent my_agent/tests.evalset.json
      - uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: results.json
```

## Multi-Turn Evaluation

Multi-turn tests use the standard `.evalset.json` format with multiple `Invocation` entries in the `conversation` array — one per exchange. Each invocation captures the user message, expected tool calls, and expected final response for that turn.

### Multi-Turn Evalset Format

```json
{
  "evalSetId": "booking_agent_multiturn",
  "evalCases": [
    {
      "evalId": "booking_flow",
      "conversation": [
        {
          "invocationId": "inv-1",
          "userContent": {"role": "user", "parts": [{"text": "I want to book a flight"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Where would you like to fly?"}]},
          "intermediateData": {"toolUses": [], "toolResponses": []}
        },
        {
          "invocationId": "inv-2",
          "userContent": {"role": "user", "parts": [{"text": "From NYC to LA next Friday"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Here are the available flights..."}]},
          "intermediateData": {
            "toolUses": [{"name": "search_flights", "args": {"from": "NYC", "to": "LA", "date": "next Friday"}}],
            "toolResponses": []
          }
        },
        {
          "invocationId": "inv-3",
          "userContent": {"role": "user", "parts": [{"text": "Book the first one"}]},
          "finalResponse": {"role": "model", "parts": [{"text": "Your flight has been booked. Confirmation: FL-001."}]},
          "intermediateData": {
            "toolUses": [{"name": "create_booking", "args": {"flight_id": "FL-001"}}],
            "toolResponses": []
          }
        }
      ]
    }
  ]
}
```

For dynamic multi-turn simulations without fixed prompts, use `conversation_scenario` instead (see [Simulated Scenario Tests](#simulated-scenario-tests)).

## Best Practices

1. **Start with task/intent identification** - Map all tasks before writing a single test
2. **Map happy and failure trajectories** - Every task has at least one happy path and 2-3 failure modes
3. **Use all 9 built-in metrics as baseline** - Then select the relevant subset per task category
4. **Construct rubrics per task** - Present rubrics to the user for review before committing
5. **Test in layers** - eval-file trajectory tests first, then integration eval sets, then scenario tests
6. **Test tool sequences, not just outputs** - Verify the agent reasons correctly
7. **Include edge cases** - Empty inputs, invalid data, ambiguous queries
8. **Test error handling** - API failures, invalid tool arguments
9. **Use semantic matching** - Exact string matching is too brittle
10. **Version your test data** - Track test evolution with agent changes
11. **Monitor in production** - Evaluation is not just for development

### Test Coverage Checklist

```markdown
- [ ] Tasks/intents identified and documented
- [ ] Happy and failure trajectories mapped per task
- [ ] Rubrics defined and confirmed for each task category
- [ ] Eval trajectory tests for each happy/failure path
- [ ] Integration eval sets: happy path per tool
- [ ] Integration eval sets: tool selection with ambiguous input
- [ ] Integration eval sets: multi-tool sequences
- [ ] Integration eval sets: error recovery
- [ ] Integration eval sets: edge cases (empty, null, large inputs)
- [ ] Integration eval sets: state persistence across pipeline stages
- [ ] Scenario tests: realistic multi-turn conversations per task
- [ ] Scenario tests: adversarial / out-of-scope inputs
- [ ] Safety/guardrail triggers tested
- [ ] Rubric-based evals passing thresholds
```
