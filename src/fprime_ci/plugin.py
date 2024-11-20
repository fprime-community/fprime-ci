""" fprime_ci/plugin.py: plugin management for fprime_ci """
from abc import ABC, abstractmethod
from typing import Type
import fprime_gds.plugin.definitions
fprime_gds.plugin.definitions.PLUGIN_NAME = "fprime_ci" # Monkey-patch the plugin-system name

import fprime_gds.plugin.system # Borrow the fprime GDS plugin system


class CiPlugin(ABC):

    @abstractmethod
    def load(self, context: dict):
        """ Load the software to target hardware """

    @abstractmethod
    def boot(self, context: dict):
        """ Boot the software"""

    @classmethod
    @fprime_gds.plugin.definitions.gds_plugin_specification
    def register_ci_plugin(cls) -> Type["CiPlugin"]:
        """ Allows loading of Ci plugin"""
        raise NotImplementedError()


class TestCiPlugin(CiPlugin):
    def load(self, context: dict):
        print("LOADING")

    def boot(self, context: dict):
        print("BOOTING")

    @classmethod
    def get_name(cls):
        """ Get the name of this plugin """
        return "test"

    @classmethod
    def get_arguments(cls):
        """ Get arguments for the framer/deframer """
        return {}

    @classmethod
    @fprime_gds.plugin.definitions.gds_plugin_implementation
    def register_ci_plugin(cls) -> Type["CiPlugin"]:
        """ Allows loading of Ci plugin"""
        return TestCiPlugin


_PLUGIN_METADATA = {
    "ci": {
        "class": CiPlugin,
        "type": fprime_gds.plugin.definitions.PluginType.SELECTION,
        "built-in": [TestCiPlugin]
    }
}
fprime_gds.plugin.system._PLUGIN_METADATA = _PLUGIN_METADATA # Monkey-patch our metadata

# After monkey-patching reimport to get the plugins object
from fprime_gds.plugin.system import Plugins

