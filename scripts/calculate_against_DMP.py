import os
import sys
import arcpy
import logging
from collections import namedtuple

from typing import (List, Union)
numeric = Union[int, float]
from toolbox_utils.messages_print import aprint, log_it, setup_logging # log_it printuje jak do arcgis console tak do souboru
from toolbox_utils.gdb_getter import get_gdb_path_3D_geoms, get_gdb_path_3D_geoms_multiple
from toolbox_utils.clear_selection import clear_selection

class CheckAgainstDMP(object):
    '''
    Class as a arcgis tool abstraction in python
    '''

    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "1. Calculate difference between PolygonZ geometry and Raster surface"
        self.name = 'Check difference between geometry and DMP'
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        log_file_path = arcpy.Parameter(
            name='log_dir_path',
            displayName="Output location for the .log file:",
            direction='Input',
            datatype='DEFolder',
            parameterType='Required',
            enabled='True',
        )

        input_DMP = arcpy.Parameter(
            name='input_dmp',
            displayName='Input DMP for height comparison',
            direction='Input',
            datatype = ['DERasterDataset','GPRasterLayer'],
            parameterType = 'Required',
            enabled = 'True'
        )


        input_PolygonZ_geometery = arcpy.Parameter(
            name='in_geom',
            displayName='In PolygonZ',
            direction='Input',
            datatype=['GPFeatureLayer', 'DEFeatureClass'],
            parameterType='Required',
            enabled='True'
            )
        
        calculate_zonal_table_flag = arcpy.Parameter(
            name='calculate_zonal_table_flag',
            displayName='Calculate zonal table and fields?',
            direction='Input',
            datatype='GPBoolean',
            parameterType='Optional',
            enabled='True'
        )
        
        update_fields_flag = arcpy.Parameter(
            name='update_fields_flag',
            displayName='Update fields based on zonal table?',
            direction='Input',
            datatype='GPBoolean',
            parameterType='Optional',
            enabled='True'
        )
        


        # TODO - uncoment whern running as a tool
        log_file_path.value = os.path.dirname(arcpy.mp.ArcGISProject("CURRENT").filePath)
        input_DMP.value = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\29_Plackova_aktualizace_3d_modelu\01_Developement\gis\29_Plackova_aktualizace_3d_modelu\29_Plackova_aktualizace_3d_modelu.gdb\sumavska_test_dmp"
        # output_PolyZ_workspace.filter.list = ["Local Database"]

        params = [log_file_path, input_DMP, input_PolygonZ_geometery, calculate_zonal_table_flag, update_fields_flag]

        return params

    
    def isLicensed(self):
        try:
            if arcpy.CheckExtension("Spatial") != "Available":
                raise Exception
        except Exception:
            return False  # The tool cannot be run
        
        return True  # The tool can be run

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        pass

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        pass

    def execute(self, parameters, messages):
        """Process the parameters"""
        param_values = (p.valueAsText for p in parameters)
        try:
            main(*param_values) 
        except Exception as err:
            arcpy.AddError(err)
            sys.exit(1)
        return


# UTILITY
def init_logging(log_dir_path: str) -> None:
    '''
    initializes logging instance (logger object, format, log_file locatio etc.) for current tool
    '''
    class_name = CheckAgainstDMP().name.replace(' ', '_')
    setup_logging(log_dir_path,class_name, __name__)

def get_fc_from_gdb_within_dataset(gdb_path: str) -> str:
    '''
    Returns first feature class from first dataset in given gdb.
    '''
    arcpy.env.workspace = gdb_path

    for dat in arcpy.ListDatasets():
        for fc in arcpy.ListFeatureClasses('','', dat):
            return fc    

def get_fc_from_gdb_direct(gdb_path: str, fc_name=None) -> str:
    '''
    Returns first fc from given gdb or any with specified name fc_name.
    '''
    arcpy.env.workspace = gdb_path

    for fc in arcpy.ListFeatureClasses(fc_name):
        return fc

def fieldExists(dataset: str, field_name: str) -> bool:
    """Return boolean indicating if field exists in the specified dataset."""
    return field_name in [field.name for field in arcpy.ListFields(dataset)]


def tableExists(table_name: str) -> bool:
    '''Return boolean indicating if table exists in the specified workspace.'''
    # TODO - make optional to create zonal statistics 
    return table_name in [table for table in arcpy.ListTables(table_name)]    

