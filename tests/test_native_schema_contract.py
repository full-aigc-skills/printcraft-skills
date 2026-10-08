"""完整检查原生Schema支持边界，不能由未选中的分支隐藏未知约束。"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT.name.removesuffix('-skills')

class NativeSchemaContract(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('gateway', ROOT/'skills'/f'{DOMAIN}-use/scripts/command_gateway.py')
        self.gateway = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gateway)

    def test_unknown_constraint_in_unselected_branch_is_refused(self):
        schema = {'anyOf': [{'type': 'object'}, {'not': {'type': 'string'}}]}
        with self.assertRaisesRegex(ValueError, 'unsupported_schema_constraint'):
            self.gateway.validate_schema(schema, {})

    def test_unknown_constraint_in_missing_property_is_refused(self):
        schema = {'type': 'object', 'properties': {'optional': {'format': 'date-time'}}}
        with self.assertRaisesRegex(ValueError, 'unsupported_schema_constraint'):
            self.gateway.validate_schema(schema, {})

    def test_malformed_schema_is_a_controlled_failure(self):
        for schema in [
            {'type': []}, {'type': 'object', 'required': [False]},
            {'type': 'object', 'additionalProperties': 'yes'},
            {'type': 'array', 'items': []}, {'type': 'number', 'minimum': True},
            {'type': 'string', 'minLength': -1}, {'type': 'string', 'pattern': '['},
            {'enum': 'abc'}, {'anyOf': [{'type': 'object'}, 123]},
        ]:
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, 'invalid_native_schema|unsupported_schema_type'):
                self.gateway.validate_schema(schema, {})

    def test_numeric_exponent_overflow_is_refused_by_json_reader(self):
        for token in ['1e10000', '-1e10000']:
            with self.assertRaisesRegex(ValueError, 'nonfinite_json_number'):
                self.gateway.strict_json('{"nested": ['+token+']}')
        self.assertEqual(self.gateway.strict_json('{"n": 1.5e2}'), {'n': 150.0})

    def test_json_number_equivalence_keeps_booleans_distinct(self):
        self.gateway.validate_schema({'enum': [1]}, 1.0)
        self.gateway.validate_schema({'const': {'values': [1.0, True]}}, {'values': [1, True]})
        for schema, value in [({'enum': [True]}, 1), ({'const': {'value': True}}, {'value': 1})]:
            with self.assertRaisesRegex(ValueError, 'parameter_enum_mismatch|parameter_const_mismatch'):
                self.gateway.validate_schema(schema, value)

    def test_boolean_schema_and_nested_rejection(self):
        self.gateway.validate_schema(True, {'anything': [1, True]})
        self.gateway.validate_schema({'type': 'object', 'properties': {'blocked': False}}, {})
        for schema, value in [(False, None), ({'properties': {'blocked': False}}, {'blocked': 1})]:
            with self.assertRaisesRegex(ValueError, 'parameter_schema_false'):
                self.gateway.validate_schema(schema, value)

    def test_valid_combinations_and_additional_properties_remain_supported(self):
        schema = {'type': 'object', 'required': ['value'], 'properties': {
            'value': {'anyOf': [{'type': 'integer', 'minimum': 1}, {'type': 'string', 'pattern': '^ok$'}]},
        }, 'additionalProperties': {'type': 'boolean'}}
        for value in [{'value': 2}, {'value': 'ok', 'flag': True}]:
            self.gateway.validate_schema(schema, value)
        with self.assertRaises(ValueError):
            self.gateway.validate_schema(schema, {'value': 0})

if __name__ == '__main__':
    unittest.main()
