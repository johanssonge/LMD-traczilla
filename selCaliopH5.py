#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exploring the CALIOP database to select orbits and initialize parcels for
backward trajectory calculations on a regular grid.

This is meant to run on ICARE.

Generates part_000 initialization file for a year and a month and two auxiliary files
containing the list of parameters and the catalog of retained orbits.

In the initial version,
- night orbits are retained
- orbits are retained every 3 days in the month (interdate=3)
- levels from 20 to 14 kms are retained with a sampling of ~ 200 m (inlev=3)
- On the horizontal the resolution is about 10 km (ns=2) between 30S (latmin) and
45N (latmax)
 
@author: Bernard Legras
"""
import numpy as np
from datetime import datetime,timedelta
from dateutil.relativedelta import relativedelta
import pickle,gzip
#import matplotlib.pyplot as plt
import os
import h5py
# from pyhdf.SD import SD
# from pyhdf import HDF, VS, V
import glob
# from astropy.time import Time, TimeDelta
import argparse
import io107
import pdb

# Main irectories for aerosol profiles and L1 data
dirAProf = '/scratch/erikj//Data/Calipso/05kmAPro.v4.20'
# dirAProf = '/DATA/LIENS/CALIOP/05kmAPro.v4.20'
#dirL1 = '/DATA/LIENS/CALIOP/CAL_LID_L1.v3.40'

parser = argparse.ArgumentParser()
parser.add_argument("-y","--year",type=int,help="year")
parser.add_argument("-m","--month",type=int,choices=1+np.arange(12),help="month")
#parser.add_argument("-d","--day",type=int,choices=1+np.arange(31),help="day0")

# Default parameters

# End day of the selection
year = 2017
month = 8
day = 1

args = parser.parse_args()
if args.year is not None: year = args.year
if args.month is not None: month = args.month

# Define dates and date interval
endDate = datetime(year, month, 1, 0)
originDate = endDate + relativedelta(months=1)
interdate = 3

# Latitude band
latmin = -30
latmax = 45

# Horizontal spacing in 5 km units
ns = 2 # that is 10 km

# first element below 20 km
l20 = 57
# last element above 14 km
l14 = 156
# The interval is 59.8755 m
intlev = 3
# range of altitudes every 3 points (about 180 m)
altidx = np.arange(l20,l14+1,intlev)
nlev = len(altidx)

altx_ref = pickle.load(open('alx_ref.pkl','rb'))
altx_ref = np.array(altx_ref)

# Create catalog
catalog = {}
catalog_file = 'selCaliop_Calalog'+endDate.strftime('-%b%Y.pkl')
params = {}
params = {'enddate':endDate,'originDate':originDate,'latmin':latmin,'latmax':latmax,
          'ns':ns,'toplev':l20,'botlev':l14,'intlev':intlev,'nlev':nlev,
          'altx':altx_ref,'type':'night','interdate':interdate}
params_file =  'selCaliop_Params'+endDate.strftime('-%b%Y.pkl')

# Generate the dictionary to be used to write part_000
part0 = {}
part0_file = endDate.strftime('part_000-%b%Y')
# Heading data
part0['lhead'] = 3
part0['outnfmt'] = 107
part0['mode'] = 3   # modify that
part0['stamp_date'] = originDate.year*10**10 + originDate.month*10**8 + \
    originDate.day*10**6 + originDate.hour*10**4 + originDate.minute*100
part0['itime'] = 0
part0['step'] = 450
part0['idx_orgn'] = 1
part0['nact_lastO'] = 0
part0['nact_lastNM'] = 0
part0['nact_lastNH'] = 0
part0['flag'] = np.empty(0,dtype=int)
part0['ir_start'] = np.empty(0,dtype=int)
part0['x'] = np.empty(0,dtype=float)
part0['y'] = np.empty(0,dtype=float)
part0['t'] = np.empty(0,dtype=float)
part0['p'] = np.empty(0,dtype=float)
part0['idx_back'] = np.empty(0,dtype=int)
numpart = 0

# Browse dates
# Starts from the last day of the month
date = originDate - timedelta(days=1)

while date >= endDate:
    # Generate names of daily directories
    dirday = os.path.join(dirAProf,date.strftime('%Y/%Y_%m_%d'))
    # List the content of the daily aeorosol directory
    fic = sorted(glob.glob(dirday+'/CAL_LID_L2_05kmAPro-*.h5'))
    print(dirday, len(fic))
    # process all the half-orbits in the aerosol directory
    catalog[date] = {}
    for i in range(len(fic)):
        # pop file
        file = fic.pop()
        #print(file)
        # skip day files
        if ('ZD' in file): continue
        # open file
        try:
#             hdf = SD(file)
#             hh = HDF.HDF(file,HDF.HC.READ)
            h5 = h5py.File(file, 'r')
        except:
            print('H5 Error -> giving up')
            continue
        # Check altitude
        pdb.set_trace()
        meta = hh.vstart().attach('metadata')
        altx = np.array(meta.read()[0][meta.field('Lidar_Data_Altitudes')._idx])
        if np.max((altx - altx_ref)**2)>1.e-5:
            print('ACHTUNG ALARM! NON CONFORM ALTITUDE')
            continue

        # Reads latitudes and longitudes
        lats = hdf.select('Latitude').get()[:,1]
        lons = hdf.select('Longitude').get()[:,1] % 360
        # Read pressure (hPa), temperature (degree C)
        # Conversion to Pa and K
        pres = hdf.select('Pressure').get()[:]
        temp = hdf.select('Temperature').get()[:]
        pres *= 100
        temp += 273.15
        # Read time
        tai = hdf.select('Profile_Time').get()[:,1]
        tt = Time('1993-01-01 00:00:00',scale='tai') + TimeDelta(tai, format='sec')
        utc = tt.utc.datetime
        # Selection of the latitude range and sampling every ns
        sel = np.where((lats>latmin) & (lats<latmax))[0][0:-1:ns]
        if len(sel) == 0: continue
        # Selection of the 1D data
        lats = lats[sel]
        lons = lons[sel]
        utc = utc[sel]
        ir_start = np.array([int((utc[i] - originDate).total_seconds()) for i in range(len(utc))])
        # Selection of the 2D data
        pres = pres[sel,:][:,altidx]
        temp = temp[sel,:][:,altidx]
        # Expand the 1D fields
        ir_start = np.repeat(ir_start,nlev).astype(int)
        lats = np.repeat(lats,nlev)
        lons = np.repeat(lons,nlev)
        # Unidimensionalize the 2D fields
        npart = nlev * len(sel)
        pres = np.reshape(pres,npart)
        temp = np.reshape(temp,npart)

        # Enrich the catalog
        fname = os.path.basename(file)
        # extract orbit
        orbit = fname[35:-4]
        catalog[date][orbit] = {'type':'night','longitudes':[lons[0],lons[-1]],
                                'utc':[utc[0],utc[-1]],'selection':sel,'lensel':len(sel),
                                'npart':npart}
        print(date,orbit,len(sel),npart)
        # fill part0
        idx1 = numpart
        numpart += npart
        part0['x'] = np.append(part0['x'],lons)
        part0['y'] = np.append(part0['y'],lats)
        part0['t'] = np.append(part0['t'],temp)
        part0['p'] = np.append(part0['p'],pres)
        part0['ir_start'] = np.append(part0['ir_start'],ir_start)
        part0['idx_back'] = np.append(part0['idx_back'],np.arange(idx1+1,numpart+1,dtype=int))
        part0['flag'] = np.append(part0['flag'],np.full(npart,127,dtype=int))

    date -= timedelta(days=interdate)
    
# store the dictionary of traces
# final size information
print('End of generation, particles:',numpart)
part0['numpart'] = numpart
part0['nact'] = numpart
params['numpart'] = numpart
params['lensel'] = len(sel)
params['npart'] = npart
with gzip.open(catalog_file,'wb') as f:
    pickle.dump(catalog,f)
with open(params_file,'wb') as f:
    pickle.dump(params,f)
io107.writeidx107(part0_file,part0)
