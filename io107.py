#!/usr/bin/env python
# *-* coding: utf-8 -*-
# pylint: disable=C0103, C0301
"""
Reads and write 107 format used by TRACZILLA
For both python 2 and python 3
It can read and write both normal and gzipped files. The fname is always the
name of the file without .gz suffix
@authors Ann'Sophie Tissier and Bernard Legras (legras@lmd;ens.fr)
@licence CeCILL-C
"""
from __future__ import absolute_import, division, print_function
from __future__ import unicode_literals
import os
from struct import unpack, pack
from numpy import asarray,amin,amax  # @UnresolvedImport
import gzip

################################
def readpart107(hour, part_dir, quiet=False):
    """ readpart107 reads 'part'
    files generated by traczilla routine partout_stc
    data = readpart(hour,dir) reads the part file for hour
    in the directory dir using 107 format
    As the format is common with index files, readpart107 calls
    readidx107. See below for the 107 format.

    A.-S. Tissier/ B. Legras May 2016 : Python version
    """
    #print hour
    hourfile_str = '{:03d}'.format(hour)
    #print hourfile_str
    hourfile_tot = os.path.join(part_dir, "part_" + hourfile_str)
    #print hourfile_tot
    dato = readidx107(hourfile_tot, quiet)
    return dato

######################
def readidx107(fname, quiet=False):
    """ readpart107 reads 'part'
    files generated by traczilla routine partout_stc
    data = readpart(hour,dir) reads the part file for hour
    in the directory dir and returns a structure
    data is a dictionary containing x,y,z,t
    and itra indicating whether the particle is stopped ,or not
    hour is an integer < 1000 and dir a string (not ending by /)
    readpart recognizes format 103

    Description of format 107
    Fortran 32bits binary file is made of records with one control•
    word (32bits=4bytes) at the beginning and teh end of each records
    Binary format is IEEE (not the standard bit-swapped binary format
    on Intel architecture). Programs are compiled with PGF using
    byteswapio option

    record 1: (3*int32)
        lhead: number of records of the header, here 3
        outfmt: 107 (format)
        mode: 0, new index file; 1, history file; 2, old index file
    record 2: (int64,2*int32)
        stamp_date: reference date (YYYYMMDDHHmmss)
        itime: output time from the reference date (s)
        step: time step (s)
    record 3: (6*int32)
        numpart: total number of parcels
        nact: number of active parcels
        idx_orgn: index origin
        nact_lastO
        nact_lastNM
        nact_lastNH
    record 4: (nact*int32)
        flag: flag containing informations about data source•
        and ir_start format
    record 5: (nact*int32)
        ir_start: start time of the parcels,
        usually in s from stamp_date
    record 6: (nact*float32)
        x: longitudes of the parcels (degree)
    record 7: (nact*float32)
        y: latitudes of the parcels (degrees)
    record 8: (nact*float32)
        p: pressures of the parcels (Pa)
    record 9: (nact*float32)
        t: temperatures of the parcels (K)
    record 10: (nact*int32)
        idx_back: mode 0: indexes of old parcels in the list at•
                          stamp_date -12h, undefined for new parcels
                  mode 1: index of active parcels among the list of•
                          parcels at stamp_date t
                  mode 2: index of active parcels among the lists of
                          parcels at time t-12h, segmented
                          with first old parcels at time t-12h, then
                          new parcels at time t-12h (both with their idx_orgn)

    A.-S. Tissier/ B. Legras May 2016 : Python version
    """

    # Initialization :
    data = {}

    # Open the binary file :
    print('open '+fname)
    try:
        fid = open(fname, 'rb')
    except IOError:
        if not quiet: print("try gzipped version")
        fid=gzip.open(fname+".gz",'rb')

    # Get lhead, outnfmt (format) and mode (=0, index_file; =1, historical file)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['lhead'] = unpack('>l', fid.read(4))[0]
    data['outnfmt'] = unpack('>l', fid.read(4))[0]
    data['mode'] = unpack('>l', fid.read(4))[0]
    fid.read(4)  # last fortran record word

    # Check that the format matches :
    if data['outnfmt'] != 107:
        if not quiet: print(data['lhead'], data['outnfmt'], data['mode'])
        raise ValueError('UNKNOWN FILE FORMAT')

    # Get stamp_date (Format YYYYMMDDHHmmss), itime (output time)
    # and step (time step)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['stamp_date'] = unpack('>q', fid.read(8))[0]
    data['itime'] = unpack('>l', fid.read(4))[0]
    data['step'] = unpack('>l', fid.read(4))[0]
    fid.read(4)  # last fortran record word

    if not quiet: print(data['stamp_date'], data['itime'], data['step'])

    # Get numpart (number of parcels), nact (number of active parcels)
    # and idx_orgn (index of first parcel)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['numpart'] = unpack('>l', fid.read(4))[0]
    data['nact'] = unpack('>l', fid.read(4))[0]
    data['idx_orgn'] = unpack('>l', fid.read(4))[0]
    data['nact_lastO'] = unpack('>l', fid.read(4))[0]
    data['nact_lastNM'] = unpack('>l', fid.read(4))[0]
    data['nact_lastNH'] = unpack('>l', fid.read(4))[0]
    fid.read(4)  # last fortran record word
    if not quiet:
        print(data['numpart'], data['nact'], data['idx_orgn'])
        print(data['nact_lastO'],data['nact_lastNM'],data['nact_lastNH'])

    # case provided to read part_000 of M10
    if data['nact']==0:
        print("empty trajectory set")
        data['flag']=[]
        data['ir_start']=[]
        data['x']=[]
        data['y']=[]
        data['p']=[]
        data['t']=[]
        data['idx_back']=[]
        fid.close()
        return data
    # Get flag
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['flag'] = asarray(unpack('>'+str(data['nact'])+'l', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('flag', data['flag'][0], data['flag'][data['nact']-1])

    # Get ir_start (launch time)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['ir_start'] = asarray(unpack('>'+str(data['nact'])+'l', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    #print('ir', data['ir_start'][0], data['ir_start'][data['nact']-1])
    if not quiet: print('ir', amin(data['ir_start'])/86400., amax(data['ir_start'])/86400.)

    # Get longitude (in degree)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['x'] = asarray(unpack('>'+str(data['nact'])+'f', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('x', amin(data['x']),amax(data['x']))

    # Get latitude (in degree)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['y'] = asarray(unpack('>'+str(data['nact'])+'f', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('y', amin(data['y']),amax(data['y']))

    # Get the pressure (in Pascal)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['p'] = asarray(unpack('>'+str(data['nact'])+'f', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('p', amin(data['p']),amax(data['p']))

    # Get the temperature (in Kelvin)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['t'] = asarray(unpack('>'+str(data['nact'])+'f', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('t', amin(data['t']),amax(data['t']))

    # Get idx_back
    # (mode 0 : index of old parcels in the list at stamp_date -12h;
    # undefined for new parcels)
    # (mode 1 : index of current active parcels among the list of parcels at
    # stamp_date)
    fid.read(4)  # first fortran record word (normaly 4 characters, char)
    data['idx_back'] = asarray(unpack('>'+str(data['nact'])+'l', fid.read(data['nact']*4)))
    fid.read(4)  # last fortran record word
    if not quiet: print('idx', data['idx_back'][0], data['idx_back'][data['nact']-1])

    # decode flag (commented out as not needed and slowing the reading)
    #data['sat'] = asarray(data['flag']) & 0xF
    #data['mod'] = (asarray(data['flag']) & 0x10) >> 4
    #data['time_style'] = (asarray(data['flag']) & 0x20) >> 5
    #data['vert_coord'] = (asarray(data['flag']) & 0x40) >> 6
    #data['source_region'] = (asarray(data['flag']) & 0x1F80) >> 7
    #print 'vert_coord', data['vert_coord'][0], data['vert_coord'][data['nact']-1]

    # Close the binary file
    fid.close()

    return data

#############################
def writeidx107(fname, data,cmp=False):
    """ writeidx107 writes file under 107 format
    usage: writeidx107(fname,data)
    data is a dictionary containing the data

    Description of format 107
    Fortran 32bits binary file is made of records with one control
    word (32bits=4bytes) at the beginning and the end of each records
    containing the lenght of the record in 32bit words
    Binary format is IEEE (not the standard bit-swapped binary format
    on Intel architecture). Fortran programs compiled with pgi and the
    -byteswapio option

    A.-S. Tissier/ B. Legras May 2016 : Python version
    """

    # Open the binary file:
    if cmp:
        fid=gzip.open(fname,'wb')
    else:
        fid = open(fname, 'wb')

    if data['lhead'] != 3:
        print('!!!!!')
        print('lhead not equal to 3 : change lhead')
        data['lhead'] = 3

    if data['outnfmt'] != 107:
        raise ValueError('Problem with format')

    # Write lhed, outfmt (format) and mode(=0, index_file; =1, historical file)
    cwd = pack('>l', 3*4)
    rec = pack('>3l', data['lhead'], data['outnfmt'], data['mode'])
    fid.write(cwd+rec+cwd)

    # Write stamp_date (Format YYYYMMDDHHmmss), itime (output time)
    # and step (time step)
    cwd = pack('>l', 4*4)
    rec = pack('>q', data['stamp_date'])+pack('>2l', data['itime'], data['step'])
    fid.write(cwd+rec+cwd)

    # Write numpart (number of parcels), nact (number of active parcels)
    # and idx_orgn (index of first parcel)
    cwd = pack('>l', 6*4)
    rec = pack('>6l', data['numpart'], data['nact'], data['idx_orgn'],
           data['nact_lastO'],data['nact_lastNM'],data['nact_lastNH'])
    fid.write(cwd+rec+cwd)

    # Write flag
    cwd = pack('>l', data['nact']*4)
    rec = pack('>'+str(data['nact'])+'l', *data['flag'])
    fid.write(cwd+rec+cwd)

    # Write ir_start (launch time)
    rec = pack('>'+str(data['nact'])+'l', *data['ir_start'])
    fid.write(cwd+rec+cwd)

    # Write longitude (in degree)
    rec = pack('>'+str(data['nact'])+'f', *data['x'])
    fid.write(cwd+rec+cwd)

    # Write latitude (in degree)
    rec = pack('>'+str(data['nact'])+'f', *data['y'])
    fid.write(cwd+rec+cwd)

    # Write the pressure (in Pascal)
    rec = pack('>'+str(data['nact'])+'f', *data['p'])
    fid.write(cwd+rec+cwd)

    # Write the temperature (in Kelvin)
    rec = pack('>'+str(data['nact'])+'f', *data['t'])
    fid.write(cwd+rec+cwd)

    # Write idx_back
    # (mode 0 : index of old parcels in the list at stamp_date -12h;
    # undefined for new parcels)
    # (mode 1 : index of current active parcels among the list of
    # parcels at stamp_date)
    rec = pack('>'+str(data['nact'])+'l', *data['idx_back'])
    fid.write(cwd+rec+cwd)

    # Close the file
    fid.close()

    return
