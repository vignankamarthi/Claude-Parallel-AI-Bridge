# Quick Start Guide

Deploy Parallel AI research integration for Claude Desktop.

---

## Prerequisites

- Python 3.8+
- Claude Desktop
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

### 3. Claude Desktop Integration

Configure MCP server in Claude Desktop:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "parallel-research": {
      "command": "/FULL/PATH/TO/PROJECT/venv/bin/python",
      "args": ["/FULL/PATH/TO/PROJECT/server.py"],
      "env": {
        "PARALLEL_API_KEY": "your_actual_api_key_here"
      }
    }
  }
}
```

**Required substitutions**:
- `/FULL/PATH/TO/PROJECT/` → absolute path (e.g., `/Users/yourname/Claude-Parallel-AI-Integration/`)
- `your_actual_api_key_here` → Parallel AI API key

### 4. Restart

Fully quit and restart Claude Desktop.

### 5. Verification

Test integration:
```
Use quick_research to answer: "What is OAuth 2.1?"
```

Expected latency: 5-60 seconds.

---

## Available Tools

- `quick_research` - Fast queries (lite processor, auto-approved)
- `research_architecture_decision` - Deep research (pro processor, manual approval)

---

## Troubleshooting

**Tools not registered**:
- Verify full restart (not window close)
- Confirm absolute paths (no `~` or `$HOME`)
- Validate API key in `env` section

**Client configuration errors**:
- Verify API key in both `.env` and Claude config
- Confirm `env` object exists in config

**Debugging**:
- Server logs: `logs/` directory
- Full documentation: `README.md`
- Setup report: `SETUP_REPORT.md`

---

## Reference

- [Documentation](README.md)
- [Setup Report](SETUP_REPORT.md)
- [Parallel AI Platform](https://www.parallel.ai)