""" fprime_ci_plugins/vxworks.py: vxworks CI implementation

This module supplies basic VxWorks CI plugins. These basic implementations will build and run VxWorks builds using
TFTP to provide boot modules and RSH to provide Downloadable Kernel Modules (DKMs). This plugin assumes certain
infrastructure is available on the host machine:

1. A docker container running with TFTP and RSH installed
2. The target hardware bootloader is configured for TFTP boot
"""
from fprime_ci.plugin import CiPlugin

class VxWorksCI(CiPlugin):
    """ VxWorks CI plugin implementation """

    def build(self, context: dict) -> dict:
        """ Performs the VxWorks build before the standard F Prime build

        This build step will perform the VxWorks image build providing the uVxWorks and dtb files required for loading.
        It expects the bootloader is configured to use the uVxWorks and dtb files correctly.

        This implementation ops not to set any arguments as the settings.ini should be sufficient.

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