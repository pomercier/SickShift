import unittest
from unittest.mock import patch
import bootstrap_dependencies as bootstrap

class BootstrapTests(unittest.TestCase):
    def test_ready_environment_never_runs_pip(self):
        with patch.object(bootstrap.sys, 'prefix', '/isolated'), patch.object(bootstrap.sys, 'base_prefix', '/base'), patch.object(bootstrap, 'missing_modules', return_value=[]), patch.object(bootstrap.subprocess, 'run') as run:
            bootstrap.ensure_runtime()
        run.assert_not_called()

    def test_missing_dependencies_use_current_isolated_interpreter(self):
        with patch.object(bootstrap.sys, 'prefix', '/isolated'), patch.object(bootstrap.sys, 'base_prefix', '/base'), patch.object(bootstrap, 'missing_modules', side_effect=[['fastapi'], []]), patch.object(bootstrap.importlib.util, 'find_spec', return_value=object()), patch.object(bootstrap.subprocess, 'run') as run:
            bootstrap.ensure_runtime()
        command = run.call_args.args[0]
        self.assertEqual([bootstrap.sys.executable, '-m', 'pip', 'install'], command[:4])
        self.assertNotIn('--user', command)
        self.assertNotIn('--break-system-packages', command)

    def test_install_failure_stops_before_application_startup(self):
        with patch.object(bootstrap.sys, 'prefix', '/isolated'), patch.object(bootstrap.sys, 'base_prefix', '/base'), patch.object(bootstrap, 'missing_modules', return_value=['fastapi']), patch.object(bootstrap.importlib.util, 'find_spec', return_value=object()), patch.object(bootstrap.subprocess, 'run', side_effect=OSError('offline')):
            with self.assertRaisesRegex(SystemExit, 'internet connection'):
                bootstrap.ensure_runtime()

if __name__ == '__main__':
    unittest.main()
