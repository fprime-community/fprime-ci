""" fprime_ci/ci.py: code for loading software onto target """
import logging
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type
from fprime_ci.plugin.definitions import ci_plugin_specification

from fprime_ci.power import setPowerOutletState

LOGGER = logging.getLogger(__name__)

class CiFailure(Exception):
    pass

class Ci(ABC):
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

    def cleanup(self, context: dict):
        """ Cleans after a CI run on both success and failure

        This function may be overridden by platform developers to cleaning actions. This step runs after all stages are
        executed in both success and failure cases. Since CI does not guarantee all stages are run, it is up to the
        developer to track what state needs cleaning.

        The default implementation does nothing.

        Args:
            context: build context aggregated across all build steps
        Returns:
            context optionally augmented with plugin-specific preload data
        """
        return context

    @classmethod
    @ci_plugin_specification
    def register_ci_plugin(cls) -> Type["Ci"]:
        """ Allows loading of Ci plugin"""
        raise NotImplementedError()


_CI_STAGES=[]
def stage(function):
    """ CI stage decorator

    A stage in the CI code is appended to the global list of stages known to CI. This allows the CI to automatically
    provide steps to the argument processing allowing the user to run a set of stages at a time. Typically, the user
    would build independently of the other stages, however; users may also use this functionality to step through CI.
    """
    global _CI_STAGES
    _CI_STAGES.append(function.__name__)
    return function

class CiFlow(Ci):
    """ Ci implementation of the CI flow

    The CI system runs a standard flow delegating to the plugin at specific points during the flow. This class
    encapsulates this work.
    """


    def __init__(self, plugin_delegate: Ci):
        """ Initialize flow """
        self.delegate = plugin_delegate
        self.gds_instance = None

    @stage
    def build(self, context: dict):
        """ Build the software on the target hardware """
        try:
            subprocess.run(["fprime-util", "generate", "-f"]).check_returncode()
            subprocess.run(["fprime-util", "build"]).check_returncode()
            context = self.delegate.build(context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def preload(self, context: dict):
        """ Preload software on the target hardware before power-on """
        try:
            context = self.delegate.preload(context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def gds(self, context: dict):
        """ Power the target hardware """
        try:
            arguments = ["fprime-gds", "-n"]
            if "dictionary" in context:
                dictionary_path = Path("build-artifacts") / context["dictionary"]
                arguments += ["--dictionary", str(dictionary_path)]
            arguments += context.get("extra-gds-arguments", [])
            self.gds_instance = subprocess.Popen(arguments)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def power(self, context: dict):
        """ Power the target hardware """
        try:
            setPowerOutletState("192.168.0.100", "admin", "1234", context["power-port"], True)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def load(self, context: dict):
        """ Load the software on the target hardware """
        try:
            context = self.delegate.load(context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def launch(self, context: dict):
        """ Launch the software on the target hardware """
        try:
            context = self.delegate.launch(context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    def cleanup(self, context: dict):
        """ Required shutdown steps """
        if self.gds_instance is not None:
            self.gds_instance.terminate()
        context = self.delegate.cleanup(context)
        return context

    @stage
    def test(self, context: dict):
        """ Power the target hardware """
        try:
            arguments = ["pytest"]
            if "dictionary" in context:
                dictionary_path = Path("build-artifacts") / context["dictionary"]
                arguments += ["--dictionary", str(dictionary_path)]
            if "pytest-script" in context:
                arguments += context["pytest-script"]
            arguments += context.get("extra-pytest-arguments", [])
            self.gds_instance = subprocess.Popen(arguments)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    def run(self, stages=None, context=None):
        """ Run through the CI flow """
        stages = stages or _CI_STAGES
        context = context or {}

        try:
            for stage in stages:
                LOGGER.info("Running stage: %s", stage)
                try:
                    context = getattr(self, stage)(context)
                except CiFailure as exception:
                    LOGGER.critical("Failed to run stage '%s': %s", stage, exception)
                    raise exception
                except Exception as exception:
                    LOGGER.critical("Unknown error in stage '%s'", stage, exc_info=exception)
                    raise exception
            LOGGER.info("Finished running stages: %s", stages)
            LOGGER.info("CI success!")
        finally:
            self.cleanup()
