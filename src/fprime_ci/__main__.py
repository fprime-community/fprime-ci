import argparse
import itertools
import sys

import yaml

import fprime_ci.plugin.system # Force this to run first to achieve monkey patching

import logging
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

import fprime_gds.executables.cli
from fprime_ci.ci import CiFlow

def parse_args():
    """ Parse command line arguments """
    parser = argparse.ArgumentParser(description="Fprime CI")
    parser.add_argument("-c", "--config", type=argparse.FileType('r'),
                        help="YAML configuration file used to populate arguments")
    parser.add_argument("--add-stage", action="append",
                        help="Add a stage to run. When unspecified all stages will run.")
    parser.add_argument("--skip-stage", action="append",
                        help="Skip a stage. When unspecified all stages will run.")
    # Grab the args namespace and get the configuration file
    args_ns = parser.parse_args()
    config = yaml.load(args_ns.config, Loader=yaml.SafeLoader)
    plugin_args = list(itertools.chain.from_iterable([(f"--{key}", str(value)) for key, value in config.get("plugin", {}).items()]))
    return config, plugin_args

def main():
    """ Main function """
    initial_config, plugin_args = parse_args()
    args, _ = fprime_gds.executables.cli.ParserBase.parse_args(
        [
            fprime_gds.executables.cli.PluginArgumentParser,
        ],
        arguments=plugin_args,
        description="F Prime CI system"
    )
    LOGGER.info(f"Starting CI for '{args.ci_selection}'")
    plugin = args.ci_selection_instance

    ci_flow = CiFlow(plugin)
    try:
        stages = CiFlow.get_stages() if not "add_stage" in args else args.add_stage
        stages = [stage for stage in stages if "skip_stage" not in args or stage not in args.skip_stage]
        ci_flow.run(context=initial_config, stages=stages)
    except Exception as exception:
        LOGGER.critical("Failed to run CI: %s", exception)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
