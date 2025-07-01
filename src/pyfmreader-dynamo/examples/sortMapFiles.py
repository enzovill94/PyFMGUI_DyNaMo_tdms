#%%
import sys
import os

# # Add your project src to the path if needed
sys.path.append("/Users/evillz/Github/GUI_dev_YS_LV/src/pyfmreader-dynamo/src")

# from pyfmreader.jpk.loadjpkimg import loadJPKimg
from pyfmreader.ps_nex.loadpsneximg import loadPSNEXimg, createPSNEXimgcsv
from pyfmreader.ps_nex.loadpsnexMaps import checkMapFileNULL
from pyfmreader import loadfile
import matplotlib.pyplot as plt


psnex_map_path = '/Volumes/SSK Drive /2025_11_06'
scanFolder = True

if scanFolder :
    df_point_log = checkMapFileNULL(psnex_map_path)

# # Load the file using your project's loader

# UFF = loadfile(psnex_map_file)


# #%%
# # Debug: print some metadata
# # print("File metadata:", UFF.filemetadata)

# # system_{ax}_piezo_sensitivity_(nm/V)

# x_piezo_sensitivity_nmV = UFF.filemetadata.get('system_X_piezo_sensitivity_(nm/V)')
# y_piezo_sensitivity_nmV = UFF.filemetadata.get('system_Y_piezo_sensitivity_(nm/V)')

# # Needs to be finilized
# UFF.filemetadata['isFV'] = True
# UFF.filemetadata['num_x_pixels'] = 32
# UFF.filemetadata['num_y_pixels'] = 32
# # UFF.filemetadata['scan_size_x_um'] = x_piezo_sensitivity_nmV * 1e-03 * (UFF.filemetadata['num_x_pixels']-1)
# # UFF.filemetadata['scan_size_y_um'] = y_piezo_sensitivity_nmV * UFF.filemetadata['num_y_pixels']
# UFF.filemetadata['scan_size_x_um'] = 0
# UFF.filemetadata['scan_size_y_um'] = 0
# # #%%
# # #%%
# # # Call the function and print results
# piezoImage, data = loadPSNEXimg(UFF)
# # csv_file_path, data = createPSNEXimgcsv(UFF)
# print (piezoImage.shape)
# # data
# print("Loaded channels:", list(data.keys()))
# for channel, img in data.items():
#     print(f"Channel: {channel}, shape: {img.shape}, dtype: {img.dtype}")
# print("Piezo image shape:", piezoImage.shape)

# if __name__ == "__main__":
#     plt.figure(figsize=(8, 6))
#     plt.imshow(piezoImage, cmap='viridis', aspect='auto', origin='lower')
#     plt.colorbar(label='Z Height (um)')
#     plt.title('Piezo Image Heatmap')
#     plt.xlabel('X Pixels')
#     plt.ylabel('Y Pixels')
#     plt.show(block=True)
