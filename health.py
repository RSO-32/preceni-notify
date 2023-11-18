from config import Config
import shutil


class Health:
    force_fail = False

    @staticmethod
    def check_health():
        checks = []
        checks.append({"name": "database", "status": Health.checkDb()})
        checks.append({"name": "disk", "status": Health.checkDisk()})
        checks.append({"name": "test", "status": Health.checkTest()})

        status = "UP" if all(check["status"] == "UP" for check in checks) else "DOWN"
        return status, checks

    @staticmethod
    def checkDb():
        try:
            cursor = Config.conn.cursor()
            cursor.execute("SELECT VERSION()")
            results = cursor.fetchone()
            if results:
                return "UP"
            else:
                return "DOWN"
        except:
            return "DOWN"

    @staticmethod
    def checkDisk():
        _, _, free = shutil.disk_usage("/")

        _10_mb = 10.0 * 1024 * 1024

        return "UP" if free > _10_mb else "DOWN"

    @staticmethod
    def checkTest():
        return "DOWN" if Health.force_fail else "UP"
