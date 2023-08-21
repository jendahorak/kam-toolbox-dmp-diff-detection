# import libs

import os, sys, importlib

# List of directories where modules are searched
scripts_folder = os.path.join(os.path.dirname(__file__), 'scripts')
sys.path.append(scripts_folder)

import calculate_against_DMP

# Utilitka pro reloadování při testování kodu v ArcPRO
for tool in [calculate_against_DMP]:
    importlib.reload(tool)
    

from calculate_against_DMP import CheckAgainstDMP

class Toolbox(object):
    """Define the toolbox (the name of the toolbox is the name of the
    .pyt file)."""

    def __init__(self) -> None:
        self.label = 'DMP_toolbox'
        self.alias = 'dmpvalidation'
        self.tools = [CheckAgainstDMP]
        pass