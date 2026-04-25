# This project was developed with assistance from AI tools.
"""Auto-rollback: revert the latest policy-version commit via GitHub API."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

ANOMALY_THRESHOLD = 0.85


def should_rollback(anomaly_score: float | None) -> bool:
    """Return True if anomaly score exceeds the rollback threshold."""
    if anomaly_score is None:
        return False
    return anomaly_score >= ANOMALY_THRESHOLD


async def trigger_rollback(
    factory: str,
    robot_id: str,
    anomaly_score: float,
    trace_id: str,
    log: BoundLogger,
) -> bool:
    """Create a git revert of the latest policy-version commit via GitHub API.

    Returns True if the revert was created successfully.
    """
    import httpx

    github_token = os.environ.get("GITHUB_TOKEN", "")
    github_repo = os.environ.get("GITHUB_REPO", "jeremyary/industrial-ai-showcase")
    github_branch = os.environ.get("GITHUB_BRANCH", "main")

    if not github_token:
        log.warning("rollback.skipped", reason="GITHUB_TOKEN not set")
        return False

    log.info(
        "rollback.triggered",
        factory=factory,
        robot_id=robot_id,
        anomaly_score=anomaly_score,
        trace_id=trace_id,
    )

    api_base = f"https://api.github.com/repos/{github_repo}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        commits_resp = await client.get(
            f"{api_base}/commits",
            headers=headers,
            params={"sha": github_branch, "path": f"infrastructure/gitops/apps/workloads/{factory}/policy-version.yaml", "per_page": 1},
        )
        if commits_resp.status_code != 200 or not commits_resp.json():
            log.error("rollback.no_commit_found", status=commits_resp.status_code)
            return False

        target_sha = commits_resp.json()[0]["sha"]
        log.info("rollback.reverting", commit_sha=target_sha)

        revert_resp = await client.post(
            f"{api_base}/git/refs",
            headers=headers,
            json={
                "message": f"auto-rollback: revert policy on {factory} (anomaly={anomaly_score:.2f}, trace={trace_id})",
                "sha": target_sha,
            },
        )

        if revert_resp.status_code in (200, 201):
            log.info("rollback.complete", factory=factory, reverted_sha=target_sha)
            return True

        log.error("rollback.failed", status=revert_resp.status_code, body=revert_resp.text)
        return False
