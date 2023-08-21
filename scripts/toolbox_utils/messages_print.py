import arcpy
import os
import logging
from datetime import datetime


def aprint(*args):
    '''Print message for python and arcpy tool.
    Parameters
    ----------
    *args : string
        any number of strings to be printed into messages
    '''
    args = [str(arg) for arg in args]
    m = f'{", ".join(args)}'
    # print(m)
    arcpy.AddMessage(m)



def setup_logging(log_dir_path: str, tool_name, logger_name) -> None:
    '''
    Setups custom logger with log file name named after used tool. 
    '''

    file_name = os.path.join(log_dir_path, f'{tool_name}_{datetime.now().strftime("%m-%d-%Y_%H-%M-%S")}.log')

    logger = logging.getLogger(logger_name)
    handler = logging.FileHandler(file_name)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _replace_n(message):
    message = message.replace('\n','')
    return message

def log_it(message: str, level: str, tool_name: str, arcgis_log=True, file_log=True) -> None:
    '''
    Print on steroids - by default logs out given message into specified file and also prints out message into argis messges when the tool is ran.
    '''
    logger = logging.getLogger(tool_name)


    if level == 'info':
        if arcgis_log:
            aprint(message)  
        if file_log:
            logger.info(_replace_n(message))
    elif level == 'warning':
        if arcgis_log:
            arcpy.AddWarning(message)
        if file_log:
            logger.warning(_replace_n(message))
    elif level == 'error':
        if arcgis_log:
            arcpy.AddError(message)
        if file_log:
            logger.error(_replace_n(message))
    else:
        aprint('Unknown problem with custom logging module')