def getMinConsecutive(heights: list) -> float:
    heights = [1.2, 2.3, 1.2, 3.1, 3.1, 4.0, 2.5, 2.5]

    min_height = None
    found_indices = []

    for i in range(len(heights) - 1):
        if heights[i] == heights[i + 1]:
            if min_height is None or heights[i] < min_height:
                min_height = heights[i]
                found_indices = [i, i + 1]
            elif heights[i] == min_height:
                found_indices.append(i + 1)

    if found_indices:
        return found_indices
    else:
        log_it("No consecutive identical minimum heights found.", 'info', __name__)



def calculate_diff_attributes(input_fc:str, ground_dmr:str, workspace:str = None):
    # Define a named tuple for your columns
    log_it(f'-'*15, 'info', __name__)
    log_it(f'Updating featureclasses with height attributes.', 'info', __name__)
    RowData = namedtuple('RowData', ['shape', 'min', 'max', 'mean', 'avg_verts', 'diff_avg_verts_dmp_min', 'diff_avg_verts_dmp_max', 'diff_avg_verts_dmp_mean'])

    # Example usage in your code
    cols = ['SHAPE@', 'MIN', 'MAX', 'MEAN', 'AVG_VERTS', 'DIFF_AVG_VERTS_DMP_MIN', 'DIFF_AVG_VERTS_DMP_MAX', 'DIFF_AVG_VERTS_DMP_MEAN']
    sql_expression = "PLOCHA_KOD IN (3, 2)"

    with arcpy.da.UpdateCursor(input_fc, cols, where_clause=sql_expression) as cursor:
        for row in cursor:
            # Create a named tuple from the row data
            data = RowData(*row)

            shape_geometry_attr = data.shape
            verts_z_mean = data.avg_verts

            z_vals = []
            for shape_part in shape_geometry_attr:
                for shape_vertex in shape_part:
                    x, y, z = shape_vertex.X, shape_vertex.Y, shape_vertex.Z
                    z_vals.append(z)
                z_mean = sum(z_vals) / len(z_vals)

                # TODO - more detailed calculations
                # # vert with min height
                # z_min = min(z_vals)
                # # min line 
                # min_line = getMinConsecutive(z_vals)
                # # vert with max height
                # z_max = max(z_vals)
                log_it(f"Calculate avg_height of verticies", 'info', __name__)
            
            dmp_diff_min = data.min - z_mean
            log_it(f"Calculate difference between avg_height of verticies and DMP min height for the given zone", 'info', __name__)

            dmp_diff_max = data.max - z_mean
            log_it(f"Calculate difference between avg_height of verticies and DMP max height for the given zone", 'info', __name__)

            dmp_diff_mean = data.mean - z_mean
            log_it(f"Calculate difference between avg_height of verticies and DMP avg height for the given zone", 'info', __name__)

            # Update the named tuple and assign it back to the row
            data = data._replace(avg_verts=z_mean, diff_avg_verts_dmp_min=dmp_diff_min, diff_avg_verts_dmp_max=dmp_diff_max, diff_avg_verts_dmp_mean=dmp_diff_mean)

            # Update the row with the modified named tuple
            cursor.updateRow(tuple(data))


def get_field_names(fc) -> list:
    return [f.name for f in arcpy.ListFields(fc)]


