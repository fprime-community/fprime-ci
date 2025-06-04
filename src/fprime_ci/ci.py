""" fprime_ci/ci.py: code for loading software onto target """
import copy
import logging
import os
import signal
import time
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Type
from fprime_ci.plugin.definitions import ci_plugin_specification
from fprime_ci.utilities import IOLogger, Stream

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
    class Keys(object):
        """ Required and optional context supplied keys for the system to function correctly

        These keys are may be declared in the context derived from configuration. If these are required and not defined,
        the CI system cannot function correctly and will fail early. If these are defined and of the incorrect type,
        the CI system will fail early.

        Keys are class attributes and must be set to the name used with the context object.
        Keys may define a parallel attribute <key>__ATTR__ to set attributes to a tuple of (key is required, key type).
        When unspecified, attributes are assumed to be: required, string type.

        This split was done for ease-of-use referring to the constants when reading context. i.e. context[Keys.NAME]
        """
        DEPLOYMENT_NAME = "deployment-name"
        PLATFORM_NAME = "platform-name"
        POWER_PORT = "power-port"
        POWER_PORT__ATTRS__ = (False, int)
        ENVIRONMENT = "environment"
        ENVIRONMENT__ATTRS__ = (False, dict)
        BUILD_OUTPUTS = "build-outputs"
        BUILD_OUTPUTS__ATTRS__ = (False, list)
        TEST_SCRIPT = "test-script"
        TEST_SCRIPT__ATTRS__ = (True, str)

    @staticmethod
    def subprocess(*args, asynchronous=False, timeout=10, capture=(False, False), **kwargs):
        """ subprocess.run wrapper to enforce timeouts and logging

        Wraps subprocess.run. Ensures that there is some specified timeout for the process to run so as not to bog down
        CI. Will also capture standard out/standard error and pass these units into the logging utility.

        Args:
            timeout (int): Timeout in seconds. Default: 10
            capture: capture output for post processing
            *args: additional positional arguments to pass to subprocess.run
            asynchronous: run asynchronously as a thread
            **kwargs: additional keyword arguments to pass to subprocess.run
        """
        invocation = " ".join(args[0]) if isinstance(args[0], list) else args[0]
        if "stdout" not in kwargs:
            kwargs["stdout"] = subprocess.PIPE
        if "stderr" not in kwargs:
            kwargs["stderr"] = subprocess.PIPE
        LOGGER.debug("Running: %s", invocation)
        process = subprocess.Popen(*args, **kwargs, text=True)
        
        stdout_logger = IOLogger(Stream.OUT, logging.DEBUG, logger_name=f"[{invocation[:20]}]", prefix="[stdout]", capture=capture[0])
        stderr_logger = IOLogger(Stream.ERROR, logging.ERROR, logger_name=f"[{invocation[:20]}]", prefix="[stderr]", capture=capture[1])

        io_parameters = (
            [
                process.stdout,
                process.stderr,
            ],
            [
                stdout_logger,
                stderr_logger,
            ]
        )
        if asynchronous:
            return_value = IOLogger.async_communicate(*io_parameters, timeout=timeout)
        else:
            try:
                runtime = IOLogger.communicate(
                    *io_parameters,
                    timeout=timeout
                )
            # Ensure that the process is over
            finally:
                process.kill()
                # Check the return code
                if (return_code := process.wait()) != 0:
                    raise RuntimeError(f"Process failed with return code {return_code}")

            # Warn for drastically out-of-band timeouts
            if timeout is not None and (timeout / runtime) > 2.0:
                LOGGER.warning("Timeout of %f more than double actual runtime of %f for '%s'",
                               timeout, runtime, invocation)
            return_value = runtime
        return process, return_value, (stdout_logger.data, stderr_logger.data)

    def wait_until(self, closure: Callable[None, None], timeout=float):
        """ Wait until function passes or timeout is hit """
        time_start = time.time()
        while time.time() < (time_start + timeout):
            if closure():
                return
            time.sleep(0.1)
        raise TimeoutError()


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
        self.gds_data = (None, None, (None, None))
        self.original_context = None

    @staticmethod
    def get_stages():
        """ Return the list of annotated stages """
        return _CI_STAGES

    def delegate_with_safe_context(self, delegate_method, context):
        """ Delegate to the delegate without allowing corruption to the original context"""
        context = delegate_method(context)
        if not isinstance(context, dict):
            raise CiFailure(f"Delegate failed to return context")
        for key, value in self.original_context.items():
            if key not in context or context[key] != value:
                raise CiFailure(f"Delegate corrupted context: {key} from {value} to {context.get(key, '--deleted--')}")
        return context

    @stage
    def validate(self, context: dict):
        """ Validate the initial context

        Plugins have required keys. This stage will validate the initial context contains those keys such that CI can
        fail early should these be absent. Once the required keys have been validated, this stage will calculate some
        useful keys should these (optional) keys not be set. Finally, anything set under 'environment' will be set in
        the environment used to execute 'subprocess'.

        Optional / Calculated keys:
            - "dictionary": full path to the dictionary
            - "executable": full path to the executable
            - "build-outputs": full path to outputs to validated post-build. Note: this is appended with dictionary and
                executable.

        Args:
            context: initial context supplied to the CI flow
        Return:
            validated context
        """
        for keys_class in [getattr(self, "Keys", object), getattr(self.delegate, "Keys", object)]:
            for key, value in keys_class.__dict__.items():
                if not key.startswith("__") and not key.endswith("__ATTRS__"):
                    required, expected_type = getattr(keys_class, f"{key}__ATTRS__", (True, str))
                    if required and value not in context:
                        raise CiFailure(f"Missing required key '{value}'")

                    if value in context and type(context[value]) is not expected_type:
                        raise CiFailure(f"Required key '{value}' must be of type '{expected_type.__name__}'")

        build_relative_base = Path("build-artifacts") / context["platform-name"] / context["deployment-name"]
        # Calculate the full dictionary path
        context["dictionary"] = Path.cwd() / (
                context["dictionary"] if "dictionary" in context else
                build_relative_base / "dict" / f"{context['deployment-name']}TopologyDictionary.json"
        )
        # Calculate the binary output
        context["executable"] = Path.cwd() / (
                context["executable"] if "executable" in context else
                build_relative_base / "bin" / context['deployment-name']
        )
        # Calculate the required build outputs
        context["build-outputs"] = [Path.cwd() / output for output in context.get("build-outputs", [])] + \
                [context["dictionary"], context["executable"]]
        # Set environment
        for key, value in context.get("environment", {}).items():
            os.environ[key] = value
        # Stash the original context
        self.original_context = copy.deepcopy(context)
        return context


    @stage
    def build(self, context: dict):
        """ Build the software on the target hardware """
        try:
            # Generate F Prime
            generate_arguments = ["fprime-util", "generate", "-f"]
            generate_arguments += context.get("extra-generate-arguments", [])
            self.subprocess(generate_arguments, timeout=60)
            # Build F Prime
            build_arguments = ["fprime-util", "build", "--jobs", str(context.get("jobs", 1))]
            build_arguments += context.get("extra-build-arguments", [])
            self.subprocess(build_arguments, timeout=60)
            # Custom build steps
            context = self.delegate_with_safe_context(self.delegate.build, context)
            for build_output in context["build-outputs"]:
                if not build_output.exists():
                    raise CiFailure(f"Build failed to produce output: '{build_output}'")
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def preload(self, context: dict):
        """ Preload software on the target hardware before power-on """
        try:
            context = self.delegate_with_safe_context(self.delegate.preload, context)
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
            self.gds_data = self.subprocess(arguments, asynchronous=True, timeout=None)
            time.sleep(5) # For GDS to launch and become stable
            if self.gds_data[0].poll() is not None:
                raise subprocess.SubprocessError(f"Failed to start GDS: {self.gds_data[0].poll()}")
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def power(self, context: dict):
        """ Power the target hardware """
        try:
            if "power-port" in context:
                setPowerOutletState("192.168.0.100", "admin", "1234", context["power-port"], True)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def load(self, context: dict):
        """ Load the software on the target hardware """
        try:
            context = self.delegate_with_safe_context(self.delegate.load, context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def launch(self, context: dict):
        """ Launch the software on the target hardware """
        try:
            context = self.delegate_with_safe_context(self.delegate.launch, context)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    @stage
    def test(self, context: dict):
        """ Power the target hardware """
        try:
            arguments = ["pytest"]
            if "dictionary" in context:
                dictionary_path = Path("build-artifacts") / context["dictionary"]
                arguments += ["--dictionary", str(dictionary_path)]
            arguments += [context["test-script"]]
            arguments += context.get("extra-pytest-arguments", [])
            self.subprocess(arguments, timeout=100)
        except Exception as exception:
            raise CiFailure(exception)
        return context

    def cleanup(self, context: dict):
        """ Required shutdown steps """
        failed = False
        gds_instance, gds_thread_data, _ = self.gds_data
        # Custom clean-up
        try:
            context = self.delegate_with_safe_context(self.delegate.cleanup, context)
        except Exception as exception:
            LOGGER.warning("Delegate cleanup failed: %s", exception)
            failed = True
        # Shutdown GDS
        try:
            if gds_instance is not None:
                gds_instance.send_signal(signal.SIGINT)
            if gds_thread_data is not None:
                IOLogger.join_communicate(gds_thread_data)
        except Exception as exception:
            LOGGER.warning("GDS termination failed: %s", exception)
            failed = True
        # Turn off power port
        try:
            if self.Keys.POWER_PORT in context:
                setPowerOutletState("192.168.0.100", "admin", "1234", context["power-port"], False)
        except Exception as exception:
            LOGGER.warning("Power-off outlet state failed: %s", exception)
            failed = True
        if failed:
            raise CiFailure("Failed to clean-up after CI")
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
            self.cleanup(context)
