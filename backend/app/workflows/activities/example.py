"""
Overview: Example Temporal activity for testing the worker pipeline.
Architecture: Temporal activities (Section 9.1)
Dependencies: temporalio
Concepts: Temporal activities, worker validation
"""

from temporalio import activity


@activity.defn
async def say_hello(name: str) -> str:
    """Example activity that returns a greeting."""
    activity.logger.info(f"Running say_hello activity for {name}")
    return f"Hello, {name}!"
