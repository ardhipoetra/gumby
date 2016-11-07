#!/usr/bin/env python2
import logging
import os
from binascii import hexlify
from os import path as path
from sys import path as pythonpath
from time import time

import posix

from twisted.internet.task import LoopingCall

from gumby.experiments.TriblerDispersyClient import TriblerDispersyExperimentScriptClient, BASE_DIR
from gumby.experiments.dispersyclient import main, DispersyExperimentScriptClient

# TODO(emilon): Fix this crap
pythonpath.append(path.abspath(path.join(path.dirname(__file__), '..', '..', '..', "./tribler")))
pythonpath.append('.')

from Tribler.Core.DownloadConfig import DefaultDownloadStartupConfig
from Tribler.Core.TorrentDef import TorrentDef
from Tribler.community.channel.community import ChannelCommunity
from Tribler.community.channel.preview import PreviewChannelCommunity
from Tribler.Policies.credit_mining_util import TorrentManagerCM

class ChannelDownloadClient(TriblerDispersyExperimentScriptClient):

    def __init__(self, *argv, **kwargs):
        super(ChannelDownloadClient, self).__init__(*argv, **kwargs)
        from Tribler.community.allchannel.community import AllChannelCommunity
        self.community_class = AllChannelCommunity

        self._logger.setLevel(logging.DEBUG)

        self.my_channel = None
        self.joined_community = None

        self.join_lc = None
        self.dl_lc = None

        self.upload_dir_path = None

        self.torrent_mgr = None

    def start_session(self):
        super(ChannelDownloadClient, self).start_session()
        self.session_deferred.addCallback(self.__config_dispersy)

    def __config_dispersy(self, session):
        self.session.lm.dispersy = self._dispersy
        self.session.lm.init()
        self.session.get_dispersy = True

        self._dispersy.define_auto_load(ChannelCommunity, self._my_member, (), {"tribler_session": self.session})
        self._dispersy.define_auto_load(PreviewChannelCommunity, self._my_member, (), {"tribler_session": self.session})

        self._logger.error("Dispersy configured")

    def start_dispersy(self):
        DispersyExperimentScriptClient.start_dispersy(self)

    def setup_session_config(self):
        config = super(ChannelDownloadClient, self).setup_session_config()
        config.set_state_dir(os.path.abspath(os.path.join(posix.environ.get('OUTPUT_DIR', None) or BASE_DIR, "Tribler-%d") % os.getpid()))
        config.set_megacache(True)
        config.set_dht_torrent_collecting(True)
        config.set_torrent_collecting(False)
        config.set_torrent_store(True)
        config.set_enable_multichain(False)
        config.set_tunnel_community_enabled(False)
        config.set_channel_community_enabled(False)
        config.set_preview_channel_community_enabled(False)

        config.set_dispersy(False)

        self.upload_dir_path = path.join(config.get_state_dir(), "..", "upload_dir")
        if not os.path.exists(self.upload_dir_path):
            try:
                os.makedirs(self.upload_dir_path)
            except OSError:
                # race condition of creating shared directory may happen
                pass

        logging.debug("Do session config locally")
        return config

    def online(self, dont_empty=False):
        self.set_community_kwarg("tribler_session", self.session)
        self.set_community_kwarg("auto_join_channel", True)

        super(ChannelDownloadClient, self).online()

        settings = self.session.lm.ltmgr.get_session().get_settings()
        settings['allow_multiple_connections_per_ip'] = True
        settings['ignore_limits_on_local_network'] = False
        settings['download_rate_limit'] = 500000
        settings["upload_rate_limit"] = 300000
        self.session.lm.ltmgr.get_session().set_settings(settings)

        self.torrent_mgr = TorrentManagerCM(self.session)

    def registerCallbacks(self):
        super(ChannelDownloadClient, self).registerCallbacks()

        self.scenario_runner.register(self.create, 'create')
        self.scenario_runner.register(self.join, 'join')
        self.scenario_runner.register(self.publish, 'publish')
        self.scenario_runner.register(self.start_download, 'start_download')

    def create(self):
        self._logger.error("creating-community")
        self.my_channel = ChannelCommunity.create_community(self._dispersy, self._my_member, tribler_session=self.session)
        self.my_channel.set_channel_mode(ChannelCommunity.CHANNEL_OPEN)
        self.my_channel._disp_create_channel(u'channel-name', u'channel-desc')

        self._logger.error("Community %s (%s) created with member: %s",
                           self.my_channel.get_channel_name(), self.my_channel.get_channel_id(), self.my_channel._master_member)

    def join(self):
        if not self.join_lc:
            self.join_lc = lc = LoopingCall(self.join)
            lc.start(1.0, now=False)

        self._logger.error("trying-to-join-community on %s", self._community)

        channels = self._community._channelcast_db.getAllChannels()

        if channels:
            cid = channels[0][1]
            community = self._community._get_channel_community(cid)
            if community._channel_id:

                self._community.disp_create_votecast(community.cid, 2, int(time.time()))

                self._logger.error("joining-community")
                for c in self._dispersy.get_communities():
                    if isinstance(c, ChannelCommunity):
                        self.joined_community = c
                if self.joined_community is None:
                    self._logger.error("couldn't join community")
                self._logger.error("Joined community with member: %s", self.joined_community._master_member)
                self.join_lc.stop()
                return

    def publish(self, filename, size):
        if self.my_channel or self.joined_community:
            tdef = self._create_test_torrent(filename, size)
            if self.my_channel:
                self.my_channel._disp_create_torrent_from_torrentdef(tdef, int(time()))
            elif self.joined_community:
                self.joined_community._disp_create_torrent_from_torrentdef(tdef, int(time()))

            dscfg = DefaultDownloadStartupConfig.getInstance().copy()
            dscfg.set_dest_dir(self.upload_dir_path)

            def seeder_callback(ds):
                from Tribler.Core.simpledefs import dlstatus_strings
                self._logger.error('Seed infohash=%s, down=%d, up=%d, progress=%s, status=%s, peers=%s ul_lim=%s' %
                              (tdef.get_infohash().encode('hex')[:5],
                               ds.get_current_speed('down')/1000,
                               ds.get_current_speed('up')/1000,
                               ds.get_progress(),
                               dlstatus_strings[ds.get_status()],
                               sum(ds.get_num_seeds_peers()), ds.download.handle.upload_limit()))

                if sum(ds.get_num_seeds_peers()) != 0:
                    libdl = ds.download
                    for i in libdl.handle.get_peer_info():
                        self._logger.error("%s:%s source:%s", i.ip[0], i.ip[1], i.source)

                return 1.0, False

            download = self.session.start_download_from_tdef(tdef, dscfg)
            download.set_state_callback(seeder_callback, delay=1)

    def _create_test_torrent(self, filename='', size=0):
        filepath = path.join(self.upload_dir_path, "%s-%s.data" % (self.scenario_file, filename))

        tdef = TorrentDef()
        with open(filepath, 'wb') as fp:
            fp.write("0" * int(size))

        tdef.add_content(filepath)

        # doesn't matter for now
        tdef.set_tracker("http://127.0.0.1:9197/announce")
        tdef.finalize()

        tdef_file = path.join(self.upload_dir_path, "%s.torrent" % filename)
        tdef.save(tdef_file)

        self._logger.error("Created %s torrent (%s) with size %s", filename, hexlify(tdef.get_infohash()), size)

        return tdef

    def start_download(self, name):
        if not self.dl_lc:
            self.dl_lc = lc = LoopingCall(self.start_download, name)
            lc.start(1.0, now=False)

        if self.joined_community:
            self.dl_lc.stop()
            self.dl_lc = None
        else:
            self._logger.error("Pending download")
            return

        #shameless copy from boostingsource
        CHANTOR_DB = ['ChannelTorrents.channel_id', 'Torrent.torrent_id', 'infohash', '""', 'length',
                          'category', 'status', 'num_seeders', 'num_leechers', 'ChannelTorrents.id',
                          'ChannelTorrents.dispersy_id', 'ChannelTorrents.name', 'Torrent.name',
                          'ChannelTorrents.description', 'ChannelTorrents.time_stamp', 'ChannelTorrents.inserted']

        torrent_values = self.joined_community._channelcast_db.getTorrentsFromChannelId(self.joined_community.get_channel_id(), True, CHANTOR_DB, 5)
        if torrent_values:
            listtor = self.torrent_mgr.create_torrents(torrent_values, True,
                    {self.joined_community.get_channel_id(): self.joined_community._channelcast_db.getChannel(self.joined_community.get_channel_id())})

            self._logger.error("list torrent %s", listtor)

if __name__ == '__main__':
    ChannelDownloadClient.scenario_file = posix.environ.get('SCENARIO_FILE', 'channel_download.scenario')
    main(ChannelDownloadClient)