# Parallel AI MCP Server

A Model Context Protocol (MCP) server that integrates Parallel AI's deep research API with Claude Desktop for comprehensive technical research with structured citations.

**Author**: Vignan Kamarthi

## Overview

This MCP server provides Claude Desktop with access to Parallel AI's enterprise research API, enabling deep technical research with citation-backed answers across software engineering, ML/AI, data engineering, and research domains. The integration supports async/parallel task execution, multiple processor tiers (from quick fact retrieval to extensive SOTA research), and user approval workflows for cost management.

## Features

- **Async/Parallel Execution**: Submit multiple research tasks simultaneously, continue working while research runs in background
- **Deep Research**: Comprehensive technical research with structured citations across all domains (Software, ML, Data, Research)
- **Structured Citations**: Field-level citations with URLs, excerpts, confidence scores, and reasoning
- **Multiple Processor Tiers**: 9 tiers from Lite ($5/1K) to Ultra8x ($2,400/1K)
- **Approval Workflow**: User consent required before expensive API calls with cost/time estimates
- **Task Status Tracking**: Check progress and results of async research tasks
- **Quick Research**: Fast Lite processor mode for basic queries without approval (no blocking)
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

Edit your Claude Desktop config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**IMPORTANT**: Use absolute paths and paste your actual API key:

```json
{
  "mcpServers": {
    "parallel-research": {
      "command": "/ABSOLUTE/PATH/TO/PROJECT/venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/PROJECT/server.py"],
      "env": {
        "PARALLEL_API_KEY": "your_actual_api_key_here",
        "DEFAULT_PROCESSOR": "pro"
      }
    }
  }
}
```

Replace:

- `/ABSOLUTE/PATH/TO/PROJECT/` with the full path to this project directory
- `your_actual_api_key_here` with your Parallel AI API key
- On Windows, use forward slashes or escaped backslashes in paths

6. Restart Claude Desktop

**Fully quit** Claude Desktop (not just close the window) and restart it to load the MCP server.

## Usage

### Deep Research (Async)

Submit comprehensive research tasks that run in background:

```
Use the deep_research tool to research:
"Compare OAuth 2.1 vs JWT authentication for microservices"
```

**Async execution**: Task returns immediately with task_id. Continue working while research runs in background (3-9 minutes).

**Domain examples:**

- Software: "Compare authentication approaches for microservices"
- ML/AI: "Compare focal loss vs weighted CE for imbalanced datasets"
- Data: "Compare Kafka vs Pulsar for streaming pipelines"
- Research: "Compare evaluation protocols for few-shot benchmarks"

### Quick Research (Sync)

For fast, low-cost queries (no approval required, returns immediately):

```
Use the quick_research tool to answer:
"What is OAuth 2.1?"
```

### Task Status

Check progress/results of async research tasks:

```
Use the task_status tool with task_id:
"<task_id_from_deep_research>"
```

Returns progress updates or final results when complete.

### Session Start

Access the research session prompt for usage instructions:

```
Use the research_session_start prompt
```

## Processor Tiers

Choose the appropriate processor based on your research needs:

| Tier    | Cost        | Latency    | Use Case                      |
| ------- | ----------- | ---------- | ----------------------------- |
| lite    | $5/1K       | 5-60s      | Basic fact retrieval          |
| base    | $10/1K      | 15-100s    | Standard research             |
| core    | $30/1K      | 1-5min     | When Pro is overkill          |
| core2x  | $60/1K      | 1-5min     | Enhanced core (2x multiplier) |
| **pro** | **$100/1K** | **3-9min** | **Deep research (default)**   |
| ultra   | $300/1K     | 5-25min    | Extensive research            |
| ultra2x | $600/1K     | 5-25min    | 2x ultra                      |
| ultra4x | $1,200/1K   | 8-30min    | 4x ultra                      |
| ultra8x | $2,400/1K   | 8-30min    | 8x ultra (SOTA)               |

## API Reference

### Tools

#### `deep_research`

Conduct comprehensive research with async execution. Returns immediately with task_id. Research runs in background.

**Parameters**:

- `query` (str): Research question (domain-agnostic)
- `processor` (str, optional): Processor tier (default: from DEFAULT_PROCESSOR env)

**Returns** (immediate):

```python
{
    "task_id": str,  # Use with task_status to check progress
    "processor": str,
    "estimated_duration": str
}
```

**Async behavior**: Submit multiple research tasks in parallel. Continue working while they run.

#### `task_status`

Check status and results of async research task.

**Parameters**:

- `task_id` (str): Task ID from deep_research

**Returns**:

```python
# If complete:
{
    "status": "complete",
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

# If running:
{
    "status": "running",
    "progress": float  # 0.0 to 1.0
}
```

#### `quick_research`

Quick research using Lite processor (5-60s, $5/1K queries). No approval required. Synchronous.

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

## Async/Parallel Execution

The server supports true async/parallel research execution:

**Workflow:**

1. Submit research task with `deep_research` → Returns task_id immediately
2. Continue working (coding, editing, etc.) while research runs in background
3. Check progress with `task_status(task_id)` when convenient
4. Retrieve full results when complete

**Parallel tasks:**

```
Submit Task A → task_id_A (research runs for 3-9 min)
Submit Task B → task_id_B (research runs for 3-9 min)
Submit Task C → task_id_C (research runs for 3-9 min)

All three run simultaneously in background.
Check status of any task at any time.
```
