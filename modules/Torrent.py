import hashlib
import math
import time
from threading import Lock
from threading import Thread

from . import trackerAPI
from .TorrentWriter import TorrentWriter
from .config import CONFIG
from .Peer import Peer
from .TorrentMetainfo import TorrentMetainfo
from .TorrentStates import TorrentStates


class Torrent:
    def __init__(self, metainfo):
        self.metainfo = metainfo
        self.downloaded_data_len = 0
        self.prev_time = time.time()
        self.writer = TorrentWriter(metainfo)
        self.prev_peers_count = 1
        self.peers = {}
        self.peers_blacklist = set()
        self.peers_lock = Lock()
        self.p_blocks = [self._get_initial_blocks_list(i)
                         for i in range(len(metainfo.pieces))]
        self.p_numblocks = [0] * len(metainfo.pieces)
        self.exp_p_blocks = {}
        self._init_exp_p_blocks()
        self.exp_p_blocks_lock = Lock()
        self.state = (TorrentStates.NOT_STARTED if self.progress != 1
                      else TorrentStates.DOWNLOADED)

    def _get_initial_blocks_list(self, piece_idx):
        block_len = CONFIG['int_block_len']
        cur_piece_len = self.metainfo.get_piece_len_at(piece_idx)
        cur_blocks_count = math.ceil(cur_piece_len / block_len)
        return [None] * cur_blocks_count

    def _init_exp_p_blocks(self):
        exp_pieces = self.writer.get_uncompleted_piece_indexes()
        for piece_idx in exp_pieces:
            self.exp_p_blocks[piece_idx] = {
                b_i for b_i in range(len(self.p_blocks[piece_idx]))}

    def _get_new_ip_port_list(self):
        try:
            return trackerAPI.get_peers_list_by_torrent_metainfo(self.metainfo)
        except trackerAPI.PeersFindingError:
            return []

    # "pbi" is (piece_idx, block_idx)
    def get_pbi_for_peer(self, peer):
        res_piece_idx = res_block_idx = None
        with self.exp_p_blocks_lock:
            for piece_idx in self.exp_p_blocks:
                cur_blocks = self.exp_p_blocks[piece_idx]
                if peer.have_piece(piece_idx):
                    res_piece_idx = piece_idx
                    if len(cur_blocks) != 0:
                        res_block_idx = cur_blocks.pop()
                        break
        return res_piece_idx, res_block_idx

    def handle_incorrect_pbi(self, piece_idx, block_idx):
        with self.exp_p_blocks_lock:
            self.exp_p_blocks[piece_idx].add(block_idx)

    def handle_peer_disconnect(self, peer, peer_is_bad):
        if peer_is_bad:
            self.peers_blacklist.add(peer.name)
        with self.peers_lock:
            self.peers.pop(peer.name)
        if len(self.peers) < self.prev_peers_count * 0.7:
            self.add_new_peers()

    @property
    def progress(self):
        return 1 - len(self.exp_p_blocks) / len(self.p_blocks)

    @property
    def download_speed(self):
        cur_time = time.time()
        res_bits_count = self.downloaded_data_len * 8
        self.downloaded_data_len = 0
        res_time = cur_time - self.prev_time
        if res_time == 0:
            return '0 bit/s'
        self.prev_time = cur_time
        if res_bits_count / 1024 < 1:
            res_number = res_bits_count
            res_speed = 'bit/s'
        elif res_bits_count / 1024 ** 2 < 1:
            res_number = res_bits_count / 1024
            res_speed = 'Kbit/s'
        else:
            res_number = res_bits_count / 1024 ** 2
            res_speed = 'Mbit/s'
        return '{:.2f} {}'.format(res_number / res_time, res_speed)

    def add_new_peers(self):
        while True:
            ip_port_list = self._get_new_ip_port_list()
            threads = []
            for ip, port in ip_port_list:
                cur_thread = Thread(target=self._add_new_peer, args=(ip, port))
                threads.append(cur_thread)
                cur_thread.start()
            for thread in threads:
                thread.join()
            self.prev_peers_count = max(len(self.peers), 1)
            if len(self.peers) >= self.prev_peers_count:
                break
        with self.peers_lock:
            for peer in self.peers.values():
                if not peer.is_running:
                    Thread(target=peer.run_download, args=()).start()

    def _add_new_peer(self, ip, port):
        cur_ip_port = ip + ':' + str(port)
        if (cur_ip_port not in self.peers and
                    cur_ip_port not in self.peers_blacklist):
            peer = Peer(ip, port, self)
            if peer.is_available:
                with self.peers_lock:
                    self.peers[cur_ip_port] = peer

    def run_download(self):
        if self.state == TorrentStates.DOWNLOADED:
            return
        self.state = TorrentStates.STARTED
        self.add_new_peers()

    def pause_download(self):
        if self.state == TorrentStates.STARTED:
            self.state = TorrentStates.PAUSED
            self.peers.clear()

    def handle_block(self, piece_idx, block_idx, block):
        self.downloaded_data_len += len(block)
        self.p_blocks[piece_idx][block_idx] = block
        self.p_numblocks[piece_idx] += 1
        if self.p_numblocks[piece_idx] == len(self.p_blocks[piece_idx]):
            self.handle_piece(piece_idx)

    def handle_piece(self, piece_idx):
        piece = b''.join(self.p_blocks[piece_idx])
        cur_piece_hash = hashlib.sha1(piece).digest()
        if cur_piece_hash != self.metainfo.pieces[piece_idx]:
            self._handle_incorrect_piece(piece_idx)
            return
        self.p_blocks[piece_idx] = None
        self.writer.write_piece(piece_idx, piece)
        with self.exp_p_blocks_lock:
            self.exp_p_blocks.pop(piece_idx)
        # TODO: send 'have' msg to peers
        if len(self.exp_p_blocks) == 0:
            self.state = TorrentStates.DOWNLOADED

    def _handle_incorrect_piece(self, piece_idx):
        self.p_blocks[piece_idx] = self._get_initial_blocks_list(piece_idx)
        with self.exp_p_blocks_lock:
            self.exp_p_blocks[piece_idx] = {
                b_i for b_i in range(len(self.p_blocks[piece_idx]))}
            self.p_numblocks[piece_idx] = 0
