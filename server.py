#!/usr/bin/env python3
"""
Parallel AI MCP Server

A Model Context Protocol server with stdio transport for async/parallel
research task execution using Parallel AI's deep research API.

Author: Vignan Kamarthi

Migrated to MCPServer API (mcp SDK v1.25+) on 2026-04-06.
"""

import os
import uuid
import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import comprehensive logging system
from utils.logger import SystemLogger, log_entry, log_exit, log_progress

# MCP imports
try:
    from mcp.server.mcpserver.server import MCPServer
    from mcp.types import TextContent
except ImportError:
    SystemLogger.error("MCP not installed", context={"module": "mcp.server"})
    print("ERROR: MCP not installed. Run: pip install mcp")
    exit(1)

# Global client and task queue
parallel_client = None
task_queue: Dict[str, 'TaskState'] = {}


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskState:
    """
    State container for async research tasks.

    Attributes
    ----------
    task_id : str
        Unique task identifier
    query : str
        Research query
    processor : str
        Processor tier (lite/base/core/pro/ultra/etc)
    status : TaskStatus
        Current task status
    result : Optional[Dict]
        Research result when complete
    error : Optional[str]
        Error message if failed
    created_at : datetime
        Task creation timestamp
    started_at : Optional[datetime]
        Timestamp when task execution started
    run_id : Optional[str]
        Parallel AI run ID
    """
    task_id: str
    query: str
    processor: str
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    run_id: Optional[str] = None


# Cost and time estimate maps (shared across tools)
COST_MAP = {
    "lite": "$5", "base": "$10", "core": "$30", "core2x": "$60",
    "pro": "$100", "ultra": "$300", "ultra2x": "$600",
    "ultra4x": "$1,200", "ultra8x": "$2,400",
}
TIME_MAP = {
    "lite": "5-60s", "base": "15-100s", "core": "1-5min", "core2x": "1-5min",
    "pro": "3-9min", "ultra": "5-25min", "ultra2x": "5-25min",
    "ultra4x": "8-30min", "ultra8x": "8-30min",
}
VALID_PROCESSORS = list(COST_MAP.keys())


# Initialize MCP server
server = MCPServer("parallel-research")


