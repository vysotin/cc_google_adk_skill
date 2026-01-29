# Testing and Evaluation Framework

## Table of Contents
- [Overview](#overview)
- [Test File Format](#test-file-format)
- [Evaluation Metrics](#evaluation-metrics)
- [Running Evaluations](#running-evaluations)
- [Pytest Integration](#pytest-integration)
- [Multi-Turn Evaluation](#multi-turn-evaluation)
- [Custom Evaluators](#custom-evaluators)

## Overview

ADK evaluation focuses on:
1. **Trajectory** - Did the agent call the right tools in the right order?
2. **Final Response** - Is the output correct and useful?
3. **Safety** - Is the response safe and grounded?

Deterministic pass/fail is often unsuitable for LLM agents due to model variability.

## Test File Format

Create `<agent_name>.test.json` alongside your agent:

```json
{
  "name": "weather_agent_tests",
  "description": "Tests for weather agent functionality",
  "data": [
    {
      "name": "basic_weather_query",
      "query": "What's the weather in New York?",
      "expected_tool_calls": ["get_weather"],
      "expected_tool_args": {
        "get_weather": {"city": "New York"}
      },
      "reference_answer": "The weather in New York"
    },
    {
      "name": "multi_city_query",
      "query": "Compare weather in NYC and LA",
      "expected_tool_calls": ["get_weather", "get_weather"],
      "reference_answer": "comparison of weather"
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
- `reference_answer` - Expected content (partial match)

## Evaluation Metrics

### Built-in Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| `tool_trajectory_avg_score` | Exact match of tool call sequence | Verify correct tool usage |
| `response_match_score` | ROUGE-1 similarity | Compare against reference |
| `final_response_match_v2` | LLM-judged semantic equivalence | Semantic correctness |
| `rubric_based_final_response_quality_v1` | Custom quality rubrics | Domain-specific quality |
| `rubric_based_tool_use_quality_v1` | Tool usage assessment | Evaluate tool selection |
| `hallucinations_v1` | Groundedness validation | Factual accuracy |
| `safety_v1` | Harmlessness checking | Safety compliance |

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

## Running Evaluations

### CLI

```bash
# Run all tests for an agent
adk eval my_agent

# Run specific test file
adk eval my_agent --test-file weather.test.json

# Verbose output
adk eval my_agent --verbose

# Output results to file
adk eval my_agent --output results.json
```

### Dev UI

```bash
adk web
# Navigate to agent → Tests tab
# Run tests interactively
# Inspect events, state changes, latency
```

## Pytest Integration

```python
# test_weather_agent.py
import pytest
from google.adk.evaluation import EvalRunner, load_test_file

@pytest.fixture
def eval_runner():
    from my_agent import root_agent
    return EvalRunner(agent=root_agent)

def test_weather_queries(eval_runner):
    test_cases = load_test_file("weather_agent.test.json")
    results = eval_runner.run(test_cases)

    for result in results:
        assert result.trajectory_score >= 0.9, \
            f"Test {result.name} failed: {result.trajectory_score}"

def test_single_case(eval_runner):
    result = eval_runner.run_single(
        query="What's the weather in Tokyo?",
        expected_tools=["get_weather"]
    )
    assert result.passed
    assert "Tokyo" in result.response

@pytest.mark.parametrize("city", ["London", "Paris", "Berlin"])
def test_multiple_cities(eval_runner, city):
    result = eval_runner.run_single(
        query=f"Weather in {city}?",
        expected_tools=["get_weather"]
    )
    assert city in result.response
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
      - run: adk eval my_agent --output results.json
      - uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: results.json
```

## Multi-Turn Evaluation

Test complex conversations with multiple exchanges.

### Evalset Format

```json
{
  "name": "conversation_tests",
  "type": "evalset",
  "sessions": [
    {
      "name": "booking_flow",
      "turns": [
        {
          "user": "I want to book a flight",
          "expected_tools": ["search_flights"],
          "expected_response_contains": "destination"
        },
        {
          "user": "From NYC to LA next Friday",
          "expected_tools": ["search_flights"],
          "expected_response_contains": "options"
        },
        {
          "user": "Book the first one",
          "expected_tools": ["create_booking"],
          "expected_response_contains": "confirmation"
        }
      ]
    }
  ]
}
```

### Simulated User Interactions

```python
from google.adk.evaluation import SimulatedUser

# LLM generates realistic follow-up queries
simulator = SimulatedUser(
    persona="Impatient customer who wants quick answers",
    goal="Book a flight to Hawaii"
)

results = eval_runner.run_simulated(
    agent=my_agent,
    simulator=simulator,
    max_turns=10
)
```

## Custom Evaluators

### Response Evaluator

```python
from google.adk.evaluation import Evaluator

class ToneEvaluator(Evaluator):
    """Evaluate response tone/style."""

    def evaluate(self, response: str, context: dict) -> float:
        # Check for professional tone
        negative_words = ["sorry", "unfortunately", "can't"]
        score = 1.0
        for word in negative_words:
            if word.lower() in response.lower():
                score -= 0.1
        return max(0.0, score)

# Use in tests
eval_runner = EvalRunner(
    agent=my_agent,
    evaluators=[ToneEvaluator()]
)
```

### Tool Usage Evaluator

```python
class EfficiencyEvaluator(Evaluator):
    """Penalize excessive tool calls."""

    def evaluate(self, trajectory: list, expected: list) -> float:
        if len(trajectory) <= len(expected):
            return 1.0
        # Penalize extra calls
        extra = len(trajectory) - len(expected)
        return max(0.0, 1.0 - (extra * 0.2))
```

## Best Practices

1. **Test tool sequences, not just outputs** - Verify the agent reasons correctly
2. **Include edge cases** - Empty inputs, invalid data, ambiguous queries
3. **Test error handling** - API failures, invalid tool arguments
4. **Use semantic matching** - Exact string matching is too brittle
5. **Version your test data** - Track test evolution with agent changes
6. **Monitor in production** - Evaluation isn't just for development

### Test Coverage Checklist

```markdown
- [ ] Happy path for each tool
- [ ] Tool selection with ambiguous input
- [ ] Multi-tool sequences
- [ ] Error recovery
- [ ] Edge cases (empty, null, large inputs)
- [ ] Safety/guardrail triggers
- [ ] Multi-turn conversations
- [ ] State persistence across turns
```
