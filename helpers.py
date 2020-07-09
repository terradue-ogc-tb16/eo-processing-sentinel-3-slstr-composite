import os
import sys
sys.path.append(os.path.join(os.environ['PREFIX'], 'conda-otb/lib/python'))
os.environ['OTB_APPLICATION_PATH'] = os.path.join(os.environ['PREFIX'], 'conda-otb/lib/otb/applications')
os.environ['GDAL_DATA'] =  os.path.join(os.environ['PREFIX'], 'share/gdal')
os.environ['PROJ_LIB'] = os.path.join(os.environ['PREFIX'], 'share/proj')
os.environ['GPT_BIN'] = os.path.join(os.environ['PREFIX'], 'snap/bin/gpt')
import otbApplication

import gdal
import numpy as np
import math
from py_snap_helpers import *

def get_slstr_nodata_mask(classif_flags):
    
    # 'unfilled_pixel': 128
    
    b1 = int(math.log(128, 2))
    b2 = b1
    
    return _capture_bits(classif_flags.astype(np.int64), b1, b2)

def get_slstr_confidence_mask(slstr_confidence, classif_flags):
    
    pixel_classif_flags = {'coastline': 1,
                           'cosmetic': 256,
                             'day': 1024,
                             'duplicate': 512,
                             'inland_water': 16,
                             'land': 8,
                             'ocean': 2,
                             'snow': 8192,
                             'spare': 64,
                             'summary_cloud': 16384,
                             'summary_pointing': 32768,
                             'sun_glint': 4096,
                             'tidal': 4,
                             'twilight': 2048,
                             'unfilled': 32}
    
    
    b1 = int(math.log(pixel_classif_flags[slstr_confidence], 2))
    b2 = b1
    
    return _capture_bits(classif_flags.astype(np.int64), b1, b2)

def get_slstr_mask(slstr_cloud, classif_flags):
    
    pixel_classif_flags = {'11_12_view_difference': 2048,
                           '11_spatial_coherence': 64,
                           '1_37_threshold': 2,
                           '1_6_large_histogram': 8,
                           '1_6_small_histogram': 4,
                           '2_25_large_histogram': 32,
                           '2_25_small_histogram': 16,
                           '3_7_11_view_difference': 4096,
                           'fog_low_stratus': 1024,
                           'gross_cloud': 128,
                           'medium_high': 512,
                           'spare': 16384,
                           'thermal_histogram': 8192,
                           'thin_cirrus': 256,
                           'visible': 1}
    
    
    b1 = int(math.log(pixel_classif_flags[slstr_cloud], 2))
    b2 = b1
    
    return _capture_bits(classif_flags.astype(np.int64), b1, b2)


def _capture_bits(arr, b1, b2):
    
    width_int = int((b1 - b2 + 1) * "1", 2)
 
    return ((arr >> b2) & width_int).astype('uint8')

def export_s3(bands):

    ds = gdal.Open(bands[0])
    
    width = ds.RasterXSize
    height = ds.RasterYSize

    input_geotransform = ds.GetGeoTransform()
    input_georef = ds.GetProjectionRef()
    
    ds = None
    
    driver = gdal.GetDriverByName('GTiff')
    
    output = driver.Create('s3.tif', 
                       width, 
                       height, 
                       len(bands), 
                       gdal.GDT_Float32)

    output.SetGeoTransform(input_geotransform)
    output.SetProjection(input_georef)
    
    for index, band in enumerate(bands):
        print(band)
        temp_ds = gdal.Open(band) 
        
        band_data = temp_ds.GetRasterBand(1).ReadAsArray()
        output.GetRasterBand(index+1).WriteArray(band_data)
        
    output.FlushCache()
    
    output = None
    
    del(output)
    
    return True

def read_s3(bands):

    gdal.UseExceptions()
    
    stack = []
    
    for index, band in enumerate(bands):
        
        temp_ds = gdal.Open(band) 
 
        if not temp_ds:
            raise ValueError()
            
        stack.append(temp_ds.GetRasterBand(1).ReadAsArray())
      
    return np.dstack(stack)


