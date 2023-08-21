import os
import sys
import arcpy
import logging
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
            datatype='GPLayer',
            parameterType='Required',
            enabled='True'
            )


        
        log_file_path.value = os.path.dirname(arcpy.mp.ArcGISProject("CURRENT").filePath)
        input_DMP.value = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\26_Aktualizace_3D_dat\01_Developement\gis\26_Aktualizace_3D_dat\26_Aktualizace_3D_dat.gdb\sumavska_test_dmp"
        # output_PolyZ_workspace.filter.list = ["Local Database"]

        params = [log_file_path, input_DMP, input_PolygonZ_geometery]

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



def check_flying_buildings(input_fc:str, ground_dmr:str, workspace:str = None) -> None:
    ''' Updates values for DTM_diff  a DTM_diff_val. Checks if feature is under or over specified terrain.'''
    log_it(f'-'*15, 'info', __name__)
    log_it(f'Updating featureclasses with height attributes.', 'info', __name__)
   
    # cols = ['RIMSA_VYSKA', 'MIN', 'MAX','DTM_diff_min_max_flatness', 'DTM_diff_max_info', 'ID_SEG','DTM_diff_min_info','DTM_diff_min','DTM_diff_max']
    cols = ['SHAPE@', 'ID_PLO','RIMSA_VYSKA', 'MIN','MAX', 'DTM_diff_min', 'DTM_diff_max', 'AVG_height_of_verts']
    bad_seg_ids = []
    sql_expression = "PLOCHA_KOD IN (3, 2)"




    with arcpy.da.UpdateCursor(input_fc, cols, where_clause=sql_expression) as cursor:
        for row in cursor:
            attrs = [att for att in row]

            polygon = row[0]



            z_vals = []
            for part in polygon:
                for point in part:
                    x, y, z = point.X, point.Y, point.Z
                    z_vals.append(z)
                    log_it(f"X: {x}, Y: {y}, Z: {z}", 'info', __name__)
                z_mean = sum(z_vals) / len(z_vals)
                row[-1] = z_mean

            cursor.updateRow(row)

            row[-2] = row[4] - row[-1]  

            cursor.updateRow(row)




    # with arcpy.da.UpdateCursor(input_fc, cols, where_clause=sql_expression) as cur:
    #     for row in cur:
    #         atrs = [attr for attr in row]
    #         dtm_diff_min= row[0] - row[1]
    #         dtm_diff_max = row[0] - row[2]
    #         row[-2] = dtm_diff_min
    #         row[-1] = dtm_diff_max
    #         log_it(f'{row[0]}, {row[1]}, {row[2]}, {row[3]}, {row[4]}', 'info', __name__)
            
            # if dtm_diff_min > 0:
            #     row[-3] = 'PATA_SEG_VYSKA je nad DTM'
            # elif dtm_diff_min < 0:
            #     row[-3] = 'PATA_SEG_VYSKA je pod DTM'
            # else:
            #     row[-3] = 'PATA_SEG_VYSKA odpovida DTM'


            # if dtm_diff_max >= 0:
            #     # log_it(f'{dtm_diff_max}', 'info', __name__)
            #     row[-1] = dtm_diff_max
                # row[3] = row[2] -  row[1]
                # if dtm_diff_max >= 0.5:
                #     bad_seg_ids.append(int(row[5]))

        
            # if dtm_diff_max > 0:
            #     row[4] = 'Celý segment je nad terénem'
            # elif dtm_diff_max == 0:
            #     row[4] = 'Segment sedí na terénu alespoň jedním bodem'
            # else:
            #     # momentálně není možné
            #     row[4] == 'Segment je pod terénem'    
            

            # cur.updateRow(row)
    
    # log_it(f'Checking {input_fc}...', 'info', __name__)
    # log_it(f'Všechny body podstavy segmentu jsou výše nežli 0.5 m nad DMT ID_SEG: {bad_seg_ids}', 'warning', __name__)



