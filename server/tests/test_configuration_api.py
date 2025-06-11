import requests

class TestConfigurationAPI:
    def test_job_history_settings_present(self, server_url):
        resp = requests.get(f"{server_url}/api/configuration", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        settings = data.get("settings", {})
        for key in [
            "job_history_persistence_enabled",
            "job_history_storage_backend",
            "job_history_storage_path",
            "job_history_max_entries",
            "job_history_max_age_days",
        ]:
            assert key in settings

