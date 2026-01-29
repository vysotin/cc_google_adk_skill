# Google ADK Skills

Comprehensive skills for building production-ready AI agents using [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/).

## Available Skills

### google-adk-python

Python-focused skill covering FastAPI, Flask, Streamlit, Slack, PubSub, A2A protocol, streaming, and deployment to Vertex AI/Cloud Run/GKE.

### google-adk-typescript

TypeScript-focused skill covering FunctionTool with Zod schemas, Express, Hono, custom agents with `runAsyncImpl`, and deployment to Cloud Run.

### Shared Coverage

Both skills cover:

- **Agent types** - LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, custom agents
- **Tool development** - Function tools, MCP tools, OpenAPI tools
- **Multi-agent orchestration** - Coordinator/dispatcher, sequential pipeline, parallel fan-out, hierarchical decomposition, generator-critic, iterative refinement
- **Session & state management** - SessionService, state templating, state prefixes
- **Callbacks & guardrails** - Before/after hooks at agent, model, and tool levels
- **Testing & evaluation** - Trajectory metrics, test.json datasets, CI/CD integration
- **Deployment** - Cloud Run, Docker, containers

## Installation

### Claude Code

```bash
# Install a specific skill
claude skill install ./skills/google-adk-python
claude skill install ./skills/google-adk-typescript

# Or manually copy to your project
mkdir -p .claude/skills
cp -r skills/google-adk-python .claude/skills/
cp -r skills/google-adk-typescript .claude/skills/

# Or reference in .claude/settings.json
```

```json
{
  "skills": [
    "./skills/google-adk-python",
    "./skills/google-adk-typescript"
  ]
}
```

### Gemini CLI

The recommended approach is to use [skill-porter](https://github.com/jduncan-rva/skill-porter) to convert Claude Code skills to Gemini CLI extensions automatically:

```bash
# Install skill-porter
npx skill-porter convert ./skills/google-adk-python --to gemini
npx skill-porter convert ./skills/google-adk-typescript --to gemini
```

skill-porter handles metadata transformation (YAML frontmatter to JSON manifest), MCP configuration mapping, and tool restriction conversion. It achieves ~85% code reuse between platforms.


### OpenAI Codex CLI

Both Claude Code and Codex CLI use identical SKILL.md formats (YAML frontmatter + markdown), so symlinks mean changes to source skills instantly reflect in both tools.
So just copy skills to .codex/skills/ directory.
```bash
cp -r skills/google-adk-python .codex/skills/
cp -r skills/google-adk-typescript .codex/skills/
```

## Skill Structure

```
skills/
├── google-adk-python/
│   ├── SKILL.md
│   └── references/
│       ├── agents.md
│       ├── tools.md
│       ├── multi-agent.md
│       ├── testing.md
│       ├── ui-integrations.md
│       └── deployment.md
└── google-adk-typescript/
    ├── SKILL.md
    └── references/
        ├── agents.md
        ├── tools.md
        ├── multi-agent.md
        ├── callbacks.md
        ├── testing.md
        └── deployment.md
```

## Sources

- [Google ADK Official Documentation](https://google.github.io/adk-docs/)
- [Google ADK Python SDK](https://github.com/google/adk-python)
- [Google ADK TypeScript SDK](https://github.com/google/adk-js)
- [ADK Training Hub](https://github.com/raphaelmansuy/adk_training) by Raphael Mansuy
- [Google Developers Blog - ADK](https://developers.googleblog.com/en/agent-development-kit-easy-to-build-multi-agent-applications/)
- [Google Developers Blog - ADK TypeScript](https://developers.googleblog.com/introducing-agent-development-kit-for-typescript-build-ai-agents-with-the-power-of-a-code-first-approach/)
- [Google Cloud Documentation](https://docs.cloud.google.com/agent-builder/agent-development-kit/overview)

## License

These skills are provided as-is for use with AI coding assistants. The Google ADK framework is governed by its own [Apache 2.0 license](https://github.com/google/adk-python/blob/main/LICENSE).
