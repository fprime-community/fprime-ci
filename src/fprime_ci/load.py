""" fprime_ci/load.py: code for loading software onto target """
import copy
from fprime_ci.plugin import CiPlugin


class LoadException(Exception):
    pass


def load(plugin: CiPlugin, context: dict) -> dict:
    """ Load the software on to the target platform delegating to the selected plugin

    Given the selected plugin name and the context, load the software onto the target platform by selecting the plugin's
    load_implementation and delegating to it. This function will trap all exceptions raised by the plugin and convert
    them into a LoadException.

    Args:
        plugin: name of the plugin to used while loading
        context: contextual information rolled forward from the previous step

    Returns:
        an updated context containing information about the software being loaded
    """
    context = copy.deepcopy(context)
    try:
        context = plugin.load(context)
    except Exception as exception:
        raise LoadException(exception)
    return context