def s3_slstr_proc(operators, **kwargs):
   
    options = dict()
    
    for operator in operators:
            
        print('Getting default values for Operator {}'.format(operator))
        parameters = get_operator_default_parameters(operator)
        
        options[operator] = parameters

    for key, value in kwargs.items():
        
        print('Updating Operator {}'.format(key))
        options[key.replace('_', '-')].update(value)
     
    mygraph = GraphProcessor()
    
    for index, operator in enumerate(operators):
    
        print('Adding Operator {} to graph'.format(operator))
        if index == 0:            
            source_node_id = ''
        
        else:
            source_node_id = operators[index - 1]
       
        mygraph.add_node(operator,
                         operator, 
                         options[operator], source_node_id)
    
    #mygraph.view_graph()
    
    mygraph.run()
    
def s3_rgb_composite(red, green, blue, cloud, confidence, exception, geo_transform, projection_ref, output_name, hfact=5.0):

    rgb_r = np.zeros(red.shape)
    rgb_g = np.zeros(red.shape)
    rgb_b = np.zeros(red.shape)
    
    mask_land = get_slstr_confidence_mask('land', confidence)
    mask_sea = get_slstr_confidence_mask('ocean', confidence)
    
    mask_nodata = get_slstr_nodata_mask(exception)
    
    # original mask
    #mask = (mask_land == 0) | (mask_nodata == 1)
    
    #mask = (mask_land == 0) | (mask_nodata == 1) | (mask_sea == 0)
    mask = (mask_nodata == 1)
    
    mask = ((mask_land == 0) & (mask_sea == 0)) |  (mask_nodata == 1)
    
    rgb_r = np.where(mask,
                     0,
                     red*255).astype(np.uint8)
    
    rgb_g = np.where(mask,
                     0,
                     green*255).astype(np.uint8)
    
    rgb_b = np.where(mask,
                     0,
                     blue*255).astype(np.uint8)
    
    alpha = np.where(mask, 
                     0,
                     255).astype(int)

    # contrast enhancement
    ContrastEnhancement = otbApplication.Registry.CreateApplication('ContrastEnhancement')

    rgb_data = np.dstack([rgb_r, rgb_g, rgb_b])
    
    ContrastEnhancement.SetVectorImageFromNumpyArray('in', rgb_data)
    
    ContrastEnhancement.SetParameterOutputImagePixelType('out', 
                                                         otbApplication.ImagePixelType_uint8)
    ContrastEnhancement.SetParameterFloat('nodata', 0.0)
    ContrastEnhancement.SetParameterFloat('hfact', hfact)
    ContrastEnhancement.SetParameterInt('bins', 256)
    ContrastEnhancement.SetParameterInt('spatial.local.w', 500)
    ContrastEnhancement.SetParameterInt('spatial.local.h', 500)
    ContrastEnhancement.SetParameterString('mode', 'lum')

    ContrastEnhancement.Execute()

    ce_data = ContrastEnhancement.GetVectorImageAsNumpyArray('out')
            
    rgb_r = None
    rgb_g = None
    rgb_b = None

    driver = gdal.GetDriverByName('GTiff')

    output = driver.Create(output_name, 
                           ce_data.shape[1], 
                           ce_data.shape[0], 
                           4, 
                           gdal.GDT_Byte)

    output.SetGeoTransform(geo_transform)
    output.SetProjection(projection_ref)
    output.GetRasterBand(1).WriteArray(ce_data[:,:,0])
    output.GetRasterBand(2).WriteArray(ce_data[:,:,1])
    output.GetRasterBand(3).WriteArray(ce_data[:,:,2])
    output.GetRasterBand(4).WriteArray(alpha)
    
    output.FlushCache()
    
    output = None
    
    del(output)
    
    return rgb_r, rgb_g, rgb_b, alpha