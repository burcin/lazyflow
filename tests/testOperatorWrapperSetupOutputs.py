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

import time
import random
import threading
from functools import partial
import numpy
import vigra
import lazyflow.graph
from lazyflow.operators.operators import OpArrayCache
from lazyflow.operator import Operator
from lazyflow.slot import InputSlot, OutputSlot
from lazyflow.operatorWrapper import OperatorWrapper

class OpA(Operator):
    input = InputSlot()
    output = OutputSlot()
    
    
    def __init__(self, parent = None):
        Operator.__init__(self, parent)
        self.countSetupOutputs = 0
    
    def setupOutputs(self):
        self.countSetupOutputs += 1
        self.output.meta.shape = self.input.meta.shape
        self.output.meta.dtype = self.input.meta.dtype
        
    
    def execute(self, slot, subindex, roi, result):
        pass

    def propagateDirty(self, slot, subindex, roi):
        pass

class TestOperatorWrapperSetupOutputs(object):
    
    def test(self):
        # test wether setupOutputs is only called once
        # for each inner operator, even when resizing the slot
        # more then one time
        graph = lazyflow.graph.Graph()
        opaw = OperatorWrapper(OpArrayCache, graph = graph)
        opbw = OperatorWrapper(OpA, graph = graph)
        
        opbw.input.connect(opaw.Output)
        
        array = numpy.ndarray((10,20), dtype = numpy.float32)
        opaw.Input.resize(1)
        opaw.Input[0].setValue(array)
        
        assert opbw.innerOperators[0].countSetupOutputs == 1

        opaw.Input.resize(2)
        opaw.Input[1].setValue(array)

        assert opbw.innerOperators[0].countSetupOutputs == 1

        
if __name__ == "__main__":
    import sys
    import nose
    sys.argv.append("--nocapture")    # Don't steal stdout.  Show it on the console as usual.
    sys.argv.append("--nologcapture") # Don't set the logging level to DEBUG.  Leave it alone.
    ret = nose.run(defaultTest=__file__)
    if not ret: sys.exit(1)
