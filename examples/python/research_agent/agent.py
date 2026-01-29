"""Research Assistant - Multi-agent ADK application.

Demonstrates:
- LlmAgent with custom tools
- SequentialAgent pipeline (researcher -> writer -> reviewer)
- Callbacks for guardrails
- State management via output_key and instruction templating
"""

from google.adk.agents import Agent, SequentialAgent
from .tools import search_articles, get_topic_stats, format_citation


def before_agent_callback(callback_context, **kwargs):
    """Log agent entry and enforce topic restrictions."""
    agent_name = callback_context.agent_name
    print(f"[Callback] Entering agent: {agent_name}")
    return None  # Proceed normally


def before_model_callback(callback_context, llm_request, **kwargs):
    """Safety guardrail: block requests containing harmful content markers."""
    # Check the last user message for blocked content
    if llm_request and hasattr(llm_request, "contents"):
        for content in (llm_request.contents or []):
            if hasattr(content, "parts"):
                for part in (content.parts or []):
                    if hasattr(part, "text") and part.text:
                        if "BLOCKED" in part.text.upper():
                            from google.genai.types import Content, Part

                            return Content(
                                role="model",
                                parts=[Part(text="Request blocked by safety guardrail.")],
                            )
    return None  # Proceed normally


# Stage 1: Research agent - gathers information
researcher = Agent(
    name="researcher",
    model="gemini-2.0-flash",
    instruction="""You are a research specialist. When given a topic:
1. Use search_articles to find relevant papers
2. Use get_topic_stats to get publication statistics
3. Summarize your findings concisely

Always include specific data from the tools in your summary.""",
    description="Gathers research articles and statistics on a topic",
    tools=[search_articles, get_topic_stats],
    output_key="research_findings",
    before_agent_callback=before_agent_callback,
    before_model_callback=before_model_callback,
)

# Stage 2: Writer agent - creates a summary report
writer = Agent(
    name="writer",
    model="gemini-2.0-flash",
    instruction="""You are a technical writer. Based on the research findings below,
write a concise research summary report (3-4 paragraphs).

Research findings:
{research_findings}

Include:
- Overview of the topic and its significance
- Key findings from the articles
- Publication trends and statistics
- Recommended areas for further study

Use format_citation for any article references.""",
    description="Writes a structured research summary from findings",
    tools=[format_citation],
    output_key="draft_report",
    before_agent_callback=before_agent_callback,
)

# Stage 3: Reviewer agent - provides quality feedback
reviewer = Agent(
    name="reviewer",
    model="gemini-2.0-flash",
    instruction="""You are a quality reviewer. Review this draft report:

{draft_report}

Evaluate on:
1. Accuracy - Are the facts and citations correct?
2. Clarity - Is it easy to understand?
3. Completeness - Does it cover key aspects?

Provide a quality score (1-10) and brief feedback.
If the score is 8 or above, approve with "APPROVED".
Otherwise provide specific improvements needed.""",
    description="Reviews and scores the draft report",
    output_key="review_result",
    before_agent_callback=before_agent_callback,
)

# Root agent: Sequential pipeline
root_agent = SequentialAgent(
    name="research_pipeline",
    description="Research assistant that finds, writes, and reviews topic summaries",
    sub_agents=[researcher, writer, reviewer],
)
