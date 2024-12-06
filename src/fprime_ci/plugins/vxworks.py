""" fprime_ci_plugins/vxworks.py: vxworks CI implementation

This module supplies basic VxWorks CI plugins. These basic implementations will build and run VxWorks builds using
TFTP to provide boot modules and RSH to provide Downloadable Kernel Modules (DKMs). This plugin assumes certain
infrastructure is available on the host machine:

1. A docker container running with TFTP and RSH installed
2. The target hardware bootloader is configured for TFTP boot
"""
import logging
from typing import Type
import serial

import fprime_gds.plugin.definitions
from fprime_ci.ci import Ci
from fprime_ci.plugin.definitions import plugin

LOGGER = logging.getLogger(__name__)

@plugin
class VxWorksDkm(Ci):
    """ VxWorks CI plugin implementation supporting DKMs """
    def __init__(self, port, baud, flow:str="no"):
        """  """
        self.port = serial.Serial()
        self.port.port = port
        self.port.baudrate = baud
        self.port.rtscts = flow == "yes"

    def write_to_vxworks(self, message: bytes):
        """ Write to the serial port """
        assert self.port.is_open, "Serial port is not open"
        LOGGER.debug(">  " + message.decode("ascii").strip())
        self.port.write(message + b"\r\n")

    def wait_for_vxprompt(self):
        """ Wait for the vxprompt to be ready """
        assert self.port.is_open, "Serial port is not open"
        message = b""
        while message != b"-> ":
            byte_read = self.port.read(1)
            if len(byte_read) == 1 and byte_read[0] < 128:
                message += byte_read
                if byte_read == b"\n":
                    LOGGER.debug("<  " + message.decode("ascii").strip())
                    message = b""
            else:
                LOGGER.warning("Read non-ascii data from serial port")
        LOGGER.debug("<  " + message.decode("ascii").strip())

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
        # TODO: copy files to remoted area and list in context
        context["dkm_path"] = f"data/{context['deployment-name']}"
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
        try:
            self.port.open()
            self.wait_for_vxprompt()
            load_string = f"ld < {context['dkm_path']}"
            self.write_to_vxworks(load_string.encode("ascii"))
        except serial.SerialException as exception:
            raise Exception(f"Failed to use serial port: {exception}")
        finally:
            self.port.close()
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
        #TODO: wait for acknowledge
        try:
            self.port.open()
            self.wait_for_vxprompt()
            load_string = f"sp main"
            self.write_to_vxworks(load_string.encode("ascii"))
            self.wait_for_vxprompt()
        except serial.SerialException as exception:
            raise Exception(f"Failed to use serial port: {exception}")
        finally:
            self.port.close()
        return context

    @classmethod
    def get_name(cls):
        """ Returns the name of the plugin """
        return "vxworks-dkm"

    @classmethod
    def get_arguments(cls):
        """ Returns the arguments of the plugin """
        return {
            ("--port",): {
                "type": str,
                "default": "/dev/ttyUSB0",
                "help": "Serial port used to communicate with VxWorks",
            },
            ("--baud",): {
                "type": int,
                "default": 115200,
                "help": "Baud rate for the serial interface",
            },
            ("--flow",): {
                "default": "no",
                "type": str,
                "help": "Whether to enable flow control on the serial interface. Default: no",
            }

        }