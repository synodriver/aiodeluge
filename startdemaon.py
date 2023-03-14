"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
from deluge.core.rpcserver import log

log.setLevel("DEBUG")

from deluge.core.daemon_entry import start_daemon

start_daemon()
