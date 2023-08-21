import os
from typing import List

def get_gdb_path_3D_geoms(location_folder: str, geometry: str) -> str:
    '''
    Gets path to GDB containing desired data type (3D geometry). 
    '''
    for subdir, dirs, files in os.walk(location_folder):
        if geometry == 'Multipatch':
            if subdir.endswith('_multipatch.gdb'):
                return subdir
        elif geometry == 'PolygonZ':
            if subdir.endswith('.gdb') and '_multipatch' not in subdir:
                return subdir
        else:
            print('Geometry wasnt specified correctly.')



def get_gdb_path_3D_geoms_multiple(locality_folder_path: str, desired_geoms: List[str], tool_name) -> List:
    '''
    Returns list with paths to desired geodatabases (PolygonZ, Multipatch).
    '''
    gdb_paths = []

    for geom in desired_geoms:
        gdb_paths.append(get_gdb_path_3D_geoms(locality_folder_path, geom)) 
    
    return gdb_paths