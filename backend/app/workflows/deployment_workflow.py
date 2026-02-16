"""
Overview: Deployment execution workflows — original and saga-based deployment pipelines.
Architecture: Temporal workflows for deployment pipeline (Section 9.1)
Dependencies: temporalio, app.workflows.activities.deployment
Concepts: DeploymentExecutionWorkflow (legacy shim), DeploymentSagaWorkflow (saga pattern
    with compensations: resolve → create CI → deploy → finalize, with rollback on failure).
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.deployment import (
        create_deployment_ci,
        delete_deployment_ci,
        finalize_deployment,
        release_all_allocations,
        resolve_deployment_parameters,
        resolve_parameters_via_rm,
        update_deployment_status,
    )


@workflow.defn
class DeploymentExecutionWorkflow:
    """Legacy deployment workflow — resolve parameters, then mark complete.

    Deprecated: Use DeploymentSagaWorkflow for new deployments.
    """

    @workflow.run
    async def run(self, deployment_id: str) -> str:
        # Step 1: Resolve parameters
        try:
            await workflow.execute_activity(
                resolve_deployment_parameters,
                deployment_id,
                start_to_close_timeout=timedelta(minutes=5),
            )
        except Exception:
            await workflow.execute_activity(
                update_deployment_status,
                args=[deployment_id, "FAILED"],
                start_to_close_timeout=timedelta(seconds=30),
            )
            return "FAILED"

        # Step 2: (Future) Execute Pulumi stack operation

        # Step 3: Mark as DEPLOYED
        await workflow.execute_activity(
            update_deployment_status,
            args=[deployment_id, "DEPLOYED"],
            start_to_close_timeout=timedelta(seconds=30),
        )

        return "DEPLOYED"


@workflow.defn
class DeploymentSagaWorkflow:
    """Saga-based deployment workflow with compensations.

    Steps:
        1. resolve_parameters_via_rm → compensation: release_all_allocations
        2. create_deployment_ci → compensation: delete_deployment_ci
        3. deploy_to_cloud (placeholder) → compensation: destroy_cloud_resource (placeholder)
        4. finalize_deployment (mark DEPLOYED, CI lifecycle→active)
    """

    @workflow.run
    async def run(self, deployment_id: str) -> str:
        compensations: list[tuple] = []

        try:
            # Step 1: Resolve parameters via Resource Manager
            await workflow.execute_activity(
                resolve_parameters_via_rm,
                deployment_id,
                start_to_close_timeout=timedelta(minutes=5),
            )
            compensations.append(("release_all_allocations", deployment_id))

            # Step 2: Create CI and link to deployment
            ci_id = await workflow.execute_activity(
                create_deployment_ci,
                deployment_id,
                start_to_close_timeout=timedelta(minutes=2),
            )
            if ci_id:
                compensations.append(("delete_deployment_ci", deployment_id, ci_id))

            # Step 3: Deploy to cloud (placeholder for Phase 12 Pulumi integration)
            # await workflow.execute_activity(
            #     deploy_to_cloud,
            #     args=[deployment_id],
            #     start_to_close_timeout=timedelta(minutes=30),
            # )
            # compensations.append(("destroy_cloud_resource", deployment_id))

            # Step 4: Finalize — mark DEPLOYED, CI→active
            await workflow.execute_activity(
                finalize_deployment,
                deployment_id,
                start_to_close_timeout=timedelta(seconds=30),
            )

            return "DEPLOYED"

        except Exception:
            # Run compensations in reverse order
            for comp in reversed(compensations):
                try:
                    if comp[0] == "release_all_allocations":
                        await workflow.execute_activity(
                            release_all_allocations,
                            comp[1],
                            start_to_close_timeout=timedelta(minutes=2),
                        )
                    elif comp[0] == "delete_deployment_ci":
                        await workflow.execute_activity(
                            delete_deployment_ci,
                            args=[comp[1], comp[2]],
                            start_to_close_timeout=timedelta(seconds=30),
                        )
                except Exception:
                    workflow.logger.exception("Compensation '%s' failed", comp[0])

            # Mark deployment as FAILED
            await workflow.execute_activity(
                update_deployment_status,
                args=[deployment_id, "FAILED"],
                start_to_close_timeout=timedelta(seconds=30),
            )

            return "FAILED"
