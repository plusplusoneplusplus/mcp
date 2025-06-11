import os
import json
import tempfile
import time
from unittest.mock import patch

from mcp_tools.command_executor.executor import CommandExecutor


class TestJobHistoryPersistence:
    def test_json_persistence_roundtrip(self):
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()
        path = tmp_file.name

        with patch('mcp_tools.command_executor.executor.env_manager') as mock_env:
            mock_env.load.return_value = None
            mock_env.get_setting.side_effect = lambda key, default: {
                'periodic_status_enabled': False,
                'periodic_status_interval': 30.0,
                'periodic_status_max_command_length': 60,
                'command_executor_max_completed_processes': 100,
                'command_executor_completed_process_ttl': 3600,
                'command_executor_auto_cleanup_enabled': False,
                'command_executor_cleanup_interval': 300,
                'job_history_persistence_enabled': True,
                'job_history_storage_backend': 'json',
                'job_history_storage_path': path,
                'job_history_max_entries': 100,
                'job_history_max_age_days': 30,
            }.get(key, default)

            executor = CommandExecutor()
            token = 'tok1'
            executor.completed_processes[token] = {'status': 'completed'}
            executor.completed_process_timestamps[token] =  time.time()
            executor._persist_completed_processes()

            # File should contain the job entry
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            assert len(data) >= 1
            token = data[-1]['token']

        # Load new instance to verify history reloads
        with patch('mcp_tools.command_executor.executor.env_manager') as mock_env:
            mock_env.load.return_value = None
            mock_env.get_setting.side_effect = lambda key, default: {
                'periodic_status_enabled': False,
                'periodic_status_interval': 30.0,
                'periodic_status_max_command_length': 60,
                'command_executor_max_completed_processes': 100,
                'command_executor_completed_process_ttl': 3600,
                'command_executor_auto_cleanup_enabled': False,
                'command_executor_cleanup_interval': 300,
                'job_history_persistence_enabled': True,
                'job_history_storage_backend': 'json',
                'job_history_storage_path': path,
                'job_history_max_entries': 100,
                'job_history_max_age_days': 30,
            }.get(key, default)

            executor2 = CommandExecutor()
            assert token in executor2.completed_processes

        os.remove(path)
