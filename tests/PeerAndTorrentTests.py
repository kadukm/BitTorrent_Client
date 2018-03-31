import os
import sys
import unittest

sys.path.append('..')

from unittest.mock import PropertyMock
from unittest.mock import patch

from modules.Peer import Peer
from modules.Torrent import Torrent
from modules.TorrentMetainfo import TorrentMetainfo
from modules.TorrentStates import TorrentStates


class PeerAndTorrentTests(unittest.TestCase):
    @patch('modules.TorrentWriter.TorrentWriter._upd_checkpoint')
    @patch('modules.Torrent.Torrent.add_new_peers')
    @patch('modules.TorrentWriter.TorrentWriter.check_place_to_download')
    @patch('modules.TorrentWriter.TorrentWriter.check_checkpoint_path')
    @patch('modules.Peer.Peer._send_msg')
    @patch('modules.Peer.Peer._init_connection')
    @patch('modules.TorrentWriter.TorrentWriter.get_uncompleted_piece_indexes')
    @patch('modules.Peer.Peer.get_new_data_from_socket')
    @patch('modules.TorrentWriter.TorrentWriter.downloads_dir',
           new_callable=PropertyMock)
    def test_request_block(self, writer, data_getter, getter,
                           _0, _1, _2, _3, _4, _5):
        writer.return_value = os.path.join(
            os.getcwd(), 'resources', 'mock_downloads')
        getter.side_effect = [[0]]
        data_getter.side_effect = [
            Peer.build_msg(1),
            (b'\x00\x00\x40\x09\x07\x00\x00\x00\x00\x00\x00\x00\x00' +
             b'\xff' * (2 ** 14 - 1) + b'\xff'),
            (b'\x00\x00\x40\x09\x07\x00\x00\x00\x00\x00\x00\x00\x00'
             + b'\xff' * (2 ** 14 - 1) + b'\xfe')]

        metainfo = TorrentMetainfo(os.path.join(
            os.getcwd(), 'resources', 'torrent_for_peer_and_torrent'))
        metainfo.pieces[0] = (
            b'B\xbc\'"\xa6=\xef\x86\xca1_Et\xe0[\tS\x8d\xd2\xb7')
        torrent = Torrent(metainfo)
        peer0 = Peer('0.0.0.0', 1000, torrent)
        peer1 = Peer('1.1.1.1', 1111, torrent)
        torrent.state = TorrentStates.STARTED
        torrent.peers[peer0.name] = peer0
        torrent.peers[peer1.name] = peer1
        peer1.run_download()
        peer0._close()
        peer1._close()

        full_downloaded_torrent_path = os.path.join(
            writer.return_value, 'torrent_for_peer_and_torrent')
        with open(full_downloaded_torrent_path, 'rb') as f:
            res = f.read()
        exp_res = b'\xff' * (2 ** 14 - 1) + b'\xfe'
        self.assertEqual(exp_res, res)


if __name__ == '__main__':
    unittest.main()