def calculate_zonal_fields(fc: str, zonal_stats_table_name: str, key_field: str, workspace: str, input_dmp, run_flag: bool, update_attr_flag:bool) -> None:
    
    if(run_flag):
        arcpy.env.workspace = workspace
        out_table = os.path.join(workspace, zonal_stats_table_name)

        if not tableExists(zonal_stats_table_name):
            log_it('Creating new zonal table...', 'info', __name__)
            sql_expression = "PLOCHA_KOD IN (3, 2)"
            building_roofs = arcpy.management.SelectLayerByAttribute(fc, "NEW_SELECTION", sql_expression)

            log_it(f'{out_table}', 'info', __name__)
            log_it('Creating Zonal statistic table...', 'info', __name__)
            # Summarizes the values of a raster within the zones of another dataset and reports the results as a table.
            arcpy.sa.ZonalStatisticsAsTable(building_roofs, key_field, input_dmp, out_table, statistics_type='MIN_MAX_MEAN')
        else:
            log_it(f'Zonal Statistics for given {fc} in {workspace} were already calculated if you wish to recalculate them choose another output workspace or delete existing zonal table', 'info', __name__)


        if update_attr_flag:
            arcpy.management.DeleteField(fc, ['MIN', 'MAX', 'MEAN', 'AVG_VERTS','DIFF_AVG_VERTS_DMP_MIN', 'DIFF_AVG_VERTS_DMP_MAX', 'DIFF_AVG_VERTS_DMP_MEAN'])
            log_it(f'Fields to be updated deleted', 'info', __name__)


        if not fieldExists(fc, 'MIN') and not fieldExists(fc, 'MAX') and not fieldExists(fc, 'MEAN'):
            arcpy.management.JoinField(fc, key_field, out_table, key_field, ['MIN', 'MAX', 'MEAN'])
            arcpy.management.AddField(fc, 'AVG_VERTS', 'DOUBLE')
            arcpy.management.AddField(fc, 'DIFF_AVG_VERTS_DMP_MIN', 'DOUBLE')
            arcpy.management.AddField(fc, 'DIFF_AVG_VERTS_DMP_MAX', 'DOUBLE')
            arcpy.management.AddField(fc, 'DIFF_AVG_VERTS_DMP_MEAN', 'DOUBLE')

            log_it(f'Required fields were created in {fc}', 'info', __name__)
        else:
            log_it(f'Field MIN and MAX already exist in {fc}. Fields MIN, MAX, MEAN, and AVG_VERTS have been updated from the ZonalTable', 'info', __name__)
    else: 
        log_it(f'Atrributes havent been calculated because of user choice, change flag for running the raster calculation.', 'info', __name__)



def main(log_dir_path: str, input_DMP: str, input_polygonZ_geometry: str, calculate_zonal_table_flag:bool, update_fields_flag:bool) -> None:
    '''
    Main runtime.
    '''
    arcpy.CheckOutExtension("Spatial")

    # setup file logging
    init_logging(log_dir_path)

    # fc = get_fc_from_gdb_direct(input_polygonZ_geometry)
    
    log_it(f'{input_polygonZ_geometry}', 'info', __name__ )

    key_field = 'OBJECTID'
    zonal_stats_table_name = f'{input_polygonZ_geometry}_zonal_stat_base_test'

    clear_selection(input_polygonZ_geometry)
    calculate_zonal_fields(input_polygonZ_geometry, zonal_stats_table_name, key_field, arcpy.env.workspace, input_DMP, calculate_zonal_table_flag, update_fields_flag)


    clear_selection(input_polygonZ_geometry)
    calculate_diff_attributes(input_polygonZ_geometry, input_DMP, arcpy.env.workspace)

##################################################
############ Run the tool from IDE ###############

# fake parametry

# imtpw = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\02_Input_Data\TOPGIS_2021\Lokalita_21_2021_08_10"
# imtpw = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\02_Input_Data\TopGIS_clean\Lokalita_43_2022_08_11"
# raster = r'I:\01_Data\02_Prirodni_pomery\04_Vyskopis\Brno\DMR_DMT\TOPGIS\2019\04_GIS\rastr\rastr\DMT2019\DTM_2019_L_025m.tif'
# omptw = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\01_Developement\02_Output\new_output_workspaces\polyZ_workspace.gdb'

# log_file_path = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\29_Plackova_aktualizace_3d_modelu\01_Developement\gis\29_Plackova_aktualizace_3d_modelu'  # bude parameter
# input_DMP = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\29_Plackova_aktualizace_3d_modelu\01_Developement\gis\29_Plackova_aktualizace_3d_modelu\29_Plackova_aktualizace_3d_modelu.gdb\sumavska_test_dmp'
# input_polygonZ_geometry = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\29_Plackova_aktualizace_3d_modelu\01_Developement\gis\29_Plackova_aktualizace_3d_modelu\29_Plackova_aktualizace_3d_modelu.gdb'
# calculate_zonal_table_flag = False
# update_fields_flag = False
# main(log_file_path, input_DMP, input_polygonZ_geometry, calculate_zonal_table_flag, update_fields_flag)

###################################################