async def poll_parallel_task(task_state: TaskState) -> None:
    """
    Background worker to poll Parallel API for task completion.

    Parameters
    ----------
    task_state : TaskState
        Task state to update
    """
    log_entry("poll_parallel_task", {"task_id": task_state.task_id, "run_id": task_state.run_id})

    try:
        task_state.status = TaskStatus.RUNNING
        task_state.started_at = datetime.now()
        start_time = task_state.started_at
        poll_count = 0

        while True:
            status = parallel_client.task_run.retrieve(task_state.run_id)

            if not status.is_active:
                elapsed = (datetime.now() - start_time).total_seconds()
                SystemLogger.info("Research completed", {
                    "poll_count": poll_count,
                    "elapsed_seconds": elapsed,
                    "status": status.status,
                    "run_id": task_state.run_id,
                    "task_id": task_state.task_id
                })
                break

            poll_count += 1
            elapsed = (datetime.now() - start_time).total_seconds()
            elapsed_mins = elapsed / 60
            SystemLogger.info(f"Research polling - {elapsed_mins:.1f}min elapsed", {
                "poll_count": poll_count,
                "api_status": status.status if hasattr(status, 'status') else 'unknown'
            })
            await asyncio.sleep(10)

        # Retrieve results
        result = parallel_client.task_run.result(task_state.run_id)

        # Parse citations
        citations = []
        if hasattr(result, "output") and hasattr(result.output, "basis"):
            for basis_item in result.output.basis:
                citation_data = {
                    "field": basis_item.field if hasattr(basis_item, "field") else None,
                    "citations": [],
                    "confidence": (
                        basis_item.confidence
                        if hasattr(basis_item, "confidence")
                        else None
                    ),
                    "reasoning": (
                        basis_item.reasoning
                        if hasattr(basis_item, "reasoning")
                        else None
                    ),
                }

                if hasattr(basis_item, "citations"):
                    for cite in basis_item.citations:
                        citation_data["citations"].append(
                            {
                                "url": cite.url if hasattr(cite, "url") else None,
                                "excerpts": (
                                    cite.excerpts if hasattr(cite, "excerpts") else []
                                ),
                                "title": cite.title if hasattr(cite, "title") else None,
                            }
                        )

                citations.append(citation_data)

        # Extract content
        content = ""
        if hasattr(result, "output") and hasattr(result.output, "content"):
            output_content = result.output.content
            if isinstance(output_content, dict):
                content = output_content.get("output", str(output_content))
            else:
                content = str(output_content)

        # Estimate token count (rough: chars / 4)
        estimated_tokens = len(content) / 4

        # Split into chunks if too large (>15k tokens per chunk for safety)
        chunk_size = 15000 * 4  # ~60k chars per chunk
        chunks = []
        if estimated_tokens > 15000:
            for i in range(0, len(content), chunk_size):
                chunks.append(content[i:i+chunk_size])
            SystemLogger.info("Large result chunked", {
                "total_tokens": int(estimated_tokens),
                "num_chunks": len(chunks),
                "task_id": task_state.task_id
            })
        else:
            chunks = [content]

        task_state.result = {
            "status": "complete",
            "content": content,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "estimated_tokens": int(estimated_tokens),
            "citations": citations,
            "processor": task_state.processor,
            "run_id": task_state.run_id,
        }
        task_state.status = TaskStatus.COMPLETE

        SystemLogger.info("Research successful", {
            "citation_groups": len(citations),
            "content_length": len(content),
            "estimated_tokens": int(estimated_tokens),
            "total_chunks": len(chunks),
            "run_id": task_state.run_id,
            "task_id": task_state.task_id
        })

    except Exception as e:
        SystemLogger.error("Research failed", exception=e, context={
            "task_id": task_state.task_id,
            "run_id": task_state.run_id
        })
        task_state.status = TaskStatus.FAILED
        task_state.error = str(e)

    log_exit("poll_parallel_task", {"status": task_state.status, "task_id": task_state.task_id})


# ---------------------------------------------------------------------------
# Tool definitions (MCPServer auto-generates input schemas from type hints)
# ---------------------------------------------------------------------------

@server.tool(
    name="quick_research",
    description="Fast research using lite processor (5-60s, $5/1K). No approval required. Use for definitions, fact-checking, quick lookups.",
)
async def quick_research(query: str) -> str:
    """Quick research using Lite processor."""
    log_entry("quick_research", {"query": query[:50] if query else ""})

    SystemLogger.info("Quick research request", {
        "query_length": len(query),
        "query_preview": query[:50] + "..." if len(query) > 50 else query
    })

    if parallel_client is None:
        SystemLogger.error("Parallel AI client not configured for quick research")
        log_exit("quick_research", {"status": "error"})
        return "ERROR: Parallel AI client not configured. Set PARALLEL_API_KEY in .env file."

    try:
        start_time = datetime.now()
        run = parallel_client.task_run.create(input=query, processor="lite")
        SystemLogger.debug("Quick research run created", {
            "run_id": run.run_id,
            "processor": "lite"
        })

        # Poll for completion
        while True:
            status = parallel_client.task_run.retrieve(run.run_id)
            if not status.is_active:
                break
            await asyncio.sleep(5)

        result = parallel_client.task_run.result(run.run_id)

        # Extract content
        content = ""
        if hasattr(result, "output") and hasattr(result.output, "content"):
            output_content = result.output.content
            if isinstance(output_content, dict):
                content = output_content.get("output", str(output_content))
            else:
                content = str(output_content)

        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        elapsed_str = f"{elapsed_seconds:.1f} seconds"

        SystemLogger.info("Quick research successful", {
            "content_length": len(content),
            "elapsed_seconds": elapsed_seconds,
            "run_id": run.run_id
        })

        response = f"""QUICK RESEARCH COMPLETE

=== METADATA ===
Query: {query}
Processor: lite
Duration: {elapsed_str}
Expected: 5-60s
Run ID: {run.run_id}
Content Length: {len(content)} chars

=== ANSWER ===
{content}
"""

        log_exit("quick_research", {"status": "complete", "run_id": run.run_id})
        return response

    except Exception as e:
        SystemLogger.error("Quick research failed", exception=e, context={
            "query": query[:50] if query else ""
        })
        log_exit("quick_research", {"status": "error"})
        return f"ERROR: {str(e)}"


