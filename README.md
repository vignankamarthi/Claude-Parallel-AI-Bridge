# Parallel AI MCP Server

A Model Context Protocol (MCP) server that integrates Parallel AI's deep research API with Claude's Tool Ecosystem for comprehensive technical research with structured citations.

**Author**: Vignan Kamarthi

## Overview

This MCP server provides Claude Desktop and Claude Code with access to Parallel AI's enterprise research API, enabling deep technical research with citation-backed answers across software engineering, ML/AI, data engineering, and research domains. The integration supports async/parallel task execution, multiple processor tiers (from quick fact retrieval to extensive SOTA research), intelligent chunking for large outputs, and user approval workflows for cost management.

## Features

- **Async/Parallel Execution**: Submit multiple research tasks simultaneously, continue working while research runs in background
- **Deep Research**: Comprehensive technical research with structured citations across all domains (Software, ML, Data, Research)
- **Structured Citations**: Field-level citations with URLs, excerpts, confidence scores, and reasoning
- **Multiple Processor Tiers**: 9 tiers from Lite ($5/1K) to Ultra8x ($2,400/1K)
- **Approval Workflow**: User consent required before expensive API calls with cost/time estimates
- **Task Status Tracking**: Real-time elapsed time vs expected duration
- **Smart Chunking**: Large research outputs (65-70k tokens) automatically split into ~15k token chunks
- **Quick Research**: Fast Lite processor mode for basic queries without approval (no blocking)
- **Comprehensive Logging**: Production-ready logging with timestamped console output
- **Rich Metadata**: Detailed task info optimized for agentic environments (Claude Code, Cursor, etc.)

## Installation

### Prerequisites

- Python 3.8+
- Claude Desktop or Claude Code
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

5. Configure MCP Client:

**For Claude Code (Recommended):**

Use the Claude Code CLI to add the MCP server:

```bash
# Add the server with environment variables
claude mcp add --transport stdio parallel-research \
  --env PARALLEL_API_KEY=your_actual_api_key_here \
  --env DEFAULT_PROCESSOR=pro \
  -- /ABSOLUTE/PATH/TO/PROJECT/venv/bin/python /ABSOLUTE/PATH/TO/PROJECT/server.py
```

Replace:

- `your_actual_api_key_here` with your Parallel AI API key
- `/ABSOLUTE/PATH/TO/PROJECT/` with the full path to this project directory

**Scope options:**

- Default (local): Private to current project
- `--scope project`: Shared via .mcp.json (commit to git)
- `--scope user`: Available across all projects

Verify installation:

```bash
claude mcp list
```

**For Claude Desktop:**

Edit your Claude Desktop config file:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

6. Activate:

**Claude Code**: Server activates automatically

**Claude Desktop**: Fully quit (Cmd+Q / File→Exit) and restart

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

For fast, low-cost queries (no approval required, completes in 5-60s):

```
Use the quick_research tool to answer:
"What is OAuth 2.1?"
```

Returns immediately with basic metadata and answer. Synchronous - blocks until complete (5-60s).

### Task Status

Check progress/results of async research tasks:

```
Use the task_status tool with task_id:
"<task_id_from_deep_research>"
```

Returns elapsed time vs expected duration for running tasks, or full results with metadata when complete.

**For large outputs (>15k tokens)**: First chunk returned automatically. Use `get_research_chunk` to retrieve remaining chunks.

### Retrieve Research Chunks

For large research outputs that exceed token limits:

```
Use the get_research_chunk tool:
task_id: "<task_id>"
chunk: 2
```

Retrieves specific chunk from multi-part research results. Ultra-tier processors can generate 65-70k tokens, automatically split into ~15k token chunks for safe retrieval.

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

