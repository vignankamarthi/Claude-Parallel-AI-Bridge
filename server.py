#!/usr/bin/env python3
"""
Parallel AI MCP Server

A Model Context Protocol server that integrates Parallel AI's deep research API
for architecture research with structured citations.

Author: Vignan Kamarthi
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ParallelMCP")

# MCP imports
try:
    from mcp.server.fastmcp import FastMCP, Context
except ImportError:
    logger.error("FastMCP not installed")
    print("ERROR: FastMCP not installed. Run: pip install mcp fastmcp")
    exit(1)

# Global client (mutable despite uppercase naming convention)
parallel_client = None


class ApprovalSchema(BaseModel):
    """
    User approval schema for expensive research operations.

    Attributes
    ----------
    approved : bool
        Whether the user approves the research task
    max_wait_minutes : int
        Maximum time to wait for results (default: 15)
    """

    approved: bool = Field(description="User approves research task")
    max_wait_minutes: int = Field(
        default=15, description="Maximum wait time in minutes"
    )


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """
    Initialize Parallel AI client on server startup.

    Parameters
    ----------
    server : FastMCP
        The MCP server instance

    Yields
    ------
    dict
        Context dictionary with parallel client
    """
    global parallel_client

    api_key = os.getenv("PARALLEL_API_KEY")
    logger.info("Initializing Parallel AI MCP Server")

    if not api_key or api_key == "your_parallel_api_key_here":
        logger.warning("PARALLEL_API_KEY not configured - running in mock mode")
        parallel_client = None
    else:
        try:
            import parallel

            parallel_client = parallel.Parallel(api_key=api_key)
            logger.info("Parallel AI client initialized successfully")
        except ImportError:
            logger.error("parallel-web package not installed")
            parallel_client = None
        except Exception as e:
            logger.error(f"Failed to initialize Parallel client: {e}")
            parallel_client = None

    try:
        yield {"parallel": parallel_client}
    finally:
        logger.info("Shutting down Parallel AI MCP Server")


# Initialize MCP server
mcp = FastMCP(
    "Parallel Architecture Research", lifespan=app_lifespan, request_timeout=360
)


@mcp.prompt(title="Start Parallel Research Session")
def research_session_start() -> str:
    """
    Generate session start prompt.

    Returns
    -------
    str
        Welcome message with usage instructions
    """
    return """You are about to use Parallel's deep research API for architecture decisions.

IMPORTANT NOTICES:
- Research tasks take 1-5 minutes (Core) or 3-9 minutes (Pro) to complete
- Each query incurs API costs ($30-$100 per 1000 queries)
- Always request user permission before initiating research
- Citations are provided for verification

