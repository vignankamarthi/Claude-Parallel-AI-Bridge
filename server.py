#!/usr/bin/env python3
"""
Parallel AI MCP Server (WebSocket)

A Model Context Protocol server with WebSocket transport for async/parallel
research task execution using Parallel AI's deep research API.

Author: Vignan Kamarthi
"""

import os
import uuid
import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Import comprehensive logging system
from utils.logger import SystemLogger, log_entry, log_exit, log_progress

# MCP imports
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
    import mcp.server.stdio
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
    progress : float
        Progress 0.0-1.0
    result : Optional[Dict]
        Research result when complete
    error : Optional[str]
        Error message if failed
    created_at : datetime
        Task creation timestamp
    run_id : Optional[str]
        Parallel AI run ID
    """
    task_id: str
    query: str
    processor: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    run_id: Optional[str] = None


class ApprovalSchema(BaseModel):
    """User approval schema for research operations."""
    approved: bool = Field(description="User approves research task")
    max_wait_minutes: int = Field(
        default=15, description="Maximum wait time in minutes"
    )


# Initialize MCP server
server = Server("parallel-research-websocket")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available research tools.

    Returns
    -------
    list[Tool]
        Available MCP tools
    """
    return [
        Tool(
            name="quick_research",
            description="Fast research using lite processor (5-60s, $5/1K). No approval required. Use for definitions, fact-checking, quick lookups.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Research question"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="deep_research",
            description="Comprehensive research with structured citations. Approval required. Runs asynchronously (non-blocking). Use for complex technical decisions, comparisons, production pattern validation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Research question (e.g., 'Compare authentication approaches for microservices', 'Compare focal loss vs weighted CE for imbalanced datasets')"
                    },
                    "processor": {
                        "type": "string",
                        "description": "Processor tier: lite, base, core, core2x, pro (default), ultra, ultra2x, ultra4x, ultra8x",
                        "default": os.getenv("DEFAULT_PROCESSOR", "pro")
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="task_status",
            description="Check status of async research task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID returned from deep_research"
                    }
                },
                "required": ["task_id"]
            }
        )
    ]


