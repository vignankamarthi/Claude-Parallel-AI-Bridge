# Quick Start Guide

Deploy Parallel AI research integration for Claude Desktop or Claude Code.

---

## Prerequisites

- Python 3.8+
- **Claude Desktop** or **Claude Code**
- Parallel AI API key ([obtain here](https://www.parallel.ai))

---

## Installation

### 1. Environment Setup

```bash
git clone <repository-url>
cd Claude-Parallel-AI-Integration
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
```

Edit `.env`:
```
PARALLEL_API_KEY=your_actual_api_key_here
DEFAULT_PROCESSOR=pro
```

### 3. MCP Client Integration

**For Claude Code (Recommended):**

Use the Claude Code CLI to add the server:

```bash
# Replace paths and API key with your actual values
claude mcp add --transport stdio parallel-research \
  --env PARALLEL_API_KEY=your_actual_api_key_here \
  --env DEFAULT_PROCESSOR=pro \
  -- /FULL/PATH/TO/PROJECT/venv/bin/python /FULL/PATH/TO/PROJECT/server.py
```

Verify installation:
```bash
claude mcp list
```

**For Claude Desktop:**

Edit config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "parallel-research": {
      "command": "/FULL/PATH/TO/PROJECT/venv/bin/python",
      "args": ["/FULL/PATH/TO/PROJECT/server.py"],
      "env": {
        "PARALLEL_API_KEY": "your_actual_api_key_here",
        "DEFAULT_PROCESSOR": "pro"
      }
    }
  }
}
```

**Required substitutions:**
- `/FULL/PATH/TO/PROJECT/` → absolute path (e.g., `/Users/yourname/Claude-Parallel-AI-Integration/`)
- `your_actual_api_key_here` → Parallel AI API key

### 4. Activate

**Claude Code**: Server activates automatically (check with `/mcp`)

**Claude Desktop**: Fully quit (Cmd+Q / File→Exit) and restart

### 5. Verification

Test integration with quick research:
```
Use quick_research to answer: "What is OAuth 2.1?"
```

Expected: Complete in 5-60 seconds with metadata and answer.

---

## Available Tools

### Core Tools

1. **`quick_research`** - Fast research (lite processor, 5-60s, no approval)
   - Synchronous, returns immediately with answer
   - Example: "What is OAuth 2.1?"

2. **`deep_research`** - Comprehensive research (async, 3-30min, requires approval)
   - Returns task_id immediately, runs in background
   - Multiple processor tiers: lite, base, core, core2x, pro, ultra, ultra2x, ultra4x, ultra8x
   - Example: "Compare authentication approaches for microservices"

3. **`task_status`** - Check async research progress/results
   - Shows elapsed time vs expected duration
   - Returns full results with rich metadata when complete
   - Automatically returns first chunk for large outputs

4. **`get_research_chunk`** - Retrieve chunks from large research outputs
   - Use when task_status indicates chunked output (>15k tokens)
   - Ultra-tier processors can generate 65-70k tokens split into ~15k token chunks

### Features

- **Async/Parallel Execution** - Submit multiple research tasks simultaneously
- **Smart Chunking** - Large outputs (65-70k tokens) automatically split for safe retrieval
- **Real-time Tracking** - Elapsed time vs expected duration
- **Rich Metadata** - Optimized for agentic environments (Claude Code, Cursor, etc.)
- **Structured Citations** - Field-level citations with confidence scores

---

## Troubleshooting

### Tools Not Available

**Claude Code:**
```bash
# Check if server is loaded
claude mcp list
```

Then restart VS Code

**Claude Desktop:**
- Fully quit (Cmd+Q / File→Exit, NOT just close window)
- Restart Claude Desktop
- Check logs: `logs/parallel_mcp_*.log`

### Common Issues

**"Tool not found: get_research_chunk"**

**Claude Code:** Restart VS Code

**Claude Desktop:** Fully quit and restart

**Configuration Errors (Claude Code)**
```bash
# Check current config
claude mcp get parallel-research

# Remove and re-add if needed
claude mcp remove parallel-research
claude mcp add --transport stdio parallel-research \
  --env PARALLEL_API_KEY=your_key \
  --env DEFAULT_PROCESSOR=pro \
  -- /path/to/venv/bin/python /path/to/server.py
```

**Configuration Errors (Claude Desktop)**
- Verify API key in `env` section of config
- Confirm absolute paths (no `~` or `$HOME`)
- Check JSON syntax is valid

**Connection Issues**
- Test server manually: `python server.py` (should show logs)
- Check logs: `logs/parallel_mcp_*.log` for errors
- **Claude Code**: Use `claude mcp get parallel-research` for diagnostics

### Updating After Code Changes

**Claude Code:**
```bash
git pull
```

Then restart VS Code

**Claude Desktop:**
```bash
git pull
# Then fully quit and restart Claude Desktop
```

Verify: Try using `get_research_chunk` or check that `task_status` shows elapsed time

---

## Quick Examples

### Example 1: Quick Research
```
Use quick_research: "What is OAuth 2.1?"
```
Returns in 5-60s with metadata.

### Example 2: Deep Research (Async)
```
Use deep_research: "Compare authentication approaches for microservices"
Processor: pro
```
Returns task_id immediately. Check with task_status.

### Example 3: Large Output (Chunked)
```
Use deep_research: "Comprehensive analysis of distributed systems patterns"
Processor: ultra8x
```
If result is large, task_status shows first chunk. Use get_research_chunk for remaining chunks.

---

## Reference

- [Full Documentation](README.md) - Complete API reference and examples
- [Parallel AI Platform](https://www.parallel.ai) - Get API key and pricing