import argparse
import itertools
import sys

import yaml

import fprime_ci.plugin.system # Force this to run first to achieve monkey patching

import logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)



from fprime_gds.executables.cli import ParserBase, ConfigDrivenParser, PluginArgumentParser
from fprime_ci.ci import CiFlow
from fprime_ci.plugin.system import Plugins

from typing import Any, Dict, Tuple



class StageParser(ParserBase):

    def get_arguments(self) -> Dict[Tuple[str, ...], Dict[str, Any]]:
        """Arguments needed for root processing"""
        return {
            ("--add-stage", ): {
                "dest": "stages",
                "action": "append",
                "default": CiFlow.get_stages(),
                "choices": CiFlow.get_stages(),
                "help": "Add a stage to run. When no --add-stage supplied, all will run",
            },
            ("--skip-stage", ): {
                "action": "append",
                "choices": CiFlow.get_stages(),
                "default": [],
                "help": "Skip stage added by --add-stage (or all)",
            }
        }
    
    def handle_arguments(self, args, **kwargs):
        """ Handle the arguments """
        args.stages = [stage for stage in args.stages if stage not in args.skip_stage]
        return args

from pathlib import Path
def main():
    """ Main function """
    ConfigDrivenParser.set_default_configuration(None)
    args, _ = ConfigDrivenParser.parse_args(
        [
            StageParser,
            PluginArgumentParser(Plugins.system()),
        ],
        description="F Prime CI system"
    )
    LOGGER.info(f"Starting CI for '{args.ci_selection}'")
    plugin = Plugins.system().get_selected_class("ci")()

    ci_flow = CiFlow(plugin)
    try:
        ci_flow.run(context=args.config_values, stages=args.stages)
    except Exception as exception:
        LOGGER.critical("Failed to run CI: %s", exception)
        raise
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
