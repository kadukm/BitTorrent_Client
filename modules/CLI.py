import time
import os
from threading import Lock
from threading import Thread

from .Torrent import Torrent
from .TorrentMetainfo import TorrentMetainfo


class CLI:
    max_name_len = 28

    def __init__(self):
        self.is_available = True
        self.print_lock = Lock()
        self.torrents_dir = os.path.join(os.getcwd(), 'torrents')
        self.torrents_names = []
        self._init_torrents_names()
        self.torrents = []
        self._init_torrents()

    @staticmethod
    def cls():
        os.system('cls' if os.name == 'nt' else 'clear')

    def run(self):
        Thread(target=self.print_torrents_table_always,
               args=(), daemon=True).start()
        while True:
            input()
            with self.print_lock:
                cmd = input('Input your command ("TorrentNumber action"): ')
                if cmd:
                    if cmd.lower()[0] == 'q':
                        return  # quit
                    try:
                        torr_idx, action = cmd.split()
                        torr_idx = int(torr_idx)
                        torrent = self.torrents[torr_idx]
                        if action.lower()[0] == 'd':
                            Thread(target=torrent.run_download,
                                   args=(), daemon=True).start()
                        elif action.lower()[0] == 'p':
                            Thread(target=torrent.pause_download,
                                   args=(), daemon=True).start()
                        else:
                            raise ValueError('Incorrect command')
                    except (ValueError, IndexError):
                        print('Incorrect command! Press Enter to continue')
                        input()

    def print_torrents_table_always(self):
        while True:
            time.sleep(1.5)
            with self.print_lock:
                self.cls()
                print(self.get_torrents_table())

    def get_torrents_table(self):
        res = ['TN | Name                         | State       | '
               'Progress | Peers | Speed', '']
        for torr_idx in range(len(self.torrents_names)):
            cur_res = ['{:<2}'.format(torr_idx)]

            full_torr_name = self.torrents_names[torr_idx]
            short_torr_name = full_torr_name[:self.max_name_len]
            cur_res.append('{:<{max_len}}'.format(short_torr_name,
                                                  max_len=self.max_name_len))
            torrent = self.torrents[torr_idx]
            cur_torr_state = torrent.state
            cur_progress = '{:.2%}'.format(torrent.progress)
            cur_peers_count = len(torrent.peers)
            cur_speed = torrent.download_speed
            cur_res.append('{:<11}'.format(cur_torr_state.name))
            cur_res.append('{:<8}'.format(cur_progress))
            cur_res.append('{:<5}'.format(cur_peers_count))
            cur_res.append('{:<11}'.format(cur_speed))
            res.append(' | '.join(cur_res))
        res.append('\nPress ENTER to begin to input commands')
        return '\n'.join(res)

    def _init_torrents(self):
        for torr_idx in range(len(self.torrents_names)):
            full_path = os.path.join(self.torrents_dir,
                                     self.torrents_names[torr_idx])
            metainfo = TorrentMetainfo(full_path)
            self.torrents.append(Torrent(metainfo))

    def _init_torrents_names(self):
        for filename in os.listdir(self.torrents_dir):
            self.torrents_names.append(filename)
