#!/usr/bin/env python2
import shutil
import ConfigParser
import logging
import os
import sys
from os import path as path
from posix import environ
from sys import path as pythonpath
from os import getpid
# tribler path
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))

# os.chdir(os.path.abspath('./tribler'))
sys.path.append('.')

from gumby.experiments.TriblerDispersyClient import TriblerDispersyExperimentScriptClient,\
    BASE_DIR
from gumby.experiments.dispersyclient import main

from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
from Tribler.Core.TorrentDef import TorrentDef
from Tribler.Policies.BoostingPolicy import SeederRatioPolicy, RandomPolicy, CreationDatePolicy
from Tribler.Policies.BoostingManager import BoostingManager, BoostingSettings
from Tribler.Policies.credit_mining_util import string_to_source

class CMining(TriblerDispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        super(CMining, self).__init__(*argv, **kwargs)
        from Tribler.community.allchannel.community import AllChannelCommunity
        self.community_class = AllChannelCommunity
        self.boosting_manager = None
        self.utility = None
        self.bsettings = None

    def registerCallbacks(self):
        super(CMining, self).registerCallbacks()
        self.scenario_runner.register(self.start_boosting, 'start_boosting')
        self.scenario_runner.register(self.add_source, 'add_source')
        self.scenario_runner.register(self.create_test_torrent, 'create_test_torrent')
        self.scenario_runner.register(self.start_download, 'start_download')
        self.scenario_runner.register(self.stop_download, 'stop_download')
        self.scenario_runner.register(self.set_boost_settings, 'set_boost_settings')
        self.scenario_runner.register(self.setup_seeder, 'setup_seeder')

    def start_dispersy(self):
        super(CMining, self).start_dispersy()
        from Tribler.community.allchannel.community import AllChannelCommunity

        self._dispersy.define_auto_load(AllChannelCommunity, self.session.dispersy_member, load=True,
                                                   kargs={'tribler_session': self.session})

    def create_test_torrent(self, filename='', size=0, with_file=False):
        logging.error("Create %s torrent with file %s" % (filename, with_file))
        filepath = path.join(self.session.get_state_dir(), "..", str(self.scenario_file) + str(filename))
        logging.error("Creating torrent..")

        tdef = TorrentDef()
        if with_file:
            with open(filepath, 'wb') as fp:
                fp.write("0" * int(size))

        tdef.add_content(filepath)

        # doesn't matter for now
        tdef.set_tracker("http://127.0.0.1:9197/announce")
        tdef.finalize()
        tdef_file = path.join(self.session.get_state_dir(), "..", "%s.torrent" % filename)
        tdef.save(tdef_file)

    def set_boost_settings(self, filename=None):

        self.bsettings = BoostingSettings(self.session)

        # parameter for experiment
        self.bsettings.credit_mining_path = os.path.join(self.session.get_state_dir(), "credit_mining")
        self.bsettings.load_config = False
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
            "seederratio": SeederRatioPolicy
        }

        self.bsettings.policy = switch_policy[config.get(section, "policy")](self.session)

        logging.debug("Read boosting settings %s", filename)

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

    def add_source(self, strsource):
        assert strsource, "Must not empty"

        self.boosting_manager.add_source(string_to_source(strsource))

    def start_download(self, name):
        defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
        dscfg = defaultDLConfig.copy()
        dscfg.set_dest_dir(path.join(self.session.get_state_dir(), "download"))

        tdef = TorrentDef.load(path.join(self.session.get_state_dir(), "..", "%s.torrent" % name))

        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['allow_multiple_connections_per_ip'] = True
        settings['ignore_limits_on_local_network'] = False
        settings['download_rate_limit'] = 500000
        settings["upload_rate_limit"] = 5000000
        self.session.lm.ltmgr.get_session().set_settings(settings)

        logging.error("Start downloading %s..", name)
        def cb(ds):
            from Tribler.Core.simpledefs import dlstatus_strings
            logging.error('Download infohash=%s, down=%d kB/s, up=%d kB/s, progress=%s, status=%s, peers=%s' %
                          (tdef.get_infohash().encode('hex'),
                           ds.get_current_speed('down')/1000,
                           ds.get_current_speed('up')/1000,
                           ds.get_progress(),
                           dlstatus_strings[ds.get_status()],
                           sum(ds.get_num_seeds_peers())))

            # if sum(ds.get_num_seeds_peers()) != 0:
            #     libdl = ds.download
            #     for i in libdl.handle.get_peer_info():
            #         logging.error("%s:%s source:%s", i.ip[0], i.ip[1], i.source)

            #vwhen, getpeerlist
            return 1.0, False

        download_impl = self.session.start_download_from_tdef(tdef, dscfg)
        download_impl.set_state_callback(cb, delay=1)

        ihash = tdef.get_infohash()
        self.session.lm.torrent_checker.add_gui_request(ihash, True)

    def stop_download(self, name):
        tdef = TorrentDef.load(path.join(self.session.get_state_dir(), "..", "%s.torrent" % name))
        logging.error("Stopping Download")
        self.session.remove_download_by_id(tdef.get_infohash(), True, True)

    def setup_session_config(self):
        config = super(CMining, self).setup_session_config()
        config.set_state_dir(os.path.abspath(os.path.join(environ.get('OUTPUT_DIR', None) or BASE_DIR, "Tribler-%d") % getpid()))
        config.set_megacache(True)
        config.set_dht_torrent_collecting(True)
        config.set_torrent_collecting(True)
        config.set_torrent_checking(True)
        config.set_enable_torrent_search(True)
        config.set_enable_channel_search(True)
        config.set_enable_multichain(False)
        config.set_tunnel_community_enabled(False)

        logging.debug("Do session config locally")
        return config

    def setup_seeder(self, filename):
        self.annotate('start seeding %s' % filename)
        logging.error("Start seeding %s", filename)

        filepath = path.join(self.session.get_state_dir(), "..", str(self.scenario_file) + str(filename))
        shutil.copyfile(filepath, path.join(self.session.get_state_dir(), str(self.scenario_file) + str(filename)))

        defaultDLConfig = DefaultDownloadStartupConfig.getInstance()
        dscfg = defaultDLConfig.copy()
        dscfg.set_dest_dir(self.session.get_state_dir())

        tdef = TorrentDef.load(path.join(self.session.get_state_dir(), "..", "%s.torrent" % filename))

        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['allow_multiple_connections_per_ip'] = True
        settings['ignore_limits_on_local_network'] = False
        settings["upload_rate_limit"] = 300000

        # settings["local_upload_rate_limit"] = 1000
        # settings["ignore_limits_on_local_network"] = False

        self.session.lm.ltmgr.get_session().set_settings(settings)

        def cb(ds):
            from Tribler.Core.simpledefs import dlstatus_strings
            logging.error('Seed infohash=%s, down=%d, up=%d, progress=%s, status=%s, peers=%s ul_lim=%s' %
                          (tdef.get_infohash().encode('hex')[:5],
                           ds.get_current_speed('down')/1000,
                           ds.get_current_speed('up')/1000,
                           ds.get_progress(),
                           dlstatus_strings[ds.get_status()],
                           sum(ds.get_num_seeds_peers()), ds.download.handle.upload_limit()))

            if sum(ds.get_num_seeds_peers()) != 0:
                libdl = ds.download
                for i in libdl.handle.get_peer_info():
                    logging.error("%s:%s source:%s", i.ip[0], i.ip[1], i.source)

            return 1.0, False

        download = self.session.start_download_from_tdef(tdef, dscfg)
        download.set_state_callback(cb, delay=1)

if __name__ == '__main__':
    CMining.scenario_file = environ.get('SCENARIO_FILE', 'creditmining_base.scenario')
    main(CMining)
