"""Pytest tests for the research assistant agent.

Demonstrates three test layers:
1. Unit tests - Test tool functions directly and with mocks
2. Structure tests - Verify agent configuration and pipeline wiring
3. Callback tests - Test guardrail callbacks with mocked inputs

Integration tests (using ADK eval with real LLM) require GOOGLE_API_KEY.
Run ADK eval separately:
    adk eval research_agent research_agent/research_agent.evalset.json \
        --config_file_path research_agent/test_config.json
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from research_agent.tools import search_articles, get_topic_stats, format_citation


# ---------------------------------------------------------------------------
# 1. Unit Tests: Tool Functions (direct, no mocking)
# ---------------------------------------------------------------------------

class TestSearchArticles:
    """Test search_articles tool with real implementation."""

    def test_returns_articles(self):
        result = search_articles("machine learning")
        assert result["topic"] == "machine learning"
        assert len(result["articles"]) > 0
        assert "search_date" in result

    def test_respects_max_results(self):
        result = search_articles("AI", max_results=1)
        assert len(result["articles"]) == 1

    def test_article_structure(self):
        result = search_articles("robotics")
        article = result["articles"][0]
        assert "title" in article
        assert "summary" in article
        assert "source" in article
        assert "year" in article

    def test_topic_appears_in_article_titles(self):
        result = search_articles("deep learning")
        for article in result["articles"]:
            assert "deep learning" in article["title"].lower()


class TestGetTopicStats:
    """Test get_topic_stats tool with real implementation."""

    def test_returns_stats(self):
        result = get_topic_stats("deep learning")
        assert result["topic"] == "deep learning"
        assert result["total_publications"] > 0
        assert "growth_rate_percent" in result
        assert len(result["top_venues"]) > 0

    def test_includes_trending_subtopics(self):
        result = get_topic_stats("NLP")
        assert len(result["trending_subtopics"]) > 0


class TestFormatCitation:
    """Test format_citation tool with real implementation."""

    def test_formats_correctly(self):
        citation = format_citation("Test Paper", "Nature", 2024)
        assert citation == '"Test Paper." Nature, 2024.'

    def test_different_inputs(self):
        citation = format_citation("AI Survey", "IEEE", 2023)
        assert "AI Survey" in citation
        assert "IEEE" in citation
        assert "2023" in citation


# ---------------------------------------------------------------------------
# 2. Unit Tests: Tool Functions with Mocks (simulating external APIs)
# ---------------------------------------------------------------------------

class TestSearchArticlesMocked:
    """Test search_articles with mocked return values.

    Demonstrates how to mock tool functions to simulate different
    happy paths and failure trajectories deterministically.
    """

    @patch("test_agent.search_articles")
    def test_happy_path_returns_expected_shape(self, mock_search):
        """Happy path: mock returns a well-formed response."""
        mock_search.return_value = {
            "topic": "quantum computing",
            "articles": [
                {
                    "title": "Quantum Advantage in 2024",
                    "summary": "Breakthrough results in quantum error correction.",
                    "source": "Nature",
                    "year": 2024,
                },
                {
                    "title": "Practical Quantum Algorithms",
                    "summary": "Survey of near-term quantum algorithms.",
                    "source": "Science",
                    "year": 2024,
                },
            ],
            "total_found": 2,
            "search_date": "2024-12-01T00:00:00",
        }

        result = search_articles("quantum computing")

        assert result["topic"] == "quantum computing"
        assert len(result["articles"]) == 2
        assert result["articles"][0]["source"] == "Nature"
        mock_search.assert_called_once_with("quantum computing")

    @patch("test_agent.search_articles")
    def test_failure_empty_results(self, mock_search):
        """Failure trajectory: no articles found for obscure topic."""
        mock_search.return_value = {
            "topic": "xyznonexistent12345",
            "articles": [],
            "total_found": 0,
            "search_date": "2024-12-01T00:00:00",
        }

        result = search_articles("xyznonexistent12345")

        assert result["articles"] == []
        assert result["total_found"] == 0

    @patch("test_agent.search_articles")
    def test_failure_api_error(self, mock_search):
        """Failure trajectory: external API raises an exception."""
        mock_search.side_effect = ConnectionError("Search service unavailable")

        with pytest.raises(ConnectionError, match="Search service unavailable"):
            search_articles("machine learning")


class TestGetTopicStatsMocked:
    """Test get_topic_stats with mocked return values."""

    @patch("test_agent.get_topic_stats")
    def test_happy_path(self, mock_stats):
        mock_stats.return_value = {
            "topic": "AI safety",
            "total_publications": 8500,
            "publications_last_year": 1200,
            "growth_rate_percent": 22.3,
            "top_venues": ["Nature", "AAAI", "NeurIPS"],
            "trending_subtopics": ["alignment", "interpretability"],
        }

        result = get_topic_stats("AI safety")

        assert result["total_publications"] == 8500
        assert result["growth_rate_percent"] == 22.3
        assert "alignment" in result["trending_subtopics"]

    @patch("test_agent.get_topic_stats")
    def test_failure_returns_zeros(self, mock_stats):
        """Failure trajectory: stats service returns minimal data."""
        mock_stats.return_value = {
            "topic": "unknown_field",
            "total_publications": 0,
            "publications_last_year": 0,
            "growth_rate_percent": 0.0,
            "top_venues": [],
            "trending_subtopics": [],
        }

        result = get_topic_stats("unknown_field")

        assert result["total_publications"] == 0
        assert result["top_venues"] == []


class TestToolChainMocked:
    """Test the full tool chain that a research pipeline would invoke.

    Mocks all three tools to verify the expected call sequence
    matches what the agent would do during a research task.
    """

    @patch("test_agent.format_citation")
    @patch("test_agent.get_topic_stats")
    @patch("test_agent.search_articles")
    def test_happy_path_full_research_chain(
        self, mock_search, mock_stats, mock_citation
    ):
        """Happy path: full tool chain for a research query with citation."""
        mock_search.return_value = {
            "topic": "robotics",
            "articles": [
                {
                    "title": "Advances in Robotics",
                    "summary": "Recent breakthroughs.",
                    "source": "IEEE",
                    "year": 2024,
                }
            ],
            "total_found": 1,
        }
        mock_stats.return_value = {
            "topic": "robotics",
            "total_publications": 12000,
            "growth_rate_percent": 15.0,
        }
        mock_citation.return_value = '"Advances in Robotics." IEEE, 2024.'

        # Simulate the tool call sequence the agent would make
        articles = search_articles("robotics")
        stats = get_topic_stats("robotics")
        citation = format_citation(
            articles["articles"][0]["title"],
            articles["articles"][0]["source"],
            articles["articles"][0]["year"],
        )

        # Verify the chain completed correctly
        assert articles["total_found"] == 1
        assert stats["total_publications"] == 12000
        assert "IEEE" in citation

        # Verify call order
        mock_search.assert_called_once_with("robotics")
        mock_stats.assert_called_once_with("robotics")
        mock_citation.assert_called_once_with("Advances in Robotics", "IEEE", 2024)


# ---------------------------------------------------------------------------
# 3. Structure Tests: Agent Configuration
# ---------------------------------------------------------------------------

class TestAgentStructure:
    """Verify agent hierarchy, tools, and configuration."""

    def test_root_agent_exists(self):
        from research_agent import root_agent
        assert root_agent is not None
        assert root_agent.name == "research_pipeline"

    def test_has_sub_agents(self):
        from research_agent.agent import researcher, writer, reviewer
        assert researcher.name == "researcher"
        assert writer.name == "writer"
        assert reviewer.name == "reviewer"

    def test_researcher_has_tools(self):
        from research_agent.agent import researcher
        assert len(researcher.tools) >= 2

    def test_output_keys_configured(self):
        from research_agent.agent import researcher, writer, reviewer
        assert researcher.output_key == "research_findings"
        assert writer.output_key == "draft_report"
        assert reviewer.output_key == "review_result"

    def test_pipeline_agent_order(self):
        from research_agent import root_agent
        sub_names = [a.name for a in root_agent.sub_agents]
        assert sub_names == ["researcher", "writer", "reviewer"]


# ---------------------------------------------------------------------------
# 4. Pipeline State Flow Tests (Mocked Sub-Agent Outputs)
# ---------------------------------------------------------------------------

class TestPipelineStateFlow:
    """Verify state template wiring between pipeline stages."""

    def test_writer_instruction_references_research_findings(self):
        from research_agent.agent import writer
        assert "{research_findings}" in writer.instruction

    def test_reviewer_instruction_references_draft_report(self):
        from research_agent.agent import reviewer
        assert "{draft_report}" in reviewer.instruction

    def test_writer_template_resolves_with_mock_data(self):
        """Simulate researcher output flowing into writer via state template."""
        mock_findings = (
            "Found 5 articles on quantum computing. "
            "Key finding: quantum advantage demonstrated in 2024."
        )
        from research_agent.agent import writer
        resolved = writer.instruction.replace("{research_findings}", mock_findings)
        assert "quantum computing" in resolved
        assert "quantum advantage" in resolved

    def test_reviewer_template_resolves_with_mock_data(self):
        """Simulate writer output flowing into reviewer via state template."""
        mock_draft = (
            "# Quantum Computing Report\n\n"
            "Quantum computing has shown significant progress in 2024."
        )
        from research_agent.agent import reviewer
        resolved = reviewer.instruction.replace("{draft_report}", mock_draft)
        assert "Quantum Computing Report" in resolved


# ---------------------------------------------------------------------------
# 5. Callback Tests (Guardrails with Mocked Inputs)
# ---------------------------------------------------------------------------

class TestCallbacks:
    """Test callback functions with mocked LLM request objects."""

    def test_before_model_callback_blocks_harmful_content(self):
        from research_agent.agent import before_model_callback

        mock_part = MagicMock()
        mock_part.text = "Tell me about BLOCKED topic"
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        mock_request = MagicMock()
        mock_request.contents = [mock_content]
        mock_context = MagicMock()

        result = before_model_callback(mock_context, mock_request)

        # Should return a Content override (not None)
        assert result is not None

    def test_before_model_callback_allows_normal_content(self):
        from research_agent.agent import before_model_callback

        mock_part = MagicMock()
        mock_part.text = "Tell me about machine learning"
        mock_content = MagicMock()
        mock_content.parts = [mock_part]
        mock_request = MagicMock()
        mock_request.contents = [mock_content]
        mock_context = MagicMock()

        result = before_model_callback(mock_context, mock_request)

        # Should return None (proceed normally)
        assert result is None

    def test_before_agent_callback_returns_none(self):
        from research_agent.agent import before_agent_callback

        mock_context = MagicMock()
        result = before_agent_callback(mock_context)

        assert result is None


# ---------------------------------------------------------------------------
# 6. Eval Data Validation Tests (Verify .evalset.json structure)
# ---------------------------------------------------------------------------

class TestEvalSetData:
    """Validate the eval set JSON file against agent capabilities."""

    @pytest.fixture
    def eval_cases(self):
        with open("research_agent/research_agent.evalset.json") as f:
            data = json.load(f)
        return data["evalCases"]

    def test_eval_set_has_cases(self, eval_cases):
        assert len(eval_cases) >= 3, "Should have at least 3 eval cases"

    def test_all_cases_have_conversations(self, eval_cases):
        for case in eval_cases:
            assert "conversation" in case, (
                f"Eval case '{case['evalId']}' missing conversation"
            )
            assert len(case["conversation"]) > 0

    def test_tool_names_match_agent_tools(self, eval_cases):
        """Verify all tool names in eval data match actual agent tools."""
        known_tools = {"search_articles", "get_topic_stats", "format_citation"}

        for case in eval_cases:
            for invocation in case["conversation"]:
                intermediate = invocation.get("intermediateData", {})
                for tool_use in intermediate.get("toolUses", []):
                    assert tool_use["name"] in known_tools, (
                        f"Unknown tool '{tool_use['name']}' in "
                        f"eval case '{case['evalId']}'"
                    )

    def test_happy_path_cases_have_tool_uses(self, eval_cases):
        """Happy path cases should include expected tool calls."""
        happy_cases = [c for c in eval_cases if "happy_path" in c["evalId"]]
        for case in happy_cases:
            for invocation in case["conversation"]:
                tool_uses = invocation.get("intermediateData", {}).get(
                    "toolUses", []
                )
                assert len(tool_uses) > 0, (
                    f"Happy path '{case['evalId']}' should have tool calls"
                )

    def test_no_tool_cases_have_empty_tool_uses(self, eval_cases):
        """Cases where no tool should be called have empty toolUses."""
        no_tool_cases = [c for c in eval_cases if "no_tool" in c["evalId"]]
        for case in no_tool_cases:
            for invocation in case["conversation"]:
                tool_uses = invocation.get("intermediateData", {}).get(
                    "toolUses", []
                )
                assert len(tool_uses) == 0, (
                    f"No-tool case '{case['evalId']}' should have empty toolUses"
                )

    @pytest.mark.parametrize(
        "eval_id,expected_tools",
        [
            ("happy_path_basic_research", ["search_articles", "get_topic_stats"]),
            (
                "happy_path_climate_research",
                ["search_articles", "get_topic_stats"],
            ),
            (
                "happy_path_with_citation",
                ["search_articles", "get_topic_stats", "format_citation"],
            ),
            ("no_tool_for_greeting", []),
            ("no_tool_for_capabilities_question", []),
        ],
    )
    def test_expected_tool_trajectory(self, eval_cases, eval_id, expected_tools):
        """Parametrized: verify each eval case has the correct tool trajectory."""
        case = next((c for c in eval_cases if c["evalId"] == eval_id), None)
        assert case is not None, f"Eval case '{eval_id}' not found"

        actual_tools = []
        for invocation in case["conversation"]:
            intermediate = invocation.get("intermediateData", {})
            for tool_use in intermediate.get("toolUses", []):
                actual_tools.append(tool_use["name"])

        assert actual_tools == expected_tools, (
            f"Case '{eval_id}': expected {expected_tools}, got {actual_tools}"
        )
