#!/usr/bin/env python2
import shutil

import libtorrent as lt
import ConfigParser
import logging
import os
import sys
from binascii import hexlify, unhexlify
from os import path as path
from posix import environ
from sys import path as pythonpath
from twisted.internet import reactor
# tribler path
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

# os.chdir(os.path.abspath('./tribler'))
sys.path.append('.')

from experiments.tribler.channel_download import ChannelDownloadClient
from gumby.experiments.dispersyclient import main
from gumby.experiments.TriblerDispersyClient import TriblerDispersyExperimentScriptClient

from Tribler.Core.TorrentDef import TorrentDef
from Tribler.Policies.BoostingPolicy import SeederRatioPolicy, RandomPolicy, CreationDatePolicy, ScoringPolicy, \
    BoostingPolicy
from Tribler.Policies.BoostingManager import BoostingManager, BoostingSettings
from Tribler.Policies.credit_mining_util import string_to_source
from Tribler.Core.simpledefs import NTFY_TORRENTS, NTFY_INSERT, NTFY_UPDATE, NTFY_MAGNET_STARTED

class CreditMiningClient(ChannelDownloadClient):

    def __init__(self, *argv, **kwargs):
        super(CreditMiningClient, self).__init__(*argv, **kwargs)

        self._logger.setLevel(logging.DEBUG)
        self.boosting_manager = None
        self.bsettings = None

        self.chn_join_lc = None
        self.loaded_torrent = {}
        self.connect_lc = None

    def registerCallbacks(self):
        super(CreditMiningClient, self).registerCallbacks()
        self.scenario_runner.register(self.start_boosting, 'start_boosting')
        self.scenario_runner.register(self.add_source, 'add_source')
        self.scenario_runner.register(self.set_boost_settings, 'set_boost_settings')

    def set_boost_settings(self, filename=None):

        self.bsettings = BoostingSettings(self.session)

        # parameter for experiment
        self.bsettings.credit_mining_path = os.path.join(self.session.get_state_dir(), "credit_mining")
        self.bsettings.load_config = False
        self.bsettings.check_dependencies = False
        self.bsettings.min_connection_start = -1
        self.bsettings.min_channels_start = -1

        if filename is None:
            return

        config = ConfigParser.RawConfigParser()
        config.read(path.join(environ['EXPERIMENT_DIR'], filename))

        section = "Tribler.Policies.BoostingManager"
        self.bsettings.max_torrents_per_source = config.getint(section, "max_torrents_per_source")
        self.bsettings.max_torrents_active = config.getint(section, "max_torrents_active")
        self.bsettings.source_interval = config.getint(section, "source_interval")
        self.bsettings.swarm_interval = config.getint(section, "swarm_interval")
        self.bsettings.share_mode_target = config.getint(section, "share_mode_target")
        self.bsettings.tracker_interval = config.getint(section, "tracker_interval")
        self.bsettings.logging_interval = config.getint(section, "logging_interval")

        switch_policy = {
            "random": RandomPolicy,
            "creation": CreationDatePolicy,
            "seederratio": SeederRatioPolicy,
            "scoring": ScoringPolicy,
            "all": PickAllPolicy
        }

        self.bsettings.policy = switch_policy[config.get(section, "policy")](self.session)

        self._logger.debug("Read boosting settings %s", filename)

    def start_boosting(self):
        if self.bsettings is None:
            self.set_boost_settings()

            self.bsettings.max_torrents_active = 8
            self.bsettings.max_torrents_per_source = 5
            self.bsettings.tracker_interval = 5
            self.bsettings.initial_tracker_interval = 5
            self.bsettings.logging_interval = 30
            self.bsettings.initial_logging_interval = 3

        self.boosting_manager = BoostingManager(self.session, self.bsettings)
        self.session.lm.boosting_manager = self.boosting_manager

        settings = self.boosting_manager.pre_session.get_settings()
        settings['allow_multiple_connections_per_ip'] = True
        settings['ignore_limits_on_local_network'] = False
        settings['user_agent'] = "Minerspre/%s" % self.my_id
        self.boosting_manager.pre_session.set_settings(settings)

        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['user_agent'] = "Miners/%s" % self.my_id
        settings["max_rejects"] = 50
        settings["allowed_fast_set_size"] = 500
        settings["inactivity_timeout"] = 1200
        self.session.lm.ltmgr.get_session().set_settings(settings)

        self.set_speed(250000, 100000)

        def receive_infohash(dummy_subject, dummy_change_type, dummy_infohash):
            self.session.notifier.notify(NTFY_TORRENTS, NTFY_INSERT, dummy_infohash)

        self.session.add_observer(receive_infohash, NTFY_TORRENTS, [NTFY_MAGNET_STARTED])

        self._logger.debug("Run Boosting %s", self.boosting_manager)

    def _load_torrent(self, torrent, callback):
        # torrent is ChannelTorrent
        def _success_download(ihash_str):
            if ihash_str in self.loaded_torrent.keys():
                return

            self.loaded_torrent[ihash_str] = True

            tdef = TorrentDef.load_from_memory(self.session.get_collected_torrent(unhexlify(ihash_str)))

            self.session.lm.torrent_db.addOrGetTorrentID(unhexlify(ihash_str))
            self.session.lm.torrent_db.addExternalTorrent(tdef)

            from Tribler.Main.Utility.GuiDBTuples import Torrent
            t = Torrent.fromTorrentDef(tdef)
            t.torrent_db = self.session.lm.torrent_db
            t.channelcast_db = self.session.lm.channelcast_db

            if t.torrent_id <= 0:
                del t.torrent_id

            from Tribler.Main.Utility.GuiDBTuples import CollectedTorrent
            ctorrent = CollectedTorrent(t, tdef)
            self.loaded_torrent[ihash_str] = ctorrent

            callback(ctorrent)

            self.session.notifier.notify(NTFY_TORRENTS, NTFY_INSERT, unhexlify(ihash_str))

            thandle = self.boosting_manager.pre_session.find_torrent(lt.big_number(unhexlify(ihash_str)))
            self._connect_peer(thandle)

        for candidate in list(self.joined_community.dispersy_yield_candidates()):
            self.session.lm.rtorrent_handler.download_torrent(
                    candidate, torrent.infohash, _success_download, priority=1)

            self.session.lm.rtorrent_handler.download_torrent(
                None, torrent.infohash, _success_download, priority=1)

    def start_download(self, name):
        if self.boosting_manager is None:
            super(CreditMiningClient, self).start_download(name)
            return

        ln = [(i, t) for i, t in self.boosting_manager.torrents.items() if name in t['name']]
        if ln:
            ihash_bin = ln[0][0]

            _torrent = self.boosting_manager.torrents[ihash_bin]
            _download = _torrent.get('download', None)
            if _download:
                handle = _download.handle
                if handle:
                    handle.pause()

                download_dir = path.join(self.session.get_state_dir(), "download")

                if not path.exists(download_dir):
                    try:
                        os.makedirs(download_dir)
                    except OSError:
                        # race condition of creating shared directory may happen
                        pass

                shutil.copy(path.join(self.bsettings.credit_mining_path, "%s" % ln[0][1]['name']), download_dir)

                self.boosting_manager.stop_download(ihash_bin, True, "Starting new download")

                def _check_done(_name, _ihash_bin):
                    if _ihash_bin not in self.boosting_manager.torrents.keys():
                        # already removed
                        super(CreditMiningClient, self).start_download(_name)
                    else:
                        reactor.callLater(5.0, _check_done, _name, _ihash_bin)

                # periodically check if it already removed properly
                reactor.callLater(10.0, _check_done, name, ihash_bin)
                return

        super(CreditMiningClient, self).start_download(name)

    def add_source(self, strsource):
        assert strsource, "Must not empty"

        if strsource == 'joinedchannel':
            if self.joined_community:
                channel_hash = self.joined_community.cid.encode("HEX")
                self._logger.debug("Add Channel: %s ", self.joined_community.master_member.mid.encode("HEX"))
                self.boosting_manager.add_source(string_to_source(channel_hash))

                ch = self.boosting_manager.get_source_object(self.joined_community.cid)
                ch.torrent_mgr.load_torrent = self._load_torrent
                from twisted.internet.task import LoopingCall
                self.connect_lc = LoopingCall(self._connect_cm)
                self.connect_lc.start(10.0, now=False)
            else:
                reactor.callLater(10.0, self.add_source, strsource)
        else:
            self.boosting_manager.add_source(string_to_source(strsource))

    def _connect_cm(self):
        if not self.boosting_manager:
            return

        for ihash, torrent in self.boosting_manager.torrents.items():
            if 'download' in torrent and torrent['download'].handle:
                self._connect_peer(torrent['download'].handle)


    def setup_session_config(self):
        config = super(CreditMiningClient, self).setup_session_config()
        config.set_videoplayer(False)
        config.set_torrent_checking(True)
        # config.set_enable_torrent_search(True)
        config.set_enable_channel_search(True)

        self._logger.debug("Do session config locally")
        return config

    def stop(self, retry=3):
        if self.boosting_manager:
            if self.connect_lc:
                self.connect_lc.stop()
            for name in self.dl_lc.keys():
                if not self.downloaded_torrent[name]:
                    self.dl_lc[name].stop()
                    self._logger.error("Can't make it to download %s", name)

            # make sure delete downloaded credit mining stuff
            shutil.rmtree(self.bsettings.credit_mining_path, ignore_errors=True)

            self.boosting_manager.shutdown()
    
            if self.dl_lc.keys():
                super(CreditMiningClient, self).stop()
        else:
            super(CreditMiningClient, self).stop()


class PickAllPolicy(BoostingPolicy):
    def apply(self, torrents, max_active, force=False):
        self._logger.error("Return all Torrents")
        return list(torrents.itervalues()), []

if __name__ == '__main__':
    CreditMiningClient.scenario_file = environ.get('SCENARIO_FILE', 'creditmining_base.scenario')
    main(CreditMiningClient)
