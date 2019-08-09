#
# ovirt-hosted-engine-ha -- ovirt hosted engine high availability
# Copyright (C) 2013 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#

import logging

from ..env import config, config_constants
from ..env import constants
from ..lib import brokerlink
from ..lib import metadata
from ..lib import storage_server
from ..lib import util
from ..lib.exceptions import MetadataError


class HAClient(object):
    class StatModes(object):
        """
        Constants used in calls to retrieve runtime stats:
          ALL - return global metadata and host statistics
          HOST - return only host statistics
          GLOBAL - return only global metadata
        """
        ALL = 'ALL'
        HOST = 'HOST'
        GLOBAL = 'GLOBAL'

    class GlobalMdFlags(object):
        """
        Constants used to refer to global metadata flags:
          MAINTENANCE - maintenance flag
        Note that the value here must equal a key in metadata.global_flags
        """
        MAINTENANCE = 'maintenance'

    class MaintenanceMode(object):
        """
        Constants used in calls to set maintenance mode:
          LOCAL - local host maintenance
          GLOBAL - global maintenance
        """
        LOCAL = 'LOCAL'
        GLOBAL = 'GLOBAL'
        LOCAL_MANUAL = 'LOCAL_MANUAL'

    def __init__(self, log=False, **kwargs):
        """
        Create an instance of HAClient.  If the caller has a log handler, it
        should pass in log=True, else logging will effectively be disabled.
        """
        if not log:
            logging.basicConfig(filename='/dev/null', filemode='w+',
                                level=logging.CRITICAL)
        self._log = logging.getLogger("{}.HAClient".format(__name__))
        self._config = None

    def _check_liveness_metadata(self, md, broker):
        md["live-data"] = broker.is_host_alive(md["host-id"])
        self._log.debug("Is host '{0}' alive? -> '{1}'"
                        .format(md["host-id"], md["live-data"]))

        return md["live-data"]

    def _check_liveness_for_stats(self, stats, broker):
        for host_id in stats:
            if host_id == 0:  # global stats
                continue
            self._check_liveness_metadata(stats[host_id], broker)

    def get_all_stats(self, mode=StatModes.ALL, timeout=None):
        """
        Connects to HA broker to get global md and/or host stats, based on
        mode (member of StatModes class).  Returns the stats in a dictionary
        as {host_id: = {key: value, ...}}
        """
        if self._config is None:
            self._config = config.Config()
        broker = brokerlink.BrokerLink(timeout=timeout)
        stats = broker.get_stats_from_storage()

        stats = self._parse_stats(stats, mode)
        self._check_liveness_for_stats(stats, broker)
        return stats

    def get_all_stats_direct(self, mode=StatModes.ALL):
        """
        Like get_all_stats(), but bypasses broker by directly accessing
        storage.
        """
        from ..broker import storage_broker

        sb = storage_broker.StorageBroker()
        stats = sb.get_raw_stats()

        return self._parse_stats(stats, mode)

    def _parse_stats(self, stats, mode):
        """
        Parse passed-in stats dict, typically returned from the HA broker.
        It should be a dictionary with key being the host id (or 0 for global
        metadata) and value being the string-encoded representation of the
        host and/or global statistics, decodable by the parsing routines in
        the metadata module.

        This returns a dict of dicts containing the parsed metadata, logging
        any encountered errors.  No mechanism is currently provided for
        callers to detect a parsing error.
        """
        output = {}
        for host_id, data in stats.items():
            try:
                if host_id == 0 and mode != self.StatModes.HOST:
                    md = metadata.parse_global_metadata_to_dict(self._log,
                                                                data)
                    output[0] = md
                elif host_id != 0 and mode != self.StatModes.GLOBAL:
                    md = metadata.parse_metadata_to_dict(host_id, data)
                    output[md['host-id']] = md
                else:
                    continue
            except MetadataError as e:
                self._log.error(str(e))
                continue
        return output

    def get_all_host_stats(self, timeout=None):
        """
        Connects to HA broker, reads stats for all hosts, and returns
        them in a dictionary as {host_id: = {key: value, ...}}
        """
        return self.get_all_stats(self.StatModes.HOST, timeout)

    def get_all_host_stats_direct(self):
        """
        Like get_all_host_stats(), but bypasses broker by directly accessing
        storage.
        """
        return self.get_all_stats_direct(self.StatModes.HOST)

    def set_global_md_flag(self, flag, value, timeout=None):
        """
        Connects to HA broker and sets flags in global metadata, leaving
        any other flags unaltered.  On error, exceptions will be propagated
        to the caller.
        """
        try:
            transform_fn = metadata.global_flags[flag]
        except KeyError:
            raise Exception('Unknown metadata flag: {0}'.format(flag))

        # If the metadata value specifies a transformation function, send the
        # input value through it in order to normalize and/or verify the data.
        if transform_fn:
            put_val = transform_fn(value)
        else:
            put_val = value

        broker = brokerlink.BrokerLink(timeout=timeout)
        all_stats = broker.get_stats_from_storage()

        global_stats = all_stats.get(0)
        if global_stats and len(global_stats):
            try:
                md_dict = metadata.parse_global_metadata_to_dict(
                    self._log, global_stats)
            except Exception:
                self._log.warn("Metadata block corrupted. Correcting.")
                md_dict = {}
        else:
            md_dict = {}

        md_dict[flag] = put_val
        block = metadata.create_global_metadata_from_dict(md_dict)
        broker.put_stats_on_storage(0, block)

    def get_local_host_id(self):
        if self._config is None:
            self._config = config.Config()

        host_id = self._config.get(config.ENGINE, config_constants.HOST_ID)
        return int(host_id) if host_id else None

    def get_local_host_score(self, timeout=None):
        if self._config is None:
            self._config = config.Config()

        host_id = int(self._config.get(config.ENGINE,
                                       config_constants.HOST_ID))
        broker = brokerlink.BrokerLink(timeout=timeout)
        stats = broker.get_stats_from_storage()

        score = 0
        if host_id in stats:
            try:
                md = metadata.parse_metadata_to_dict(host_id, stats[host_id])
            except MetadataError as e:
                self._log.error(str(e))
            else:
                # Only report a non-zero score if the local host has had a
                # recent update.
                if self._check_liveness_metadata(md, broker):
                    score = md['score']

        return score

    def set_maintenance_mode(self, mode, value, timeout=None):
        """
        Set maintenance to the specified mode.
        global - Disable/Enable the agents from monitoring the state
        of the engine virtual machine.
        local - Set the host's local maintenance (true/false).
        local maintenance manual - for manual setting of local maintenance
        when set/unset, local mode should have the same value.
        """
        if mode == self.MaintenanceMode.GLOBAL:
            self.set_global_md_flag(
                self.GlobalMdFlags.MAINTENANCE,
                str(value),
                timeout
            )

        elif mode == self.MaintenanceMode.LOCAL:
            if self._config is None:
                self._config = config.Config()
            self._config.set(config.HA,
                             config_constants.LOCAL_MAINTENANCE,
                             str(util.to_bool(value)))
        elif mode == self.MaintenanceMode.LOCAL_MANUAL:
            if self._config is None:
                self._config = config.Config()
            self._config.set(config.HA,
                             config_constants.LOCAL_MAINTENANCE_MANUAL,
                             str(util.to_bool(value)))
            self._config.set(config.HA,
                             config_constants.LOCAL_MAINTENANCE,
                             str(util.to_bool(value)))

        else:
            raise Exception("Invalid maintenance mode: {0}".format(mode))

    def set_shared_config(self, key, value, config_type=None):
        if self._config is None:
            self._config = config.Config()
        self._config.set_config_on_shared_storage(key, value, config_type)

    def get_shared_config(self, key, config_type=None):
        if self._config is None:
            self._config = config.Config()
        return self._config.get_config_from_shared_storage(key, config_type)

    def get_all_config_keys(self, config_type=None):
        if self._config is None:
            self._config = config.Config()
        return self._config.get_all_shared_keys(config_type)

    def reset_lockspace(self, force=False, timeout=None):
        if self._config is None:
            self._config = config.Config()

        host_id = self._config.get(config.ENGINE, config_constants.HOST_ID)
        is_configured = self._config.get(config.ENGINE,
                                         config_constants.CONFIGURED)
        if (not host_id or
                (is_configured != "True" and is_configured is not None)):
            self._log.error("Hosted engine is not configured.")
            return

        # Connect to a broker and read all stats
        broker = brokerlink.BrokerLink(timeout=timeout)

        stats = broker.get_stats_from_storage()

        # Process raw stats
        try:
            all_stats = self._parse_stats(stats, self.StatModes.ALL)
            self._check_liveness_for_stats(all_stats, broker)
        except Exception as ex:
            self._log.exception(ex)
            all_stats = {}

        # Check whether it is safe to perform lockfile reset
        for id, stats in all_stats.items():
            if id == 0:
                if (not force and
                        not stats.get(self.GlobalMdFlags.MAINTENANCE, False)):
                    raise Exception("Lockfile reset can be performed in"
                                    " global maintenance mode only.")
            else:
                if not force and not stats.get("stopped", False):
                    raise Exception("Lockfile reset cannot be performed with"
                                    " an active agent.")

        broker.reset_lockspace()

    def connect_storage_server(self, timeout=constants.VDSCLI_SSL_TIMEOUT):
        sserver = storage_server.StorageServer()
        sserver.connect_storage_server(timeout=timeout)

    def disconnect_storage_server(self, timeout=constants.VDSCLI_SSL_TIMEOUT):
        sserver = storage_server.StorageServer()
        sserver.disconnect_storage_server(timeout=timeout)

    def is_deployed(self):
        """
        Return True if all files in Config.static_files exist
        and are not empty and False otherwise.
        """
        return config.Config.static_files_exist()
