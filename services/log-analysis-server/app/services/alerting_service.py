"""
Alerting Service

Automatic anomaly detection for log analysis.
Runs background checks every 5 minutes.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import asyncio


class AlertingService:
    """자동 이상 탐지 및 알림"""

    def __init__(self, query_repo):
        self._query_repo = query_repo
        self._thresholds = {
            "error_rate_spike": 0.1,      # 10% 증가
            "slow_api_threshold": 2000,   # 2 seconds
            "service_down_minutes": 5     # 5분간 로그 없음
        }
        self._alert_history: List[Dict] = []

    async def check_anomalies(self) -> List[Dict]:
        """
        Run all anomaly checks

        Returns:
            List of detected alerts
        """
        alerts = []

        # Check 1: Error rate spike
        alert = await self._check_error_rate_spike()
        if alert:
            alerts.append(alert)

        # Check 2: Slow APIs
        alert = await self._check_slow_apis()
        if alert:
            alerts.append(alert)

        # Check 3: Service down
        alert = await self._check_service_down()
        if alert:
            alerts.append(alert)

        # Store in history
        for alert in alerts:
            self._alert_history.append({
                **alert,
                "timestamp": datetime.now().isoformat()
            })

        # Keep only last 100 alerts
        if len(self._alert_history) > 100:
            self._alert_history = self._alert_history[-100:]

        return alerts

    async def _check_error_rate_spike(self) -> Optional[Dict]:
        """
        Check for error rate spike

        Compares current error rate (last 5 min) with baseline (30-35 min ago)
        """
        # Current rate (last 5 minutes)
        sql_current = """
        SELECT COUNT(*) as error_count
        FROM logs
        WHERE level = 'ERROR'
          AND created_at > NOW() - INTERVAL '5 minutes'
          AND deleted = FALSE
        """
        try:
            current_results, _ = await self._query_repo.execute_sql(sql_current)
            current_count = current_results[0]["error_count"] if current_results else 0

            # Baseline rate (30-35 minutes ago)
            sql_baseline = """
            SELECT COUNT(*) as error_count
            FROM logs
            WHERE level = 'ERROR'
              AND created_at BETWEEN NOW() - INTERVAL '35 minutes' AND NOW() - INTERVAL '30 minutes'
              AND deleted = FALSE
            """
            baseline_results, _ = await self._query_repo.execute_sql(sql_baseline)
            baseline_count = baseline_results[0]["error_count"] if baseline_results else 0

            # Check spike
            if baseline_count > 0:
                spike_ratio = (current_count - baseline_count) / baseline_count
                if spike_ratio > self._thresholds["error_rate_spike"]:
                    severity = "critical" if spike_ratio > 0.5 else "warning"
                    return {
                        "type": "error_rate_spike",
                        "severity": severity,
                        "message": f"에러율 {spike_ratio*100:.1f}% 증가 감지 (최근 5분)",
                        "data": {
                            "current_count": current_count,
                            "baseline_count": baseline_count,
                            "spike_percentage": round(spike_ratio * 100, 1)
                        }
                    }
        except Exception as e:
            print(f"Error in _check_error_rate_spike: {e}")

        return None

    async def _check_slow_apis(self) -> Optional[Dict]:
        """
        Detect slow APIs (> 2 seconds)
        """
        sql = f"""
        SELECT path, service, AVG(duration_ms) as avg_duration, COUNT(*) as count
        FROM logs
        WHERE duration_ms > {self._thresholds["slow_api_threshold"]}
          AND path IS NOT NULL
          AND created_at > NOW() - INTERVAL '10 minutes'
          AND deleted = FALSE
        GROUP BY path, service
        HAVING COUNT(*) >= 3
        ORDER BY avg_duration DESC
        LIMIT 5
        """

        try:
            results, _ = await self._query_repo.execute_sql(sql)

            if results:
                return {
                    "type": "slow_api",
                    "severity": "warning",
                    "message": f"{len(results)}개 느린 API 감지 (>2초)",
                    "data": {
                        "slow_apis": results
                    }
                }
        except Exception as e:
            print(f"Error in _check_slow_apis: {e}")

        return None

    async def _check_service_down(self) -> Optional[Dict]:
        """
        Check if any service stopped logging
        """
        try:
            # Get active services from last hour
            sql_active = """
            SELECT DISTINCT service
            FROM logs
            WHERE created_at > NOW() - INTERVAL '1 hour'
              AND deleted = FALSE
            """
            active_services, _ = await self._query_repo.execute_sql(sql_active)

            # Check each service's recent logs
            down_services = []
            for row in active_services:
                service = row["service"]
                sql_recent = f"""
                SELECT COUNT(*) as count
                FROM logs
                WHERE service = '{service}'
                  AND created_at > NOW() - INTERVAL '{self._thresholds["service_down_minutes"]} minutes'
                  AND deleted = FALSE
                """
                results, _ = await self._query_repo.execute_sql(sql_recent)

                if results and results[0]["count"] == 0:
                    down_services.append(service)

            if down_services:
                return {
                    "type": "service_down",
                    "severity": "critical",
                    "message": f"{len(down_services)}개 서비스 로그 없음 (5분)",
                    "data": {
                        "services": down_services
                    }
                }
        except Exception as e:
            print(f"Error in _check_service_down: {e}")

        return None

    def get_alert_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent alerts

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of recent alerts
        """
        return self._alert_history[-limit:]


# Singleton
_alerting_service = None


def get_alerting_service(query_repo) -> AlertingService:
    """Get global alerting service instance"""
    global _alerting_service
    if _alerting_service is None:
        _alerting_service = AlertingService(query_repo)
    return _alerting_service
