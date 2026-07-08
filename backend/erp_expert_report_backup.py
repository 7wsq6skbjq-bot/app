"""Daily backup of expert reports — safeguard against accidental deletes.

For each report we snapshot to a Mongo collection `erp_expert_report_backups`
holding:
  - the full report doc (metadata + doors + photos array — pointing to
    photo BLOBS which stay in GridFS forever unless explicitly purged)
  - a `backed_up_at` timestamp
  - a `report_id` field for quick lookup

Retention: 90 days. The scheduler prunes older snapshots on each run.

Why not export a ZIP file to disk? Because the container's disk is wiped
on every redeploy (same problem we already solved for photos). Keeping
backups inside MongoDB means they persist across redeploys.

Photos are NOT re-uploaded to GridFS each day — the GridFS entries live
already, keyed by the original photo_id. The report snapshot references
them by id, so restore is straightforward :
   1. Insert the snapshotted report doc back into `erp_expert_reports`
   2. GridFS entries are already there → hydrate on next PDF request
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger("portech.erp")

RETENTION_DAYS = 90


async def _run_backup(db: AsyncIOMotorDatabase) -> dict:
    """Snapshot every current expert report + prune snapshots older than
    RETENTION_DAYS."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    stamp = now.strftime("%Y-%m-%dT%H-%M-%S")

    reports_cursor = db.erp_expert_reports.find({}, {"_id": 0})
    inserted = 0
    async for r in reports_cursor:
        snapshot = {
            "id": f"{r['id']}::{stamp}",       # composite key: report_id::timestamp
            "report_id": r["id"],
            "report_number": r.get("number"),
            "client_name": (r.get("client_snapshot") or {}).get("name"),
            "project_name": r.get("project_name"),
            "backed_up_at": now_iso,
            "photo_count": len(r.get("photos") or []),
            "door_count": len(r.get("doors") or []),
            "report": r,                       # full doc for restore
        }
        await db.erp_expert_report_backups.replace_one(
            {"id": snapshot["id"]}, snapshot, upsert=True,
        )
        inserted += 1

    # Prune snapshots older than RETENTION_DAYS
    cutoff = (now - timedelta(days=RETENTION_DAYS)).isoformat()
    pruned = await db.erp_expert_report_backups.delete_many(
        {"backed_up_at": {"$lt": cutoff}},
    )
    logger.info(
        "Expert-report backup done: %d snapshotted, %d pruned (cutoff %s)",
        inserted, pruned.deleted_count, cutoff,
    )
    return {"snapshotted": inserted, "pruned": pruned.deleted_count,
            "cutoff": cutoff, "at": now_iso}


def start_backup_scheduler(db: AsyncIOMotorDatabase) -> AsyncIOScheduler:
    """Daily at 02:00 America/Montreal — quiet hour, low load."""
    sched = AsyncIOScheduler(timezone="America/Montreal")
    sched.add_job(
        _run_backup, "cron", args=[db],
        hour=2, minute=0,
        id="expert_report_daily_backup",
        replace_existing=True,
    )
    sched.start()
    logger.info("Expert-report backup scheduler started (daily 02:00 America/Montreal)")
    return sched


def register_routes(router: APIRouter, db: AsyncIOMotorDatabase, auth_dep) -> None:
    """Admin endpoints to trigger a backup manually, list snapshots, and
    restore one."""

    @router.post("/expert-reports/backup/run")
    async def trigger_backup(_: dict = Depends(auth_dep)):
        return await _run_backup(db)

    @router.get("/expert-reports/backup/list")
    async def list_snapshots(
        report_id: Optional[str] = None,
        limit: int = 50,
        _: dict = Depends(auth_dep),
    ):
        q = {"report_id": report_id} if report_id else {}
        cur = db.erp_expert_report_backups.find(
            q, {"_id": 0, "report": 0},    # drop the fat "report" doc from the list
        ).sort("backed_up_at", -1).limit(max(1, min(limit, 500)))
        return [s async for s in cur]

    @router.post("/expert-reports/backup/{snapshot_id}/restore")
    async def restore_snapshot(snapshot_id: str, _: dict = Depends(auth_dep)):
        """Restore a report from a snapshot. The snapshot's full report doc
        overwrites (upserts) the current live report in `erp_expert_reports`.
        Any GridFS photo entries are left intact — the restored report just
        starts referencing them again."""
        snap = await db.erp_expert_report_backups.find_one(
            {"id": snapshot_id}, {"_id": 0},
        )
        if not snap:
            raise HTTPException(404, "Snapshot introuvable")
        report_doc = snap.get("report")
        if not report_doc:
            raise HTTPException(500, "Snapshot corrompu (report doc absent)")
        await db.erp_expert_reports.replace_one(
            {"id": report_doc["id"]}, report_doc, upsert=True,
        )
        logger.info("Restored report %s from snapshot %s",
                    report_doc.get("id"), snapshot_id)
        return {"restored": report_doc["id"], "from_snapshot": snapshot_id,
                "backed_up_at": snap.get("backed_up_at")}
