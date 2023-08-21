import arcpy
from toolbox_utils.messages_print import log_it

def clear_selection(layer):
    """Clears the selection on the input layer."""
    log_it('Clearing current selection...', 'info', __name__)
    arcpy.SelectLayerByAttribute_management(layer, "CLEAR_SELECTION")