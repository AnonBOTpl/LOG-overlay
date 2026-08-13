"""Session id helper for one game launch."""

from __future__ import absolute_import

import random
import time


def make_session_id(prefix="ts4"):
    stamp = time.strftime("%Y-%m-%dT%H-%M-%S")
    suffix = "{0:04x}".format(random.randint(0, 0xFFFF))
    return "{0}-{1}-{2}".format(prefix, stamp, suffix)