@server.tool(
    name="deep_research",
    description="Comprehensive research with structured citations. Runs asynchronously (non-blocking). Use for complex technical decisions, comparisons, production pattern validation.",
)
async def deep_research(query: str, processor: str = "pro") -> str:
    """Deep research with async execution and background polling."""
    if not processor:
        processor = os.getenv("DEFAULT_PROCESSOR", "pro")

    log_entry("deep_research", {
        "query": query[:100] if query else "",
        "processor": processor
    })

    SystemLogger.info("Deep research request received", {
        "query_length": len(query),
        "processor": processor,
        "query_preview": query[:50] + "..." if len(query) > 50 else query
    })

    # Validate processor
    if processor not in VALID_PROCESSORS:
        SystemLogger.warning(f"Invalid processor '{processor}', defaulting to 'pro'", {
            "requested_processor": processor,
            "valid_processors": VALID_PROCESSORS,
            "default": "pro"
        })
        processor = "pro"

    if parallel_client is None:
        SystemLogger.error("Parallel AI client not configured", context={
            "processor": processor,
            "help": "Set PARALLEL_API_KEY in .env file"
        })
        log_exit("deep_research", {"status": "error"})
        return "ERROR: Parallel AI client not configured. Set PARALLEL_API_KEY in .env file."

    # Create task
    task_id = str(uuid.uuid4())
    task_state = TaskState(
        task_id=task_id,
        query=query,
        processor=processor
    )
    task_queue[task_id] = task_state

    SystemLogger.info("Task created", {
        "task_id": task_id,
        "processor": processor,
        "query_preview": query[:30]
    })

    try:
        SystemLogger.info(f"Creating research run with processor '{processor}'", {
            "query_length": len(query),
            "processor": processor,
            "task_id": task_id
        })

        run = parallel_client.task_run.create(input=query, processor=processor)
        task_state.run_id = run.run_id
        task_state.status = TaskStatus.APPROVED

        SystemLogger.info("Research run created", {
            "run_id": run.run_id,
            "task_id": task_id,
            "processor": processor,
            "query_preview": query[:30]
        })

        # Start background polling
        asyncio.create_task(poll_parallel_task(task_state))

        log_exit("deep_research", {"status": "submitted", "task_id": task_id})
        return (
            f"Research task submitted (non-blocking)\n\n"
            f"Task ID: {task_id}\n"
            f"Processor: {processor}\n"
            f"Duration: {TIME_MAP.get(processor, 'unknown')}\n"
            f"Cost: {COST_MAP.get(processor, 'unknown')} per 1,000 queries\n\n"
            f"Use task_status tool to check progress.\n"
            f"You can continue working while research runs in background."
        )

    except Exception as e:
        SystemLogger.error("Research submission failed", exception=e, context={
            "query": query[:50],
            "processor": processor,
            "task_id": task_id
        })
        task_state.status = TaskStatus.FAILED
        task_state.error = str(e)
        log_exit("deep_research", {"status": "error", "task_id": task_id})
        return f"ERROR: {str(e)}"


