"""Pytest tests for the research assistant agent.

Tests tool functions directly (unit tests) since integration tests
require a valid GOOGLE_API_KEY for LLM calls.
"""

import pytest
from research_agent.tools import search_articles, get_topic_stats, format_citation


class TestSearchArticles:
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


class TestGetTopicStats:
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
    def test_formats_correctly(self):
        citation = format_citation("Test Paper", "Nature", 2024)
        assert citation == '"Test Paper." Nature, 2024.'

    def test_different_inputs(self):
        citation = format_citation("AI Survey", "IEEE", 2023)
        assert "AI Survey" in citation
        assert "IEEE" in citation
        assert "2023" in citation


class TestAgentStructure:
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
