""" fprime_ci/plugin/definitions.py: standard definitions overridden to be used in CI

The F Prime GDS provides a plugin system, however; to reuse it in CI some changes (monkey patches) are required to make
it all work. This file sets up plugin definitions and performs the necessary monkey patching.
"""
from fprime_gds.plugin.definitions import gds_plugin_implementation as ci_plugin_implementation
from fprime_gds.plugin.definitions import gds_plugin_specification as ci_plugin_specification
from fprime_gds.plugin.definitions import PluginType, gds_plugin as plugin