@server.tool(
    name="task_status",
    description="Check status of async research task",
)
async def check_task_status(task_id: str) -> str:
    """Check status of an async research task and return results if complete."""
    log_entry("task_status", {"task_id": task_id})

    if task_id not in task_queue:
        return f"ERROR: Task {task_id} not found"

    task = task_queue[task_id]

    if task.status == TaskStatus.COMPLETE:
        elapsed_seconds = (datetime.now() - task.created_at).total_seconds()
        elapsed_str = f"{elapsed_seconds/60:.1f} minutes" if elapsed_seconds >= 60 else f"{elapsed_seconds:.0f} seconds"

        result = task.result
        total_chunks = result.get('total_chunks', 1)
        estimated_tokens = result.get('estimated_tokens', 0)

        # Build citations section
        citations_text = "\n=== CITATIONS ===\n"
        for idx, citation_group in enumerate(result['citations'], 1):
            citations_text += f"\n[{idx}] {citation_group['field']}\n"
            citations_text += f"    Confidence: {citation_group['confidence']}\n"
            citations_text += f"    Reasoning: {citation_group['reasoning']}\n"
            for cite in citation_group['citations']:
                citations_text += f"    - {cite['title']}: {cite['url']}\n"

        if total_chunks > 1:
            response = f"""RESEARCH COMPLETE (CHUNKED OUTPUT)

=== METADATA ===
Task ID: {task_id}
Query: {task.query}
Processor: {task.processor}
Expected Duration: {TIME_MAP.get(task.processor, 'unknown')}
Actual Duration: {elapsed_str}
Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Run ID: {task.run_id}
Content Length: {len(result['content'])} chars (~{estimated_tokens:,} tokens)
Total Chunks: {total_chunks}
Citation Groups: {len(result['citations'])}

WARNING: This research output is LARGE ({estimated_tokens:,} tokens).
It has been split into {total_chunks} chunks for safe retrieval.

=== RESEARCH FINDINGS (CHUNK 1/{total_chunks}) ===
{result['chunks'][0]}

[... {total_chunks - 1} more chunk(s) available ...]

To retrieve additional chunks, use the get_research_chunk tool.
Example: get_research_chunk(task_id="{task_id}", chunk=2)

{citations_text}
"""
        else:
            response = f"""RESEARCH COMPLETE

=== METADATA ===
Task ID: {task_id}
Query: {task.query}
Processor: {task.processor}
Expected Duration: {TIME_MAP.get(task.processor, 'unknown')}
Actual Duration: {elapsed_str}
Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Run ID: {task.run_id}
Content Length: {len(result['content'])} chars (~{estimated_tokens:,} tokens)
Citation Groups: {len(result['citations'])}

=== RESEARCH FINDINGS ===
{result['content']}

{citations_text}
"""
        log_exit("task_status", {"status": "complete", "task_id": task_id, "chunked": total_chunks > 1})
        return response

    elif task.status == TaskStatus.FAILED:
        elapsed_seconds = (datetime.now() - task.created_at).total_seconds()
        elapsed_str = f"{elapsed_seconds/60:.1f} minutes" if elapsed_seconds >= 60 else f"{elapsed_seconds:.0f} seconds"

        log_exit("task_status", {"status": "failed", "task_id": task_id})
        return (
            f"RESEARCH FAILED\n\n"
            f"Task ID: {task_id}\n"
            f"Query: {task.query}\n"
            f"Processor: {task.processor}\n"
            f"Expected Duration: {TIME_MAP.get(task.processor, 'unknown')}\n"
            f"Failed After: {elapsed_str}\n"
            f"Error: {task.error}"
        )

    else:
        if task.started_at:
            elapsed_seconds = (datetime.now() - task.started_at).total_seconds()
            elapsed_str = f"{elapsed_seconds/60:.1f} minutes" if elapsed_seconds >= 60 else f"{elapsed_seconds:.0f} seconds"
        else:
            elapsed_str = "Not started yet"

        log_exit("task_status", {"status": task.status, "task_id": task_id})
        return (
            f"RESEARCH IN PROGRESS\n\n"
            f"Task ID: {task_id}\n"
            f"Query: {task.query}\n"
            f"Processor: {task.processor}\n"
            f"Status: {task.status}\n"
            f"Expected Duration: {TIME_MAP.get(task.processor, 'unknown')}\n"
            f"Elapsed Time: {elapsed_str}\n"
            f"Created: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Run ID: {task.run_id}\n\n"
            f"Still researching... Check back in 30s."
        )


