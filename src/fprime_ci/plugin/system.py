""" fprime_ci/plugin.py: plugin management for fprime_ci """
from abc import ABC, abstractmethod
from typing import Type

import fprime_gds.plugin.system # Borrow the fprime GDS plugin system

# Usable types
from fprime_ci.plugin.definitions import PluginType
from fprime_ci.plugins.null import Null
from fprime_ci.ci import Ci

class Plugins(fprime_gds.plugin.system.Plugins):
    @classmethod
    def get_plugin_metadata(cls, category: str = None):
        if cls.PLUGIN_METADATA is None:
            cls.PLUGIN_METADATA = {
                "ci": {
                "class": Ci,
                "type": PluginType.SELECTION,
                "built-in": [Null]
                }
            }
        return (
            cls.PLUGIN_METADATA[category]
            if category is not None
            else cls.PLUGIN_METADATA
        )
