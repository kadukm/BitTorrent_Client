import os
import sys
import unittest

sys.path.append('..')

from modules.TorrentWriter import TorrentWriter
from modules.TorrentMetainfo import TorrentMetainfo
from unittest.mock import PropertyMock
from unittest.mock import patch


class TorrentWriterTests(unittest.TestCase):
    @patch('modules.TorrentWriter.TorrentWriter.downloads_dir',
           new_callable=PropertyMock)
    @patch('modules.TorrentWriter.TorrentWriter.checkpoint_path',
           new_callable=PropertyMock)
    def test_writing_in_few_files(self, checkpoint_mock, downloads_mock):
        downloads_mock.return_value = os.path.join(
            os.getcwd(), 'resources', 'mock_downloads')
        checkpoint_mock.return_value = os.path.join(
            os.getcwd(), 'resources', 'mock_torrents_info', 'mock_sha1')
        torrent_for_real_writing_path = os.path.join(
            os.getcwd(), 'resources', 'torrent_for_real_writing_few_files')
        metainfo = TorrentMetainfo(torrent_for_real_writing_path)
        pieces = [b'\x01\x23\x45\x67'] * 4
        writer = TorrentWriter(metainfo)
        for piece_idx in range(len(pieces)):
            writer.write_piece(piece_idx, pieces[piece_idx])
        torrent_download_path = os.path.join(
            downloads_mock.return_value, 'torrent_for_real_writing_few_files')
        res = []
        exp_res = [b'\x01\x23\x45\x67\x01', b'\x23\x45', b'\x67\x01',
                   b'\x23\x45\x67', b'\x01\x23\x45\x67']
        for filename in os.listdir(torrent_download_path):
            with open(os.path.join(torrent_download_path, filename), 'rb') as f:
                res.append(f.read())
        self.assertEqual(exp_res, res)

    @patch('modules.TorrentWriter.TorrentWriter.downloads_dir',
           new_callable=PropertyMock)
    @patch('modules.TorrentWriter.TorrentWriter.checkpoint_path',
           new_callable=PropertyMock)
    def test_writing_in_single_file(self, checkpoint_mock, downloads_mock):
        downloads_mock.return_value = os.path.join(
            os.getcwd(), 'resources', 'mock_downloads')
        checkpoint_mock.return_value = os.path.join(
            os.getcwd(), 'resources', 'mock_torrents_info', 'mock_sha1')
        torrent_for_real_writing_path = os.path.join(
            os.getcwd(), 'resources', 'torrent_for_real_writing_single_file')
        metainfo = TorrentMetainfo(torrent_for_real_writing_path)
        pieces = [b'\x01\x23\x45\x67'] * 2
        writer = TorrentWriter(metainfo)
        for piece_idx in range(len(pieces)):
            writer.write_piece(piece_idx, pieces[piece_idx])
        torrent_download_path = os.path.join(
            downloads_mock.return_value, 'torrent_for_real_writing_single_file')
        with open(torrent_download_path, 'rb') as f:
            res = f.read()
        exp_res = b'\x01\x23\x45\x67' * 2
        self.assertEqual(exp_res, res)

    def test_get_info_about_pieced_from_bytes(self):
        self._check_test_getting_info(b'\xf0', [True]*4 + [False]*4)
        self._check_test_getting_info(b'\x69', [False, True, True, False] +
                                               [True, False, False, True])
        self._check_test_getting_info(b'\x10', [False]*3 + [True] + [False]*4)
        self._check_test_getting_info(b'\xaa', [True, False]*4)
        self._check_test_getting_info(b'\x55', [False, True]*4)
        self._check_test_getting_info(b'\x00\xf0',
                                      [False]*8 + [True]*4 + [False]*4)

    def _check_test_getting_info(self, data, exp_res):
        self.assertEqual(exp_res,
                         TorrentWriter.get_info_about_pieced_from_bytes(data))


if __name__ == '__main__':
    unittest.main()