@server.tool(
    name="get_research_chunk",
    description="Retrieve specific chunk from large research output. Use when research result was split into multiple chunks.",
)
async def get_research_chunk(task_id: str, chunk: int) -> str:
    """Retrieve a specific chunk from a large research result."""
    log_entry("get_research_chunk", {"task_id": task_id, "chunk": chunk})

    if task_id not in task_queue:
        return f"ERROR: Task {task_id} not found"

    task = task_queue[task_id]

    if task.status != TaskStatus.COMPLETE:
        return f"ERROR: Task {task_id} is not complete yet (status: {task.status})"

    result = task.result
    total_chunks = result.get('total_chunks', 1)
    chunks = result.get('chunks', [])

    if chunk < 1 or chunk > total_chunks:
        return f"ERROR: Invalid chunk number {chunk}. Valid range: 1-{total_chunks}"

    chunk_index = chunk - 1
    response = f"""RESEARCH CHUNK {chunk}/{total_chunks}

Task ID: {task_id}
Query: {task.query}
Chunk: {chunk} of {total_chunks}

=== CONTENT ===
{chunks[chunk_index]}

[End of chunk {chunk}/{total_chunks}]
"""
    log_exit("get_research_chunk", {"task_id": task_id, "chunk": chunk})
    return response


# ---------------------------------------------------------------------------
# Prompt definitions
# ---------------------------------------------------------------------------

@server.prompt(
    name="research_session_start",
    description="Start research session",
)
async def research_session_start() -> str:
    """Provide an overview of available research tools."""
    return """Research tools available:

- quick_research: Fast lookups (5-60s, no approval)
- deep_research: Comprehensive research with citations (async, approval required)

Deep research runs in background. Submit query, continue working, check results later."""


# ---------------------------------------------------------------------------
# Initialization and entry point
# ---------------------------------------------------------------------------

def init_parallel_client():
    """Initialize the Parallel AI client from environment."""
    global parallel_client

    api_key = os.getenv("PARALLEL_API_KEY")
    SystemLogger.info("Initializing Parallel AI MCP Server", {
        "api_key_configured": bool(api_key and api_key != "your_parallel_api_key_here"),
        "default_processor": os.getenv("DEFAULT_PROCESSOR", "pro")
    })

    if not api_key or api_key == "your_parallel_api_key_here":
        SystemLogger.warning("PARALLEL_API_KEY not configured - running in mock mode", {
            "api_key_present": bool(api_key),
            "is_placeholder": api_key == "your_parallel_api_key_here" if api_key else False
        })
        parallel_client = None
    else:
        try:
            import parallel

            parallel_client = parallel.Parallel(api_key=api_key)
            SystemLogger.info("Parallel AI client initialized successfully", {
                "client_type": type(parallel_client).__name__,
                "api_key_length": len(api_key)
            })
        except ImportError as e:
            SystemLogger.error(
                "parallel-web package not installed",
                exception=e,
                context={"package": "parallel-web", "install_command": "pip install parallel-web"}
            )
            parallel_client = None
        except Exception as e:
            SystemLogger.error(
                "Failed to initialize Parallel client",
                exception=e,
                context={"api_key_length": len(api_key) if api_key else 0}
            )
            parallel_client = None


async def main():
    """Initialize and run MCP server."""
    log_entry("main")

    init_parallel_client()

    SystemLogger.info("Starting MCP server with stdio transport", {
        "default_processor": os.getenv('DEFAULT_PROCESSOR', 'pro'),
        "parallel_configured": parallel_client is not None
    })

    await server.run_stdio_async()

    log_exit("main", {})


if __name__ == "__main__":
    SystemLogger.info("Starting Parallel AI MCP Server", {
        "default_processor": os.getenv('DEFAULT_PROCESSOR', 'pro'),
        "api_key_configured": bool(os.getenv("PARALLEL_API_KEY"))
    })

    asyncio.run(main())
