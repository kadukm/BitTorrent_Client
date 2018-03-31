import socket
import struct

from .TorrentStates import TorrentStates
from .TorrentWriter import TorrentWriter
from .config import CONFIG


class Peer:
    def __init__(self, ip, port, torrent):
        self.ip = ip
        self.port = port
        self.torrent = torrent
        self.sock = socket.socket()
        self.processed_block = None
        self.is_available = True
        self.peer_choking = True
        self.peer_interested = False
        self.im_choking = True
        self.im_interested = False
        self.buffer = b''
        self.available_pieces_map = None
        self.is_running = False

        self._init_connection()

    def _init_connection(self):
        try:
            self.sock.settimeout(CONFIG['timeout_for_peer'])
            self.sock.connect((self.ip, self.port))
            self._send_handshake(self.torrent.metainfo.info_hash)
            self._handle_handshake()
            self._send_msg(msg_id=2)  # interested
            self._check_buffer()
        except Exception:
            self.is_available = False
            self.sock.close()

    def _close(self, peer_is_bad=False):
        if self.processed_block is not None:
            self.torrent.handle_incorrect_pbi(*self.processed_block)
        self.torrent.handle_peer_disconnect(self, peer_is_bad=peer_is_bad)
        self.is_available = False
        self.is_running = False
        self.sock.close()

    @property
    def name(self):
        return '{}:{}'.format(self.ip, self.port)
    
    @property
    def buffer_length(self):
        return len(self.buffer)

    def run_download(self):
        self.is_running = True
        while (self.is_available and
               self.torrent.state == TorrentStates.STARTED):
            piece_idx, block_idx = self.torrent.get_pbi_for_peer(self)
            if piece_idx is None:
                self._close()
                break
            if block_idx is None:
                continue
            try:
                self.request_block(piece_idx, block_idx)
            except Exception:
                peer_is_bad = False
                if self.available_pieces_map is None:
                    peer_is_bad = True
                self._close(peer_is_bad)

    def request_block(self, piece_idx, block_idx):
        self.processed_block = (piece_idx, block_idx)
        if self.peer_choking:
            self._send_msg(msg_id=2)  # interested
            self._check_buffer()
            if self.peer_choking:
                self._close()
                return
        piece_len = self.torrent.metainfo.get_piece_len_at(piece_idx)
        offset = block_idx * CONFIG['int_block_len']
        block_len = min(piece_len - offset, CONFIG['int_block_len'])
        self._send_msg(msg_id=6,
                       piece_idx=piece_idx, block_len=block_len, offset=offset)
        self._check_buffer()
        if self.processed_block is not None:
            self.torrent.handle_incorrect_pbi(*self.processed_block)
            self.processed_block = None

    def have_piece(self, piece_idx):
        if self.available_pieces_map is not None:
            return self.available_pieces_map[piece_idx]
        return True

    def _send_msg(self, msg_id, **kwargs):
        if msg_id == 0:  # choke
            self.im_choking = True
        elif msg_id == 1:  # unchoke
            self.im_choking = False
        elif msg_id == 2:  # interested
            self.im_interested = True
        elif msg_id == 3:  # not_interested
            self.im_interested = False
        msg = self.build_msg(msg_id, **kwargs)
        self.sock.send(msg)

    def _handle_handshake(self):
        # msg format: <pstrlen><pstr><reserved><info_hash><peer_id>
        self._upd_buffer()
        pstrlen = self.buffer[0]
        while self.buffer_length < 49 + pstrlen:
            self._upd_buffer()
        handshake_data = self.buffer[1: 49 + pstrlen]
        pstr = handshake_data[: pstrlen]
        if pstr != CONFIG['protocol_name']:
            # TODO: check, that can decode pstr
            raise UnexpectedProtocolType(pstr.decode())
        self.buffer = self.buffer[49 + pstrlen:]

    def _check_buffer(self):
        self._upd_buffer()
        self._handle_buffer()
        if self.buffer_length != 0:
            self._check_buffer()

    def _handle_buffer(self):
        while self.buffer_length:
            if self.buffer_length < 4:
                return
            prefix_len = struct.unpack('!L', self.buffer[:4])[0]
            offset = 4
            if prefix_len + offset > self.buffer_length:
                return

            if prefix_len == 0:
                pass  # keep-alive msg
            else:
                self._decode_msg(self.buffer[offset: offset + prefix_len])
                offset += prefix_len
            self.buffer = self.buffer[offset:]

    def _decode_msg(self, msg):
        msg_id = msg[0]

        if msg_id == 0:  # choke
            self.peer_choking = True
        elif msg_id == 1:  # unchoke
            self.peer_choking = False
        elif msg_id == 2:  # interested
            self.peer_interested = True
        elif msg_id == 3:  # not_interested
            self.peer_interested = False
        elif msg_id == 4:  # have
            idx = struct.unpack('!L', msg[1:5])[0]
            if self.available_pieces_map is not None:
                self.available_pieces_map[idx] = True
        elif msg_id == 5:  # bitfield
            cur_map = TorrentWriter.get_info_about_pieced_from_bytes(msg[1:])
            pieces_count = len(self.torrent.metainfo.pieces)
            self.available_pieces_map = cur_map[:pieces_count]
        elif msg_id == 6:  # request
            pass
        elif msg_id == 7:  # piece
            piece_idx = struct.unpack('!L', msg[1:5])[0]
            offset = struct.unpack('!L', msg[5:9])[0]
            block = msg[9:]
            self.torrent.handle_block(
                piece_idx, offset // CONFIG['int_block_len'], block)
            self.processed_block = None
        elif msg_id == 8:  # cancel
            pass
        elif msg_id == 9:  # port
            pass
        else:
            raise UnexpectedMessageType('msg_id = {}'.format(msg_id))

    def get_new_data_from_socket(self):
        return self.sock.recv(CONFIG['max_ans_size'])

    def _upd_buffer(self):
        new_data = self.get_new_data_from_socket()
        if not new_data:
            raise Exception('received empty data')
        self.buffer += new_data

    def _send_handshake(self, info_hash):
        self.sock.send(self.build_handshake(info_hash))

    @staticmethod
    def build_handshake(info_hash):
        return (b'\x13' +
                CONFIG['protocol_name'] +
                b'\x00\x00\x00\x00\x00\x00\x00\x00' +
                info_hash +
                CONFIG['peer_id'])

    @staticmethod
    def build_msg(msg_id, **kwargs):
        if msg_id in {0, 1, 2, 3}:  #
            msg_len = b'\x00\x00\x00\x01'
            payload = b''
        elif msg_id == 4:  # have
            msg_len = b'\x00\x00\x00\x05'
            payload = struct.pack('!L', kwargs['piece_idx'])
        elif msg_id == 6:  # request
            msg_len = b'\x00\x00\x00\x0d'
            payload = (struct.pack('!L', kwargs['piece_idx']) +
                       struct.pack('!L', kwargs['offset']) +
                       struct.pack('!L', kwargs['block_len']))
        elif msg_id in {5, 7, 8, 9}:  # bitfield, piece, cancel, port
            raise NotImplementedError()
        elif msg_id == -1:  # keep-alive msg
            return b'\x00\x00\x00\x00'
        else:
            raise UnexpectedMessageType()

        msg_id_in_bytes = struct.pack('!B', msg_id)
        return msg_len + msg_id_in_bytes + payload


class UnexpectedMessageType(Exception):
    pass


class UnexpectedProtocolType(Exception):
    pass
