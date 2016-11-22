#!/usr/bin/env python2
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

    def registerCallbacks(self):
        super(CreditMiningClient, self).registerCallbacks()
        self.scenario_runner.register(self.start_boosting, 'start_boosting')
        self.scenario_runner.register(self.add_source, 'add_source')
        self.scenario_runner.register(self.set_boost_settings, 'set_boost_settings')
        self.scenario_runner.register(self.set_speed, 'set_speed')

    def set_speed(self, download, upload):
        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['download_rate_limit'] = int(download)
        settings["upload_rate_limit"] = int(upload)
        self.session.lm.ltmgr.get_session().set_settings(settings)

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
        self.session.lm.ltmgr.get_session().set_settings(settings)

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

    def add_source(self, strsource):
        assert strsource, "Must not empty"

        if strsource == 'joinedchannel':
            if self.joined_community:
                channel_hash = self.joined_community.cid.encode("HEX")
                self._logger.debug("Add Channel: %s ", self.joined_community.master_member.mid.encode("HEX"))
                self.boosting_manager.add_source(string_to_source(channel_hash))

                ch = self.boosting_manager.get_source_object(self.joined_community.cid)
                ch.torrent_mgr.load_torrent = self._load_torrent
            else:
                reactor.callLater(10.0, self.add_source, strsource)
        else:
            self.boosting_manager.add_source(string_to_source(strsource))

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
            for name in self.dl_lc.keys():
                if not self.downloaded_torrent[name]:
                    self.dl_lc[name].stop()
                    self._logger.error("Can't make it to download %s", name)
    
            TriblerDispersyExperimentScriptClient.stop(self, retry)
        else:
            super(CreditMiningClient, self).stop()


class PickAllPolicy(BoostingPolicy):
    def apply(self, torrents, max_active, force=False):
        self._logger.error("Return all Torrents")
        return list(torrents.itervalues()), []

if __name__ == '__main__':
    CreditMiningClient.scenario_file = environ.get('SCENARIO_FILE', 'creditmining_base.scenario')
    main(CreditMiningClient)
