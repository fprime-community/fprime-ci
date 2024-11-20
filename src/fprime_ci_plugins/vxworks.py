""" fprime_ci_plugins/vxworks.py: vxworks CI implementation """
from fprime_ci.load import load_implementation


@load_implementation
def load_vxworks_for_network_boot(context: dict):
    """ Load VxWorks software for network boot

    This function prepares the VxWorks software for network boot using TFTP to supply the VxWorks kernel and RSH to
    load when a separate Downloadable Kernel Module is supplied.

    Returns:
        updated context
    """

    print("VXWORKS -> ", context)

