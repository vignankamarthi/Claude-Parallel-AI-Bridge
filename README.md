# Parallel AI MCP Server

A Model Context Protocol (MCP) server that integrates Parallel AI's deep research API with Claude Desktop for architecture research with structured citations.

**Author**: Vignan Kamarthi

## Overview

This MCP server provides Claude Desktop with access to Parallel AI's enterprise research API, enabling deep architecture research with citation-backed answers. The integration supports multiple processor tiers (from quick fact retrieval to extensive SOTA research) with user approval workflows for cost management.

## Features

- **Deep Research**: Access Parallel AI's research API for architecture decisions
- **Structured Citations**: Field-level citations with URLs, excerpts, confidence scores, and reasoning
- **Multiple Processor Tiers**: 9 tiers from Lite ($5/1K) to Ultra8x ($2,400/1K)
- **Approval Workflow**: User consent required before expensive API calls with cost/time estimates
- **Progress Reporting**: Real-time updates during long-running research operations
- **Quick Research**: Fast Lite processor mode for basic queries without approval
- **Comprehensive Logging**: Production-ready logging with timestamped console output

## Installation

### Prerequisites

- Python 3.8+
- Claude Desktop
- Parallel AI API key (get one at [parallel.ai](https://www.parallel.ai))

### Setup

1. Clone this repository:
```bash
git clone <repository-url>
cd Claude-Parallel-AI-Integration
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
```

Edit `.env` and add your Parallel AI API key:
```
PARALLEL_API_KEY=your_api_key_here
DEFAULT_PROCESSOR=pro
```

5. Configure Claude Desktop:

Copy `claude_desktop_config.json.example` to your Claude Desktop config location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Update the path in the config:
```json
{
  "mcpServers": {
    "parallel-research": {
      "command": "python",
      "args": [
        "/full/path/to/your/project/server.py"
      ],
      "env": {
        "PARALLEL_API_KEY": "${PARALLEL_API_KEY}"
      }
    }
  }
}
```

6. Restart Claude Desktop

## Usage

### Research Architecture Decision

The main tool for comprehensive research:

```
Use the research_architecture_decision tool to research:
"Compare OAuth 2.1 vs JWT authentication for microservices"
```

You will be prompted to approve the research with cost/time estimates before execution.

### Quick Research

For fast, low-cost queries (no approval required):

```
Use the quick_research tool to answer:
"What is OAuth 2.1?"
```

### Session Start

Access the research session prompt for usage instructions:

```
Use the research_session_start prompt
```

## Processor Tiers

Choose the appropriate processor based on your research needs:

| Tier | Cost | Latency | Use Case |
|------|------|---------|----------|
| lite | $5/1K | 5-60s | Basic fact retrieval |
| base | $10/1K | 15-100s | Standard research |
| core | $30/1K | 1-5min | When Pro is overkill |
| core2x | $60/1K | 1-5min | Enhanced core (2x multiplier) |
| **pro** | **$100/1K** | **3-9min** | **Architecture decisions (default)** |
| ultra | $300/1K | 5-25min | Extensive research |
| ultra2x | $600/1K | 5-25min | 2x ultra |
| ultra4x | $1,200/1K | 8-30min | 4x ultra |
| ultra8x | $2,400/1K | 8-30min | 8x ultra (SOTA) |

## API Reference

### Tools

#### `research_architecture_decision`

Conduct deep research for architecture decisions with structured citations.

**Parameters**:
- `query` (str): Research question
- `processor` (str, optional): Processor tier (default: "pro")

**Returns**:
```python
{
    "status": "complete" | "cancelled" | "error",
    "content": str,  # Synthesized research answer
    "citations": [   # Structured citations
        {
            "field": str,
            "citations": [
                {
                    "url": str,
                    "excerpts": [str],
                    "title": str
                }
            ],
            "confidence": float,
            "reasoning": str
        }
    ],
    "processor": str,
    "run_id": str
}
```

#### `quick_research`

Quick research using Lite processor (5-60s, $5/1K queries). No approval required.

**Parameters**:
- `query` (str): Research question

**Returns**:
```python
{
    "status": "complete" | "error",
    "content": str,
    "processor": "lite",
    "run_id": str
}
```

### Prompts

#### `research_session_start`

Generate session start prompt with usage instructions.

## License

MIT License - see [LICENSE](LICENSE) file for details.

Copyright (c) 2025 Vismay Kamarthi
