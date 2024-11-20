""" fprime_ci/plugin.py: plugin management for fprime_ci """
from abc import ABC, abstractmethod
from typing import Type
import fprime_gds.plugin.definitions
fprime_gds.plugin.definitions.PLUGIN_NAME = "fprime_ci" # Monkey-patch the plugin-system name

import fprime_gds.plugin.system # Borrow the fprime GDS plugin system


class CiPlugin(ABC):
    """ Abstract (virtual) base class for CI plugins

    This class represents the steps required to be implemented by a plugin to fit in to the CI system. This comes down
    to a standard flow:
        1. Build: generate and build the software. Plugin developers can control the arguments supplied to the generate
            step using the `build` method's output context. Other build steps can be performed here.
        2. Preload: load the software on the target system. This step runs *before* power-on allowing plugin developers
            to prepare things like network boot files. It is entirely under the control of the plugin developer via the
            `preload` function, but is optional. The default is a no-op.
        3. Power: the target hardware will be powered-on. Plugin developer does not have control here.
        4. Load: load the software on the target system. This step runs *after* power-on allowing the plugin developer
            to prepare software through active programs like "scp". It is entirely under the control of the developer
            via the `load` function, but is optional. The default is a no-op.
        TODO: flag to launch pre/post GDS
        3. Launch: plugin supplied steps to launch the software on the target system. The system will have power and the
            load step will have run successfully. No other guarantees are made. This is under the control of the plugin
            developer via the `launch` function and is required.
        4. Test: ???
    """
    def build(self, context: dict) -> dict:
        """ Plugin override for setting up the build

        Developers may set the fields "platform", "generate_arguments", and "build_arguments" to customize the build
        step. When not set, the default `settings.ini` supplied settings will apply to the build.  The build will be run
        without additional arguments.

        Developers can perform other build steps here (e.g. building an OS kernel to link against).

        This default implementation is a no-op where all expected settings will default to settings.ini.

        Args:
            context: build context aggregated across all build steps
        Returns:
            context with optionally set platform, generated_arguments and build_argument
        """
        return context

    def preload(self, context: dict):
        """ Load the software to target hardware before power-on

        This function may be overridden by platform developers to perform software loading actions in preparation for
        power-on. This is the most convenient place to set up files pulled-in via the boot process (like network boot
        files, etc). This step runs directly before power-on.

        TODO: list variables containing software set-up

        The default implementation does nothing.

        Args:
            context: build context aggregated across all build steps
        Returns:
            context optionally augmented with plugin-specific preload data
        """
        return context

    def load(self, context: dict):
        """ Load the software to target hardware after power-on

        This function may be overridden by platform developers to perform software loading actions in preparation post
        power-on. This is the most convenient place to copy files via an active program like scp  This step runs
        directly after power-on.

        The default implementation does nothing.

        Note: platforms with long boot times should confirm a successful boot code before attempting load operations.

        TODO: list variables containing software set-up
        Args:
            context: build context aggregated across all build steps
        Returns:
            context optionally augmented with plugin-specific preload data
        """
        return context

    @abstractmethod
    def launch(self, context: dict):
        """ Launch the software on the target hardware

        This function must be overridden by platform developers to perform software launching actions. This might
        include running the executable via SSH, passing launch codes to a serial console, restarting the hardware, or
        nothing.

        There is no default implementation for this function, platforms with no explicit launching steps must supply
        a no-op function.

        Args:
            context: build context aggregated across all build steps
        """
        raise NotImplementedError("Platform plugins must implement this function")

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