```
# If running:
RESEARCH IN PROGRESS

Task ID: abc-123
Query: Your research question
Processor: ultra8x
Status: running
Expected Duration: 8-30min
Elapsed Time: 12.3 minutes
Created: 2025-11-04 14:23:15
Run ID: run_xyz

Still researching... Check back in 30s.

# If complete (small output):
RESEARCH COMPLETE

=== METADATA ===
Task ID: abc-123
Query: Your research question
Processor: ultra8x
Expected Duration: 8-30min
Actual Duration: 18.5 minutes
Created: 2025-11-04 14:23:15
Completed: 2025-11-04 14:41:45
Run ID: run_xyz
Content Length: 45,230 chars (~11,307 tokens)
Citation Groups: 8

=== RESEARCH FINDINGS ===
[Full content...]

=== CITATIONS ===
[Structured citations...]

# If complete (large output - chunked):
RESEARCH COMPLETE (CHUNKED OUTPUT)

=== METADATA ===
Task ID: abc-123
Query: Your research question
Processor: ultra8x
Expected Duration: 8-30min
Actual Duration: 25.2 minutes
Content Length: 280,000 chars (~70,000 tokens)
Total Chunks: 5
Citation Groups: 12

WARNING: This research output is LARGE (70,000 tokens).
It has been split into 5 chunks for safe retrieval.

=== RESEARCH FINDINGS (CHUNK 1/5) ===
[First chunk content...]

[... 4 more chunk(s) available ...]

To retrieve additional chunks, use the get_research_chunk tool.
Example: get_research_chunk(task_id="abc-123", chunk=2)

=== CITATIONS ===
[Structured citations...]
```

#### `get_research_chunk`

Retrieve specific chunk from large research output. Use when task_status indicates chunked output.

**Parameters**:

- `task_id` (str): Task ID from deep_research
- `chunk` (int): Chunk number to retrieve (1-indexed)

**Returns**:

```
RESEARCH CHUNK 2/5

Task ID: abc-123
Query: Your research question
Chunk: 2 of 5

=== CONTENT ===
[Chunk 2 content (~15k tokens)...]

[End of chunk 2/5]
```

**When to use**: Ultra-tier processors (especially ultra8x) can generate 65-70k tokens. These are automatically split into ~15k token chunks. The first chunk is returned with task_status, use this tool to retrieve chunks 2-N.

#### `quick_research`

Quick research using Lite processor (5-60s, $5/1K queries). No approval required. Synchronous (blocks until complete).

**Parameters**:

- `query` (str): Research question

**Returns**:

```
QUICK RESEARCH COMPLETE

=== METADATA ===
Query: What is OAuth 2.1?
Processor: lite
Duration: 12.3 seconds
Expected: 5-60s
Run ID: run_xyz
Content Length: 1,234 chars

=== ANSWER ===
[Research answer here...]
```

**Note**: Quick research completes synchronously (5-60s). For longer research (3-30min), use `deep_research` which runs async in background.

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

## Updating the MCP Server

After pulling updates from GitHub, follow these steps to get the latest version working:

### Quick Update (Code Changes Only)

If only Python code changed (server.py, utils/, etc.):

**For Claude Code:**

```bash
cd /path/to/Claude-Parallel-AI-Bridge
git pull
```

Then restart VS Code - changes apply automatically on startup.

**For Claude Desktop:**

```bash
cd /path/to/Claude-Parallel-AI-Bridge
git pull
```

Then restart Claude Desktop (Cmd+Q / File → Exit, then reopen) - changes apply automatically.

### Full Update (Dependencies Changed)

If requirements.txt was updated:

**For Claude Code:**

```bash
cd /path/to/Claude-Parallel-AI-Bridge
git pull
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

Then restart VS Code

**For Claude Desktop:**

```bash
cd /path/to/Claude-Parallel-AI-Bridge
git pull
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

Then fully quit and restart Claude Desktop

### Verifying the Update

Verify installation:

1. Try using `get_research_chunk` tool
2. Check that `task_status` shows elapsed time
3. Look for chunking warnings on large research outputs
4. Check the logs at `logs/parallel_mcp_*.log` for startup messages

### Common Issues

**"Tool not found: get_research_chunk"**

- **Claude Code**: Restart VS Code
- **Claude Desktop**: Restart Claude Desktop (Cmd+Q / File → Exit, then reopen)

**Dependencies missing**

- Rerun: `pip install -r requirements.txt`
- Check you're in the right venv: `which python`

**MCP not connecting (Claude Code)**

- Check server status: `claude mcp get parallel-research`
- View logs: `logs/parallel_mcp_*.log`
- Test manually: `python server.py`
- Remove and re-add if needed:
  ```bash
  claude mcp remove parallel-research
  claude mcp add --transport stdio parallel-research \
    --env PARALLEL_API_KEY=your_key \
    --env DEFAULT_PROCESSOR=pro \
    -- /path/to/venv/bin/python /path/to/server.py
  ```

**MCP not connecting (Claude Desktop)**

- Check logs: `logs/parallel_mcp_*.log` for errors
- Verify paths in config are absolute (no `~` or `$HOME`)
- Test server manually: `python server.py`
