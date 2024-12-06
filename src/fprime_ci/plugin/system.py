""" fprime_ci/plugin.py: plugin management for fprime_ci """
from abc import ABC, abstractmethod
from typing import Type

import fprime_gds.plugin.system # Borrow the fprime GDS plugin system
import fprime_ci.plugin.definitions # Monkey-patch the definitions

# Usable types
from fprime_ci.plugin.definitions import PluginType
from fprime_ci.plugins.null import Null
from fprime_ci.plugins.vxworks import VxWorksDkm
from fprime_ci.ci import Ci


_PLUGIN_METADATA = {
    "ci": {
        "class": Ci,
        "type": PluginType.SELECTION,
        "built-in": [Null, VxWorksDkm]
    }
}
fprime_gds.plugin.system._PLUGIN_METADATA = _PLUGIN_METADATA # Monkey-patch our metadata

# After monkey-patching reimport to get the plugins object
from fprime_gds.plugin.system import Plugins
