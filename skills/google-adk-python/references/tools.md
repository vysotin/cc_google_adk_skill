# Tool Development Guide

## Table of Contents
- [Function Tools](#function-tools)
- [Built-in Tools](#built-in-tools)
- [MCP Tools](#mcp-tools)
- [OpenAPI Tools](#openapi-tools)
- [AgentTool](#agenttool)
- [Tool Best Practices](#tool-best-practices)

## Function Tools

Custom Python functions as tools. The docstring and type hints become the tool schema.

### Basic Function Tool

```python
def get_stock_price(ticker: str) -> dict:
    """Get current stock price for a ticker symbol.

    Args:
        ticker: Stock ticker symbol (e.g., GOOGL, AAPL)

    Returns:
        Dictionary with price and change information
    """
    # Implementation
    return {"ticker": ticker, "price": 150.25, "change": "+2.3%"}

agent = Agent(
    name="stock_agent",
    tools=[get_stock_price]
)
```

### Async Function Tool

```python
async def fetch_data(url: str) -> dict:
    """Fetch data from a URL asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Tool with Context Access

```python
from google.adk.tools import ToolContext

def save_preference(ctx: ToolContext, key: str, value: str) -> str:
    """Save a user preference to session state."""
    ctx.session.state[key] = value
    return f"Saved {key}={value}"
```

### Tool with Structured Output

```python
from pydantic import BaseModel

class WeatherResult(BaseModel):
    city: str
    temperature: float
    condition: str
    humidity: int

def get_weather(city: str) -> WeatherResult:
    """Get weather for a city."""
    return WeatherResult(
        city=city,
        temperature=72.5,
        condition="sunny",
        humidity=45
    )
```

## Built-in Tools

### Google Search

```python
from google.adk.tools import google_search

agent = Agent(
    name="search_agent",
    tools=[google_search]
)
```

### Code Execution

```python
from google.adk.tools import code_execution

agent = Agent(
    name="coder",
    tools=[code_execution]  # Sandboxed Python execution
)
```

### Vertex AI Tools

```python
from google.adk.tools.vertexai import (
    vertex_ai_search,    # Enterprise search
    rag_retrieval,       # RAG Engine
    bigquery_tool,       # BigQuery queries
)

agent = Agent(
    name="enterprise_agent",
    tools=[vertex_ai_search, bigquery_tool]
)
```

## MCP Tools

Connect Model Context Protocol servers as tool providers.

### Local MCP Server

```python
from google.adk.tools.mcp import MCPToolset

# Connect to local MCP server
mcp_tools = MCPToolset.from_server(
    command="npx",
    args=["-y", "@anthropic/mcp-server-filesystem", "/path/to/dir"]
)

agent = Agent(
    name="file_agent",
    tools=[mcp_tools]
)
```

### Remote MCP Server

```python
mcp_tools = MCPToolset.from_url("http://mcp-server:8080")
```

### MCP with SSE Transport

```python
mcp_tools = MCPToolset.from_sse("http://mcp-server:8080/sse")
```

## OpenAPI Tools

Generate tools from OpenAPI specifications.

### From URL

```python
from google.adk.tools.openapi import OpenAPIToolset

tools = OpenAPIToolset.from_url(
    "https://api.example.com/openapi.json",
    auth={"api_key": "xxx"}  # Optional auth
)

agent = Agent(name="api_agent", tools=[tools])
```

### From File

```python
tools = OpenAPIToolset.from_file("./api_spec.yaml")
```

### Selective Operations

```python
tools = OpenAPIToolset.from_url(
    "https://api.example.com/openapi.json",
    operations=["getUser", "createOrder"]  # Only specific endpoints
)
```

## AgentTool

Wrap an agent as a callable tool for explicit invocation.

```python
from google.adk.tools import AgentTool

specialist = Agent(
    name="tax_specialist",
    instruction="Handle complex tax calculations."
)

coordinator = Agent(
    name="coordinator",
    instruction="Help with financial questions. Use tax_specialist for tax queries.",
    tools=[AgentTool(agent=specialist)]
)
```

## Tool Best Practices

### 1. Write Clear Docstrings

The LLM uses docstrings to understand when/how to use tools:

```python
# Good
def search_products(query: str, category: str = None, max_results: int = 10) -> list:
    """Search product catalog.

    Args:
        query: Search terms (e.g., "wireless headphones")
        category: Optional category filter (electronics, clothing, home)
        max_results: Maximum results to return (1-50)

    Returns:
        List of matching products with name, price, and rating
    """

# Bad
def search(q, cat=None, n=10):
    """Search stuff."""
```

### 2. Use Type Hints

```python
from typing import Optional, List
from pydantic import BaseModel, Field

class SearchParams(BaseModel):
    query: str = Field(description="Search terms")
    filters: Optional[List[str]] = Field(default=None, description="Filter tags")

def search(params: SearchParams) -> list:
    """Search with structured parameters."""
```

### 3. Handle Errors Gracefully

```python
def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {"status": "success", "data": response.json()}
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}
```

### 4. Avoid Side Effects in Tool Descriptions

```python
# Good - describes what it does
def delete_file(path: str) -> str:
    """Delete a file at the specified path. This action is irreversible."""

# Bad - hidden side effects
def process_file(path: str) -> str:
    """Process a file."""  # Doesn't mention it might delete things
```

### 5. Tool Constraints

Some tools cannot be combined. Check documentation for specific tools:

```python
# These may conflict - check docs
agent = Agent(
    tools=[google_search, code_execution]  # Verify compatibility
)
```
