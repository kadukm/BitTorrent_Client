import os
import sys
import unittest
sys.path.append('..')

from modules.TorrentMetainfo import TorrentMetainfo


class TorrentMetainfoTests(unittest.TestCase):
    def test_very_simple_torrent(self):
        very_simple_torrent_path = os.path.join(os.getcwd(), 'resources',
                                                'very_simple_torrent')
        metainfo = TorrentMetainfo(very_simple_torrent_path)
        self.assertTrue(metainfo.is_single_file)
        self.assertEqual(metainfo.name, 'test_torrent')
        self.assertEqual(metainfo.announce_list, ['test_tracker'])
        self.assertEqual(metainfo.pieces, [b'00000000000000000000'])
        self.assertTrue(metainfo.piece_length == metainfo.length == 777)

    def test_torrent_with_few_files(self):
        torrent_with_few_files_path = os.path.join(os.getcwd(), 'resources',
                                                   'torrent_with_few_files')
        metainfo = TorrentMetainfo(torrent_with_few_files_path)
        self.assertFalse(metainfo.is_single_file)
        self.assertEqual(metainfo.name, 'test_torrent_with_few_files')
        self.assertEqual(metainfo.announce_list, ['test_tracker'])
        self.assertEqual(metainfo.pieces, [b'00000000000000000000'])
        self.assertTrue(metainfo.piece_length == metainfo.length == 6)
        for i in range(len(metainfo.files)):
            self.assertEqual(metainfo.files[i]['length'], i + 1)
            self.assertEqual(metainfo.files[i]['path'], 'file' + str(i + 1))

    def test_file_with_long_path(self):
        file_with_long_path = os.path.join(os.getcwd(), 'resources',
                                           'file_with_long_path')
        metainfo = TorrentMetainfo(file_with_long_path)
        self.assertFalse(metainfo.is_single_file)
        self.assertEqual(metainfo.name, 'file_with_long_path')
        self.assertEqual(metainfo.announce_list, ['test_tracker'])
        self.assertEqual(metainfo.pieces, [b'00000000000000000000'])
        self.assertTrue(metainfo.piece_length == metainfo.length == 6)
        exp_path = os.path.join('path1', 'path2', 'filename')
        self.assertEqual(metainfo.files[0]['path'], exp_path)
        self.assertEqual(metainfo.files[0]['length'], 6)

    def test_pieces_with_different_length(self):
        pieces_with_different_length_path = os.path.join(
            os.getcwd(), 'resources', 'pieces_with_different_length')
        metainfo = TorrentMetainfo(pieces_with_different_length_path)
        self.assertTrue(metainfo.is_single_file)
        self.assertEqual(metainfo.name, 'test_torrent')
        self.assertEqual(metainfo.announce_list, ['test_tracker'])
        self.assertEqual(metainfo.pieces, [b'00000000000000000000',
                                           b'11111111111111111111'])
        self.assertEqual(metainfo.length, 3)
        self.assertEqual(metainfo.get_piece_len_at(0), 2)
        self.assertEqual(metainfo.get_piece_len_at(1), 1)

    def test_few_announces(self):
        few_announces = os.path.join(os.getcwd(), 'resources', 'few_announces')
        metainfo = TorrentMetainfo(few_announces)
        self.assertTrue(metainfo.is_single_file)
        self.assertEqual(metainfo.name, 'test_torrent')
        self.assertEqual(metainfo.pieces, [b'00000000000000000000'])
        self.assertTrue(metainfo.piece_length == metainfo.length == 777)
        self.assertEqual(len(metainfo.announce_list), 7)
        exp_announce_list = ['main_tracker', 'spare_tracker0', 'spare_tracker1',
                             'spare_tracker2', 'spare_tracker3',
                             'spare_tracker4', 'spare_tracker5']
        self.assertEqual(metainfo.announce_list, exp_announce_list)


if __name__ == '__main__':
    unittest.main()