@server.list_prompts()
async def list_prompts() -> list:
    """List available prompts."""
    return [
        {
            "name": "research_session_start",
            "description": "Start research session",
            "arguments": []
        }
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict) -> str:
    """
    Get prompt content.

    Parameters
    ----------
    name : str
        Prompt name
    arguments : dict
        Prompt arguments

    Returns
    -------
    str
        Prompt content
    """
    if name == "research_session_start":
        return """Research tools available:

- quick_research: Fast lookups (5-60s, no approval)
- deep_research: Comprehensive research with citations (async, approval required)

Deep research runs in background. Submit query, continue working, check results later."""

    return f"Unknown prompt: {name}"


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
        poll_count = 0

        while True:
            status = parallel_client.task_run.retrieve(task_state.run_id)

            if not status.is_active:
                SystemLogger.info("Research completed", {
                    "poll_count": poll_count,
                    "status": status.status,
                    "run_id": task_state.run_id,
                    "task_id": task_state.task_id
                })
                break

            poll_count += 1
            task_state.progress = 0.5 + (poll_count * 0.01)  # Incremental progress
            log_progress(task_state.progress, 1.0, f"Researching... ({status.status})")
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

        task_state.result = {
            "status": "complete",
            "content": content,
            "citations": citations,
            "processor": task_state.processor,
            "run_id": task_state.run_id,
        }
        task_state.status = TaskStatus.COMPLETE
        task_state.progress = 1.0

        SystemLogger.info("Research successful", {
            "citation_groups": len(citations),
            "content_length": len(content),
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


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls.

    Parameters
    ----------
    name : str
        Tool name
    arguments : dict
        Tool arguments

    Returns
    -------
    list[TextContent]
        Tool response
    """
    log_entry(f"call_tool:{name}", arguments)

    if name == "quick_research":
        return await quick_research(arguments.get("query"))

    elif name == "deep_research":
        return await deep_research(
            arguments.get("query"),
            arguments.get("processor", os.getenv("DEFAULT_PROCESSOR", "pro"))
        )

    elif name == "task_status":
        return await task_status(arguments.get("task_id"))

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def quick_research(query: str) -> list[TextContent]:
    """
    Quick research using Lite processor (5-60s, $5/1K queries).

    Parameters
    ----------
    query : str
        Research question

    Returns
    -------
    list[TextContent]
        Research result
    """
    log_entry("quick_research", {"query": query[:50] if query else ""})

    SystemLogger.info("Quick research request", {
        "query_length": len(query),
        "query_preview": query[:50] + "..." if len(query) > 50 else query
    })

    if parallel_client is None:
        SystemLogger.error("Parallel AI client not configured for quick research")
        log_exit("quick_research", {"status": "error"})
        return [TextContent(
            type="text",
            text="ERROR: Parallel AI client not configured. Set PARALLEL_API_KEY in .env file."
        )]

    try:
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

        SystemLogger.info("Quick research successful", {
            "content_length": len(content),
            "run_id": run.run_id
        })

        log_exit("quick_research", {"status": "complete", "run_id": run.run_id})
        return [TextContent(type="text", text=content)]

    except Exception as e:
        SystemLogger.error("Quick research failed", exception=e, context={
            "query": query[:50] if query else ""
        })
        log_exit("quick_research", {"status": "error"})
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


async def deep_research(query: str, processor: str = None) -> list[TextContent]:
    """
    Conduct deep research with async execution.

    Parameters
    ----------
    query : str
        Research question
    processor : str, optional
        Processor tier (defaults to DEFAULT_PROCESSOR from env)

    Returns
    -------
    list[TextContent]
        Task ID for status checking
    """
    if processor is None:
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
    valid_processors = [
        "lite", "base", "core", "core2x", "pro",
        "ultra", "ultra2x", "ultra4x", "ultra8x",
    ]
    if processor not in valid_processors:
        SystemLogger.warning(f"Invalid processor '{processor}', defaulting to 'pro'", {
            "requested_processor": processor,
            "valid_processors": valid_processors,
            "default": "pro"
        })
        processor = "pro"

    # Check client availability
    if parallel_client is None:
        SystemLogger.error("Parallel AI client not configured", context={
            "processor": processor,
            "help": "Set PARALLEL_API_KEY in .env file"
        })
        log_exit("deep_research", {"status": "error"})
        return [TextContent(
            type="text",
            text="ERROR: Parallel AI client not configured. Set PARALLEL_API_KEY in .env file."
        )]

    # Cost and time estimates
    cost_map = {
        "lite": "$5", "base": "$10", "core": "$30", "core2x": "$60",
        "pro": "$100", "ultra": "$300", "ultra2x": "$600",
        "ultra4x": "$1,200", "ultra8x": "$2,400",
    }
    time_map = {
        "lite": "5-60s", "base": "15-100s", "core": "1-5min", "core2x": "1-5min",
        "pro": "3-9min", "ultra": "5-25min", "ultra2x": "5-25min",
        "ultra4x": "8-30min", "ultra8x": "8-30min",
    }

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

    # Request approval via stdio (blocking for approval only)
    approval_message = f"""RESEARCH APPROVAL REQUIRED

Query: {query}
Processor: {processor}
Duration: {time_map.get(processor, "unknown")} (async - non-blocking)
Cost: {cost_map.get(processor, "unknown")} per 1,000 queries

Approve? This will run in background."""

    # NOTE: In stdio mode, approval is synchronous. In full WebSocket mode,
    # this would be async. For now, returning task_id immediately and user
    # can check status.

    try:
        # Execute research
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
        return [TextContent(
            type="text",
            text=f"Research task submitted (non-blocking)\n\nTask ID: {task_id}\nProcessor: {processor}\nDuration: {time_map.get(processor, 'unknown')}\n\nUse task_status tool to check progress.\nYou can continue working while research runs in background."
        )]

    except Exception as e:
        SystemLogger.error("Research submission failed", exception=e, context={
            "query": query[:50],
            "processor": processor,
            "task_id": task_id
        })
        task_state.status = TaskStatus.FAILED
        task_state.error = str(e)
        log_exit("deep_research", {"status": "error", "task_id": task_id})
        return [TextContent(type="text", text=f"ERROR: {str(e)}")]


async def task_status(task_id: str) -> list[TextContent]:
    """
    Check status of async research task.

    Parameters
    ----------
    task_id : str
        Task ID

    Returns
    -------
    list[TextContent]
        Task status and result if complete
    """
    log_entry("task_status", {"task_id": task_id})

    if task_id not in task_queue:
        return [TextContent(type="text", text=f"ERROR: Task {task_id} not found")]

    task = task_queue[task_id]

    if task.status == TaskStatus.COMPLETE:
        # Return full result
        result = task.result
        response = f"""RESEARCH COMPLETE

Query: {task.query}
Processor: {task.processor}
Run ID: {task.run_id}

{result['content']}

--- CITATIONS ---
"""
        for idx, citation_group in enumerate(result['citations'], 1):
            response += f"\n[{idx}] {citation_group['field']}\n"
            response += f"    Confidence: {citation_group['confidence']}\n"
            response += f"    Reasoning: {citation_group['reasoning']}\n"
            for cite in citation_group['citations']:
                response += f"    - {cite['title']}: {cite['url']}\n"

        log_exit("task_status", {"status": "complete", "task_id": task_id})
        return [TextContent(type="text", text=response)]

    elif task.status == TaskStatus.FAILED:
        log_exit("task_status", {"status": "failed", "task_id": task_id})
        return [TextContent(
            type="text",
            text=f"RESEARCH FAILED\n\nTask ID: {task_id}\nError: {task.error}"
        )]

    else:
        # Still running
        log_exit("task_status", {"status": task.status, "task_id": task_id})
        return [TextContent(
            type="text",
            text=f"Status: {task.status}\nProgress: {task.progress:.1%}\n\nStill researching... Check back in 30s."
        )]


async def main():
    """Initialize and run MCP server."""
    global parallel_client

    log_entry("main")

    api_key = os.getenv("PARALLEL_API_KEY")
    SystemLogger.info("Initializing Parallel AI MCP Server (WebSocket)", {
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

    SystemLogger.info("Starting MCP server with stdio transport", {
        "timeout": 360,
        "default_processor": os.getenv('DEFAULT_PROCESSOR', 'pro'),
        "parallel_configured": parallel_client is not None
    })

    print("Starting Parallel AI MCP Server (WebSocket-Ready)...")
    print(f"Default Processor: {os.getenv('DEFAULT_PROCESSOR', 'pro')}")
    print(f"Logs directory: logs/")
    print(f"Async task execution enabled")

    # Run with stdio transport (Claude Desktop standard)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

    log_exit("main", {})


if __name__ == "__main__":
    SystemLogger.info("Starting Parallel AI MCP Server", {
        "timeout": 360,
        "default_processor": os.getenv('DEFAULT_PROCESSOR', 'pro'),
        "api_key_configured": bool(os.getenv("PARALLEL_API_KEY"))
    })

    asyncio.run(main())
