import sys
import unittest

sys.path.append('..')

from modules import trackerAPI
from unittest.mock import Mock
from unittest.mock import patch


class TrackerTests(unittest.TestCase):
    @patch('modules.trackerAPI._get_peers_by_http')
    @patch('modules.trackerAPI._get_peers_by_udp')
    def test_http_udp_difference(self, udp_mock, http_mock):
        metainfo = Mock(announce_list=['http://hello.world.com:80'])
        trackerAPI.get_peers_list_by_torrent_metainfo(metainfo)
        http_mock.assert_called()
        udp_mock.assert_not_called()

    @patch('modules.trackerAPI._get_peers_by_http')
    @patch('modules.trackerAPI._get_peers_by_udp')
    def test_that_can_work_with_last_tracker(self, udp_mock, http_mock):
        def mock_side_effect(tracker, metainfo):
            if tracker == 'http://bad_tracker':
                raise Exception('bad tracker')
        udp_mock.side_effect = mock_side_effect
        http_mock.side_effect = mock_side_effect
        metainfo = Mock(announce_list=['http://bad_tracker',
                                       'udp://bad_tracker',
                                       'http://good_tracker'])
        trackerAPI.get_peers_list_by_torrent_metainfo(metainfo)

    def test_getting_peers_from_binary_data(self):
        data = (b'\x01\x02\x03\x04\x00\x05' +
                b'\x02\x03\x04\x05\x00\x06' +
                b'\x03\x04\x05\x06\x00\x07')
        peers = trackerAPI._get_peers_by_bin_data(data)
        self.assertEqual([('1.2.3.4', 5), ('2.3.4.5', 6), ('3.4.5.6', 7)],
                         peers)

    def test_PeersFindingError(self):
        with self.assertRaises(trackerAPI.PeersFindingError):
            metainfo = Mock(announce_list=[])
            trackerAPI.get_peers_list_by_torrent_metainfo(metainfo)

    def test_api_regex(self):
        self._check_regex_case('udp://tracker.com:', False)
        self._check_regex_case('udp://tracker.com:80', True)
        self._check_regex_case('udp://very.very.very.long.url.com:3456', True)
        self._check_regex_case('udp://tracker.com:234/announce', True)
        self._check_regex_case('udp://35.36.2.222:34565', True)
        self._check_regex_case('udp://35.36.2.222:34565/announce', True)
        self._check_regex_case('udp://35.36.2.222:345657', False)
        self._check_regex_case('ud://35.36.2.222:34563', False)
        self._check_regex_case('udp://aaaa:ffff:1111::1:206', True)
        self._check_regex_case('udp://[1111:abcd::aaaa]:11111', True)

    def _check_regex_case(self, string, is_matched):
        res_is_matched = trackerAPI.UDP_REGEX.search(string) is not None
        self.assertEqual(is_matched, res_is_matched)


if __name__ == '__main__':
    unittest.main()
