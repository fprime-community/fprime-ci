import fprime_ci.plugin # Force this to run first to achieve monkey patching
import fprime_gds.executables.cli
from fprime_ci.load import load

import logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

def main():
    """ Main function """
    args, _ = fprime_gds.executables.cli.ParserBase.parse_args(
        [
            fprime_gds.executables.cli.PluginArgumentParser,
        ],
        description="F Prime CI system"
    )
    LOGGER.info(f"Starting CI for '{args.ci_selection}'")
    plugin = args.ci_selection_instance
    load(plugin, {})


if __name__ == "__main__":
    main()
