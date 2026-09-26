"""
监控与告警模块

提供：
1. 业务指标采集（会话数、完成率、工具调用）
2. 性能指标采集（延迟、吞吐量）
3. 成本指标采集（API 调用量、Token 用量）
4. 错误率监控
5. 告警规则引擎
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .logging import SessionLogger

_log = SessionLogger("monitoring")


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float = 0.0
    labels: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    metric: str
    condition: str
    threshold: float
    severity: AlertSeverity
    window_seconds: float = 60.0
    cooldown_seconds: float = 300.0
    message: str = ""


@dataclass
class Alert:
    """告警事件"""
    rule: AlertRule
    current_value: float
    timestamp: float = 0.0
    acknowledged: bool = False

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class MetricsCollector:
    """
    指标采集器

    支持 counter、gauge、histogram 三种指标类型
    """

    def __init__(self):
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._max_histogram_size = 1000
        self._lock = threading.Lock()

    def increment(self, name: str, value: float = 1.0, **labels):
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def set_gauge(self, name: str, value: float, **labels):
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def observe(self, name: str, value: float, **labels):
        key = self._make_key(name, labels)
        with self._lock:
            hist = self._histograms[key]
            hist.append(value)
            if len(hist) > self._max_histogram_size:
                self._histograms[key] = hist[-self._max_histogram_size:]

    def get_counter(self, name: str, **labels) -> float:
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    def get_gauge(self, name: str, **labels) -> float:
        key = self._make_key(name, labels)
        return self._gauges.get(key, 0.0)

    def get_histogram_stats(self, name: str, **labels) -> dict:
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])
        if not values:
            return {"count": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "max": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "avg": round(sum(sorted_vals) / n, 3),
            "p50": round(sorted_vals[int(n * 0.5)], 3),
            "p95": round(sorted_vals[min(int(n * 0.95), n - 1)], 3),
            "p99": round(sorted_vals[min(int(n * 0.99), n - 1)], 3),
            "max": round(sorted_vals[-1], 3),
        }

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    k: self.get_histogram_stats(k)
                    for k in list(self._histograms.keys())
                },
            }

    def _make_key(self, name: str, labels: dict) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


class AlertEngine:
    """
    告警引擎

    评估告警规则，触发告警通知
    """

    def __init__(self, metrics: MetricsCollector):
        self._metrics = metrics
        self._rules: list[AlertRule] = []
        self._active_alerts: dict[str, Alert] = {}
        self._callbacks: list[Callable] = []

    def add_rule(self, rule: AlertRule):
        self._rules.append(rule)

    def on_alert(self, callback: Callable):
        self._callbacks.append(callback)

    def evaluate(self) -> list[Alert]:
        """评估所有规则，返回新触发的告警"""
        new_alerts = []
        now = time.time()

        for rule in self._rules:
            value = self._get_metric_value(rule.metric, rule.window_seconds)
            triggered = self._check_condition(value, rule.condition, rule.threshold)

            if triggered:
                if rule.name in self._active_alerts:
                    active = self._active_alerts[rule.name]
                    if now - active.timestamp < rule.cooldown_seconds:
                        continue

                alert = Alert(rule=rule, current_value=value)
                self._active_alerts[rule.name] = alert
                new_alerts.append(alert)

                _log.warning(
                    "alert_triggered",
                    alert_name=rule.name,
                    severity=rule.severity.value,
                    metric=rule.metric,
                    value=value,
                    threshold=rule.threshold,
                )

                for cb in self._callbacks:
                    try:
                        cb(alert)
                    except Exception:
                        pass

        return new_alerts

    def _get_metric_value(self, metric: str, window: float) -> float:
        if metric == "error_rate":
            total = self._metrics.get_counter("requests_total")
            errors = self._metrics.get_counter("errors_total")
            if total == 0:
                return 0.0
            return (errors / total) * 100
        if "rate" in metric:
            stats = self._metrics.get_histogram_stats(metric)
            return stats.get("p95", 0)
        return self._metrics.get_gauge(metric)

    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        if condition == "gt":
            return value > threshold
        if condition == "lt":
            return value < threshold
        if condition == "gte":
            return value >= threshold
        if condition == "eq":
            return value == threshold
        return False

    def get_active_alerts(self) -> list[Alert]:
        return list(self._active_alerts.values())

    def acknowledge(self, rule_name: str):
        if rule_name in self._active_alerts:
            self._active_alerts[rule_name].acknowledged = True


class HealthChecker:
    """
    服务健康检查

    定期检查各依赖服务的可用性
    """

    def __init__(self):
        self._checks: dict[str, Callable] = {}
        self._results: dict[str, dict] = {}
        self._last_check: float = 0.0

    def register(self, name: str, check_func: Callable):
        self._checks[name] = check_func

    async def check_all(self) -> dict[str, dict]:
        now = time.time()
        results = {}

        for name, check_func in self._checks.items():
            try:
                start = time.time()
                ok, detail = await check_func()
                latency = round((time.time() - start) * 1000, 1)
                results[name] = {
                    "healthy": ok,
                    "latency_ms": latency,
                    "detail": detail,
                    "checked_at": now,
                }
            except Exception as exc:
                results[name] = {
                    "healthy": False,
                    "latency_ms": 0,
                    "detail": str(exc),
                    "checked_at": now,
                }

        self._results = results
        self._last_check = now
        return results

    def get_status(self) -> dict:
        return {
            "checks": self._results,
            "last_check": self._last_check,
            "overall_healthy": all(
                r.get("healthy", False) for r in self._results.values()
            ),
        }


# ─── 全局实例 ────────────────────────────────────────────────────────────────

metrics = MetricsCollector()
alert_engine = AlertEngine(metrics)
health_checker = HealthChecker()


def setup_default_alert_rules():
    """配置默认告警规则"""
    rules = [
        AlertRule(
            name="high_error_rate",
            metric="error_rate",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.CRITICAL,
            message="错误率超过 5%",
        ),
        AlertRule(
            name="high_latency_p95",
            metric="request_latency_rate",
            condition="gt",
            threshold=8000.0,
            severity=AlertSeverity.WARNING,
            message="P95 延迟超过 8 秒",
        ),
        AlertRule(
            name="high_session_count",
            metric="active_sessions",
            condition="gt",
            threshold=1000.0,
            severity=AlertSeverity.WARNING,
            message="活跃会话数超过 1000",
        ),
        AlertRule(
            name="high_cost_per_session",
            metric="cost_per_session",
            condition="gt",
            threshold=1.0,
            severity=AlertSeverity.WARNING,
            message="单次会话成本超过 $1",
        ),
    ]
    for rule in rules:
        alert_engine.add_rule(rule)


setup_default_alert_rules()
