"""真实公开计划入口在不支持Schema时禁止编辑；目录进程为模拟。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class SchemaPreflight(unittest.TestCase):
    def test_hidden_unsupported_schema_stops_before_native_edit(self):
        scripts = ROOT/'skills/printcraft-use/scripts'
        spec = importlib.util.spec_from_file_location('gateway', scripts/'command_gateway.py')
        gateway = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gateway)
        catalog = [{'name': 'doc_info', 'input_schema': {'properties': {'optional': {'format': 'date-time'}}}}]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            plan = root/'plan.json'
            plan.write_text(json.dumps({'domain': 'printcraft', 'steps': [{'command': 'doc_info', 'params': {}}]}))
            output = root/'output'
            reply = io.StringIO()
            discovery = subprocess.CompletedProcess([], 0, json.dumps(catalog), '')
            with patch.object(sys, 'argv', ['commands.py', 'run', str(plan), '--output', str(output)]), patch.object(gateway.subprocess, 'run', return_value=discovery) as native, contextlib.redirect_stdout(reply):
                status = gateway.main('printcraft', scripts)
            self.assertEqual(status, 1)
            self.assertEqual(native.call_count, 1)
            self.assertIn('unsupported_schema_constraint', reply.getvalue())
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
