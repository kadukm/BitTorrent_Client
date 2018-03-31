import sys
import unittest
sys.path.append('..')

from modules.BencodeParser import BencodeParser


class BencodeParserTests(unittest.TestCase):
    parser = BencodeParser()

    def test_simple_cases(self):
        self._check_case(b'd3:aaa3:aaae', {b'aaa': b'aaa'})  # strings
        self._check_case(b'd2:aai10ee', {b'aa': 10})  # int
        self._check_case(b'd2:aal2:bb2:ccee', {b'aa': [b'bb', b'cc']})  # list
        self._check_case(b'd2:aad2:bb2:ccee', {b'aa': {b'bb': b'cc'}})  # dict

    def test_empty_collections(self):
        self._check_case(b'de', {})
        self._check_case(b'd2:aalee', {b'aa': []})

    def test_empty_string(self):
        self._check_case(b'd3:key0:e', {b'key': b''})
        self._check_case(b'd0:5:valuee', {b'': b'value'})

    def test_key_e_in_dict(self):
        self._check_case(b'd1:e3:ende', {b'e': b'end'})

    def test_list_in_list(self):
        self._check_case(b'd4:listlleleleee', {b'list': [[], [], []]})

    def test_cases_with_find_info(self):
        self._check_case(b'd4:info3:tute', (7, 12, {b'info': b'tut'}), True)
        self._check_case(b'd4:info4:infoe', (7, 13, {b'info': b'info'}), True)

    def _check_case(self, data, exp_res, find_info_key=False):
        parse_res = self.parser.parse_data(data, find_info_key)
        self.assertEqual(exp_res, parse_res)


if __name__ == '__main__':
    unittest.main()
