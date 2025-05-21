""" fprime_ci.plugin.null: null plugin for CI """
import json
from typing import Type

from fprime_ci.plugin.definitions import ci_plugin_implementation, plugin
from fprime_ci.ci import Ci

@plugin(Ci)
class Null(Ci):
    """ NullPlugin - prints out steps """

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
        print(f"[INFO] Build step run with context:\n{json.dumps(context, indent=4)}")
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
        print(f"[INFO] Preload run with context:\n{json.dumps(context, indent=4)}")
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
        print(f"[INFO] Load run with context:\n{json.dumps(context, indent=4)}")
        return context

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
        print(f"[INFO] Preload run with context:\n{json.dumps(context, indent=4)}")
        return context

    @classmethod
    def get_name(cls):
        """ Return the name of the plugin """
        return "null"

    @classmethod
    def get_arguments(cls):
        """ Return the name of the plugin """
        return {}
