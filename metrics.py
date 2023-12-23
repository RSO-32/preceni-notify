from dataclasses import dataclass
import shutil, psutil


@dataclass
class Metric:
    name: str
    value: str


class Metrics:
    @staticmethod
    def get_metrics():
        metrics = []

        total, used, free = shutil.disk_usage("/")

        metrics.append(Metric("disk_total", str(total)))
        metrics.append(Metric("disk_used", str(used)))
        metrics.append(Metric("disk_free", str(free)))
        metrics.append(Metric("cpu_percent", str(psutil.cpu_percent())))
        metrics.append(Metric("ram_percent", str(psutil.virtual_memory().percent)))

        return metrics
