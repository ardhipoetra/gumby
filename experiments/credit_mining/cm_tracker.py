from os import path as path
from sys import path as pythonpath

import os
pythonpath.append(path.abspath(path.join(os.getcwd(), "python-bittorrent")))

from bittorrent import Tracker

# track = Tracker(port=6969)
# track.run()

#TODO find a way to stop tracker via gumby
