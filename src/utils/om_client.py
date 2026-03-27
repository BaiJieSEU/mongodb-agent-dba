"""Ops Manager REST API client (BL-013, BL-015).

Read-only HTTP Digest auth wrapper for the OM public API v1.0.
All methods return empty/None on failure — callers never need to handle exceptions.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPDigestAuth

logger = logging.getLogger(__name__)

_TIMEOUT_S = 10


class OMClient:
    """Thin read-only client for the Ops Manager Public API v1.0."""

    def __init__(self, url: str, group_id: str, public_key: str, private_key: str) -> None:
        self._root = f"{url.rstrip('/')}/api/public/v1.0"
        self._base = f"{self._root}/groups/{group_id}"
        self._auth = HTTPDigestAuth(public_key, private_key)

    # ── private ────────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Optional[dict]:
        try:
            r = requests.get(
                f"{self._base}{path}",
                auth=self._auth,
                params=params or {},
                timeout=_TIMEOUT_S,
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            logger.warning("OM API [%s]: %s", path, exc)
            return None

    @staticmethod
    def _latest(measurements: list, metric: str) -> Optional[float]:
        """Return the most-recent non-null data point value for a named metric."""
        for meas in measurements:
            if meas.get("name") == metric:
                for point in reversed(meas.get("dataPoints", [])):
                    v = point.get("value")
                    if v is not None:
                        return float(v)
        return None

    # ── public ─────────────────────────────────────────────────────────────────

    def get_version(self) -> Optional[str]:
        """Return the Ops Manager server version string, or None on failure."""
        try:
            r = requests.get(f"{self._root}/", auth=self._auth, timeout=_TIMEOUT_S)
            r.raise_for_status()
            return r.json().get("version")
        except Exception as exc:
            logger.warning("OM version check failed: %s", exc)
            return None

    def get_hosts(self) -> List[Dict]:
        """Return all registered host docs for the group; [] on failure."""
        data = self._get("/hosts")
        return data.get("results", []) if data else []

    def get_host_measurements(
        self,
        host_id: str,
        metrics: List[str],
        period: str = "PT5M",
        granularity: str = "PT1M",
    ) -> Dict[str, Optional[float]]:
        """Return {metric_name: latest_value} for each requested metric."""
        data = self._get(
            f"/hosts/{host_id}/measurements",
            params={"granularity": granularity, "period": period, "m": metrics},
        )
        if data is None:
            return {m: None for m in metrics}
        meas_list = data.get("measurements", [])
        return {m: self._latest(meas_list, m) for m in metrics}

    def get_disk_name(self, host_id: str) -> Optional[str]:
        """Return the first disk partition name, or None."""
        data = self._get(f"/hosts/{host_id}/disks")
        if not data:
            return None
        results = data.get("results", [])
        return results[0].get("partitionName") if results else None

    def get_disk_measurements(
        self,
        host_id: str,
        partition: str,
        metrics: List[str],
        period: str = "PT5M",
        granularity: str = "PT1M",
    ) -> Dict[str, Optional[float]]:
        """Same shape as get_host_measurements but for a disk partition."""
        data = self._get(
            f"/hosts/{host_id}/disks/{partition}/measurements",
            params={"granularity": granularity, "period": period, "m": metrics},
        )
        if data is None:
            return {m: None for m in metrics}
        meas_list = data.get("measurements", [])
        return {m: self._latest(meas_list, m) for m in metrics}