What would you like me to research? (I'll ask for approval before starting)
"""


@mcp.tool()
async def research_architecture_decision(
    query: str, ctx: Context, processor: str = "pro"
) -> Dict[str, Any]:
    """
    Conduct deep research for architecture decisions with structured citations.

    Parameters
    ----------
    query : str
        Research question (e.g., "Compare authentication approaches for microservices")
    ctx : Context
        MCP context for progress reporting and approval
    processor : str, optional
        Processor tier: lite, base, core, core2x, pro, ultra, ultra2x, ultra4x, ultra8x
        Default is "pro"

    Returns
    -------
    dict
        Research results containing:
        - status : str - "complete", "cancelled", or "error"
        - content : str - Synthesized research answer
        - citations : list - Structured citations with URLs, excerpts, confidence scores
        - processor : str - Processor tier used
        - run_id : str - Parallel AI run ID for reference

    Examples
    --------
    >>> result = await research_architecture_decision(
    ...     "Compare OAuth 2.1 vs JWT authentication",
    ...     ctx,
    ...     processor="pro"
    ... )
    """
    logger.info(f"Research request: query='{query}', processor='{processor}'")

    # Validate processor
    valid_processors = [
        "lite",
        "base",
        "core",
        "core2x",
        "pro",
        "ultra",
        "ultra2x",
        "ultra4x",
        "ultra8x",
    ]
    if processor not in valid_processors:
        logger.warning(f"Invalid processor '{processor}', defaulting to 'pro'")
        processor = "pro"

    # Cost and time estimates
    cost_map = {
        "lite": "$5",
        "base": "$10",
        "core": "$30",
        "core2x": "$60",
        "pro": "$100",
        "ultra": "$300",
        "ultra2x": "$600",
        "ultra4x": "$1,200",
        "ultra8x": "$2,400",
    }
    time_map = {
        "lite": "5-60s",
        "base": "15-100s",
        "core": "1-5min",
        "core2x": "1-5min",
        "pro": "3-9min",
        "ultra": "5-25min",
        "ultra2x": "5-25min",
        "ultra4x": "8-30min",
        "ultra8x": "8-30min",
    }

    # Request user approval
    logger.info("Requesting user approval for research task")
    approval = await ctx.elicit(
        message=f"""
APPROVAL REQUIRED

Research Query: {query}
Processor: {processor}
Estimated Time: {time_map.get(processor, "unknown")}
API Cost: {cost_map.get(processor, "unknown")} per 1,000 queries

Approve this research task?
        """,
        schema=ApprovalSchema,
    )

    if not approval.data.approved:
        logger.info("Research cancelled by user")
        return {"status": "cancelled", "message": "Research cancelled by user"}

    # Check client availability
    if parallel_client is None:
        logger.error("Parallel AI client not configured")
        return {
            "status": "error",
            "message": "Parallel AI client not configured. Set PARALLEL_API_KEY in .env file.",
        }

    try:
        # Execute research
        logger.info(f"Creating research run with processor '{processor}'")
        await ctx.report_progress(0.1, 1.0, "Initiating research...")

        run = parallel_client.task_run.create(input=query, processor=processor)
        logger.info(f"Research run created: run_id={run.run_id}")

        # Poll for completion
        poll_count = 0
        while True:
            status = parallel_client.task_run.retrieve(run.run_id)
            if not status.is_active:
                logger.info(
                    f"Research completed after {poll_count} polls: status={status.status}"
                )
                break

            poll_count += 1
            await ctx.report_progress(0.5, 1.0, f"Researching... ({status.status})")
            await asyncio.sleep(10)

        # Retrieve results
        result = parallel_client.task_run.result(run.run_id)

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

        logger.info(
            f"Research successful: {len(citations)} citation groups, content length={len(content)}"
        )
        await ctx.report_progress(1.0, 1.0, "Research complete")

        return {
            "status": "complete",
            "content": content,
            "citations": citations,
            "processor": processor,
            "run_id": run.run_id,
        }

    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        return {"status": "error", "message": f"Research failed: {str(e)}"}


@mcp.tool()
async def quick_research(query: str, ctx: Context) -> Dict[str, Any]:
    """
    Quick research using Lite processor (5-60s, $5/1K queries).

    No approval required for fast, low-cost queries.

    Parameters
    ----------
    query : str
        Quick research question
    ctx : Context
        MCP context for progress reporting

    Returns
    -------
    dict
        Research results containing:
        - status : str - "complete" or "error"
        - content : str - Research answer
        - processor : str - Always "lite"
        - run_id : str - Parallel AI run ID

    Examples
    --------
    >>> result = await quick_research("What is OAuth 2.1?", ctx)
    """
    logger.info(f"Quick research request: query='{query}'")

    if parallel_client is None:
        logger.error("Parallel AI client not configured")
        return {
            "status": "error",
            "message": "Parallel AI client not configured.",
        }

    try:
        await ctx.report_progress(0.3, 1.0, "Quick research in progress...")

        run = parallel_client.task_run.create(input=query, processor="lite")
        logger.info(f"Quick research run created: run_id={run.run_id}")

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

        logger.info(f"Quick research successful: content length={len(content)}")
        await ctx.report_progress(1.0, 1.0, "Complete")

        return {
            "status": "complete",
            "content": content,
            "processor": "lite",
            "run_id": run.run_id,
        }

    except Exception as e:
        logger.error(f"Quick research failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    print("Starting Parallel AI MCP Server...")
    print(f"Timeout: 360 seconds")
    print(f"Default Processor: {os.getenv('DEFAULT_PROCESSOR', 'pro')}")

    mcp.run()
