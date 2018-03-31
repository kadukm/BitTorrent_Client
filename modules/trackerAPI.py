import re
import socket
import struct
import requests

from .BencodeParser import BencodeParser
from .config import CONFIG


UDP_REGEX = re.compile(r'udp://[(\[]?(.+?)[)\]]?:([\d]{1,5})(?![\d:])')


def get_peers_list_by_torrent_metainfo(metainfo):
    # TODO: use Threads for connections to trackers
    for announce in metainfo.announce_list:
        try:
            get_method = (_get_peers_by_http if announce[0] == 'h'
                          else _get_peers_by_udp)
            return get_method(announce, metainfo)
        except Exception:
            continue
    raise PeersFindingError('cant find peers')


def _parse_announce_url(announce):
    matched_link = re.search(UDP_REGEX, announce)
    host = matched_link.group(1)
    str_port = matched_link.group(2)
    port = 80 if str_port == '' else int(str_port)
    return host, port


def _get_peers_by_http(announce, metainfo):
    response = requests.get(announce, _get_url_args4http(metainfo),
                            timeout=CONFIG['timeout'])
    peers = _get_peers_dict(response.content)
    if isinstance(peers[b'peers'], bytes):
        peers = _get_peers_by_bin_data(peers[b'peers'])
    else:
        peers = _get_peers_by_peers_list(peers[b'peers'])
    return peers


def _get_url_args4http(metainfo):
    request = {'info_hash': metainfo.info_hash,
               'peer_id': CONFIG['peer_id'], 'port': CONFIG['port'],
               'uploaded': '0', 'downloaded': '0', 'left': metainfo.length,
               'compact': '1', 'no_peer_id': '1', 'numwant': CONFIG['numwant']}
    return request


def _get_peers_by_udp(announce, metainfo):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(CONFIG['timeout'])
        host, port = _parse_announce_url(announce)
        s.connect((host, port))
        transaction_id = b'\x00\x00\x00\xff'
        cur_msg = b''.join((b'\x00\x00\x04\x17\x27\x10\x19\x80',
                            b'\x00\x00\x00\x00',
                            transaction_id))
        s.send(cur_msg)
        ans = s.recv(16)  # response's length equals 16 bytes
        # TODO: check action
        # TODO: check transaction_id
        cur_msg = _get_udp_request(ans[8:16], transaction_id, metainfo)
        s.send(cur_msg)
        ans = s.recv(CONFIG['max_ans_size'])
        return _get_peers_by_bin_data(ans[20:])


def _get_udp_request(connection_id, transaction_id, metainfo):
    # with ..., ACTION, ..., PEER_ID and DOWNLOADED fields
    msg_list = [connection_id, b'\x00\x00\x00\x01', transaction_id,
                metainfo.info_hash, b'-MY2282-123456789000',
                b'\x00\x00\x00\x00\x00\x00\x00\x00']

    hex_metainfo_len = hex(metainfo.length)[2:]
    full_hex_metainfo_len = ('0'*(16 - len(hex_metainfo_len)) +
                                  hex_metainfo_len)
    msg_list.append(bytes.fromhex(full_hex_metainfo_len))  # LEFT

    msg_list.append(b'\x00\x00\x00\x00\x00\x00\x00\x00')  # UPLOADED
    msg_list.append(b'\x00\x00\x00\x00')  # EVENT (none)
    msg_list.append(b'\x00\x00\x00\x00')  # IP
    msg_list.append(b'\x00\x00\x00\x00')  # KEY
    msg_list.append(struct.pack('!L', CONFIG['numwant']))
    msg_list.append(b'\x00\x00\x1a\xe1')  # PORT
    return b''.join(msg_list)


def _get_peers_dict(data):
    bp = BencodeParser()
    return bp.parse_data(data)


def _get_peers_by_peers_list(peers_list):
    res_peers = []
    for peers_dict in peers_list:
        res_peers.append((peers_dict[b'ip'].decode(), peers_dict[b'port']))
    return res_peers


def _get_peers_by_bin_data(data):
    res = []
    cur_idx = 0
    next_idx = 6
    while cur_idx < len(data):
        del_idx = cur_idx + 4
        ip = _get_ip(data[cur_idx: del_idx])
        port = _parse_bytes_to_int(data[del_idx: next_idx])
        res.append((ip, port))
        cur_idx = next_idx
        next_idx += 6
    return res


def _get_ip(bin_ip):
    res = []
    for i in range(4):
        res.append(str(bin_ip[i]))
    return '.'.join(res)


def _parse_bytes_to_int(cur_bytes):
    return struct.unpack('!H', cur_bytes)[0]


class PeersFindingError(Exception):
    pass
