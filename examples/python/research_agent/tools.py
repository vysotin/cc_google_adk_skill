"""Custom tools for the research assistant agent."""

import random
from datetime import datetime


def search_articles(topic: str, max_results: int = 3) -> dict:
    """Search for research articles on a given topic.

    Args:
        topic: The research topic to search for (e.g., "machine learning", "climate change")
        max_results: Maximum number of articles to return (1-10)

    Returns:
        Dictionary with list of articles containing title, summary, and source
    """
    articles = [
        {
            "title": f"Advances in {topic}: A 2024 Review",
            "summary": f"This paper reviews recent developments in {topic}, highlighting key breakthroughs and future directions.",
            "source": "Journal of AI Research",
            "year": 2024,
        },
        {
            "title": f"Understanding {topic}: Challenges and Opportunities",
            "summary": f"An analysis of current challenges in {topic} and emerging opportunities for researchers.",
            "source": "Nature Reviews",
            "year": 2024,
        },
        {
            "title": f"Practical Applications of {topic}",
            "summary": f"A survey of real-world applications of {topic} across different industries.",
            "source": "IEEE Transactions",
            "year": 2023,
        },
    ]
    return {
        "topic": topic,
        "articles": articles[:max_results],
        "total_found": len(articles),
        "search_date": datetime.now().isoformat(),
    }


def get_topic_stats(topic: str) -> dict:
    """Get publication statistics for a research topic.

    Args:
        topic: The research topic to get statistics for

    Returns:
        Dictionary with publication counts, growth rate, and top venues
    """
    return {
        "topic": topic,
        "total_publications": random.randint(5000, 50000),
        "publications_last_year": random.randint(500, 5000),
        "growth_rate_percent": round(random.uniform(5.0, 25.0), 1),
        "top_venues": [
            "Nature",
            "Science",
            "IEEE",
            "ACM",
        ],
        "trending_subtopics": [
            f"{topic} applications",
            f"{topic} ethics",
            f"automated {topic}",
        ],
    }


def format_citation(title: str, source: str, year: int) -> str:
    """Format a citation in a standard academic format.

    Args:
        title: The title of the article
        source: The publication source/journal
        year: The publication year

    Returns:
        Formatted citation string
    """
    return f'"{title}." {source}, {year}.'