def check_tables_and_fields(fc: str, zonal_stats_table_name: str, key_field: str, workspace: str, input_dmp) -> None:
    '''Checks if in specified workspace exists a table or fields in existing fc if not creates them.'''
    arcpy.env.workspace = workspace
    out_table = os.path.join(workspace, zonal_stats_table_name)

    if not tableExists(zonal_stats_table_name):
        log_it('Creating new zonal table...', 'info', __name__)
        sql_expression = "PLOCHA_KOD IN (3, 2)"
        building_roofs = arcpy.management.SelectLayerByAttribute(fc, "NEW_SELECTION", sql_expression)

        log_it(f'{out_table}', 'info', __name__)
        log_it('Creating Zonal statistic table...', 'info', __name__)
        arcpy.sa.ZonalStatisticsAsTable(building_roofs, key_field, input_dmp, out_table, statistics_type='MIN_MAX_MEAN')
    else:
        log_it(f'Zonal Statistics for given {fc} in {workspace} were already calculated if you wish to recalculate them choose another output workspace', 'info', __name__)

    if not fieldExists(fc, 'MIN') and not fieldExists(fc, 'MAX'):
        arcpy.management.JoinField(fc, key_field, out_table, key_field, 'MIN')
        arcpy.management.JoinField(fc, key_field, out_table, key_field, 'MAX')
        arcpy.management.AddField(fc, 'AVG_height_of_verts', 'DOUBLE')
        arcpy.management.AddField(fc, 'DTM_diff_min', 'DOUBLE')
        arcpy.management.AddField(fc, 'DTM_diff_min_info', 'TEXT')
        arcpy.management.AddField(fc, 'DTM_diff_max', 'DOUBLE')
        arcpy.management.AddField(fc, 'DTM_diff_max_info', 'TEXT')
        arcpy.management.AddField(fc, 'DTM_diff_min_max_flatness', 'DOUBLE')
        
        log_it(f'Required fields were created in {fc}', 'info', __name__)
    else:
        log_it(f'Field MIN and MAX already exists in {fc}. Fields MIN, MAX wont be joined from ZonalTable', 'info', __name__)



def main(log_dir_path: str, input_DMP: str, input_polygonZ_geometry: str, *args) -> None:
    '''
    Main runtime.
    '''
 
    arcpy.CheckOutExtension("Spatial")

    # setup file logging
    init_logging(log_dir_path)


    log_it(f'{input_polygonZ_geometry}', 'info', __name__)
    log_it(f'{type(input_polygonZ_geometry)}', 'info', __name__)
    log_it(f'{arcpy.env.workspace}', 'info', __name__)

    key_field = 'OBJECTID'
    output_fc_name = input_polygonZ_geometry
    zonal_stats_table_name = f'{output_fc_name}_zonal_stat_base'
    check_tables_and_fields(output_fc_name, zonal_stats_table_name, key_field, arcpy.env.workspace, input_DMP)


    clear_selection(output_fc_name)
    check_flying_buildings(output_fc_name, input_DMP, arcpy.env.workspace)

##################################################
############ Run the tool from IDE ###############

# fake parametry

# imtpw = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\02_Input_Data\TOPGIS_2021\Lokalita_21_2021_08_10"
# imtpw = r"I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\02_Input_Data\TopGIS_clean\Lokalita_43_2022_08_11"
# raster = r'I:\01_Data\02_Prirodni_pomery\04_Vyskopis\Brno\DMR_DMT\TOPGIS\2019\04_GIS\rastr\rastr\DMT2019\DTM_2019_L_025m.tif'
# omptw = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\01_Developement\02_Output\new_output_workspaces\polyZ_workspace.gdb'
# log_file_path = r'I:\04_Hall_of_Fame\11_Honza_H\00_Projekty\12_3D_model_validation_refactoring\01_Developement\02_Output\test_logs'  # bude parameter
# main(log_dir_path=log_file_path, input_DMP=raster, location_root_folder_paths=imtpw, path_to_copy_analysis_workspace=omptw)

###################################################