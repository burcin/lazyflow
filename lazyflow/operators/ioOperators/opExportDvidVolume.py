# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Copyright 2011-2014, the ilastik developers
import httplib
import contextlib

import vigra

import pydvid

from lazyflow.graph import Operator, InputSlot
from lazyflow.utility import OrderedSignal
from lazyflow.roi import roiFromShape

import logging
logger = logging.getLogger(__name__)

class OpExportDvidVolume(Operator):
    Input = InputSlot()
    NodeDataUrl = InputSlot() # Should be a url of the form http://<hostname>[:<port>]/api/node/<uuid>/<dataname>
    
    def __init__(self, transpose_axes, *args, **kwargs):
        super(OpExportDvidVolume, self).__init__(*args, **kwargs)
        self.progressSignal = OrderedSignal()
        self._transpose_axes = transpose_axes

    # No output slots...
    def setupOutputs(self):
        if self._transpose_axes:
            assert self.Input.meta.axistags.channelIndex == len(self.Input.meta.axistags)-1
        else:
            assert self.Input.meta.axistags.channelIndex == 0
                    
    def execute(self, slot, subindex, roi, result): pass 
    def propagateDirty(self, slot, subindex, roi): pass

    def run_export(self):
        self.progressSignal(0)

        url = self.NodeDataUrl.value
        url_path = url.split('://')[1]
        hostname, api, node, uuid, dataname = url_path.split('/')
        assert api == 'api'
        assert node == 'node'
        
        # Request the data
        axiskeys = self.Input.meta.getAxisKeys()
        data = self.Input[:].wait()
        
        if self._transpose_axes:
            data = data.transpose()
            axiskeys = reversed(axiskeys)
        
        axiskeys = "".join( axiskeys )
        
        # FIXME: We assume the dataset needs to be created first.
        #        If it already existed, this (presumably) causes an error on the DVID side.
        metadata = pydvid.voxels.VoxelsMetadata.create_default_metadata( data.shape, data.dtype.type, axiskeys, 0.0, "" )

        connection = httplib.HTTPConnection( hostname )
        with contextlib.closing( connection ):
            self.progressSignal(5)
            pydvid.voxels.create_new(connection, uuid, dataname, metadata)
    
            client = pydvid.voxels.VoxelsAccessor( connection, uuid, dataname )
            
            # For now, we send the whole darn thing at once.
            # TODO: Stream it over in blocks...
            
            # Send it to dvid
            start, stop = roiFromShape(data.shape)
            client.post_ndarray( start, stop, data )
        
        self.progressSignal(100)
    
        