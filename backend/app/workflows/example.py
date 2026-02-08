"""
Overview: Example Temporal workflow for testing the workflow pipeline.
Architecture: Temporal workflows (Section 9.1)
Dependencies: temporalio, app.workflows.activities.example
Concepts: Temporal workflows, worker validation
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.example import say_hello


@workflow.defn
class ExampleWorkflow:
    """Example workflow that runs a single activity."""

    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello,
            name,
            start_to_close_timeout=timedelta(seconds=30),
        )
