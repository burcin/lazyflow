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

"""
This module implements the basic flow graph
of the lazyflow module.

Basic usage example:

---
import numpy
import lazyflow.graph
from lazyflow.operators.operators import  OpArrayPiper


g = lazyflow.graph.Graph()

operator1 = OpArrayPiper(graph=g)
operator2 = OpArrayPiper(graph=g)

operator1.inputs["Input"].setValue(numpy.zeros((10,20,30), dtype=numpy.uint8))

operator2.inputs["Input"].connect(operator1.outputs["Output"])

result = operator2.outputs["Output"][:].wait()
---

"""

#Python
import sys
import copy
import functools
import collections
import itertools
import threading
import logging

logger = logging.getLogger(__name__)

#third-party
import psutil
if (int(psutil.__version__.split(".")[0]) < 1 and
    int(psutil.__version__.split(".")[1]) < 3):
    msg = "Lazyflow: Please install a psutil python module version"\
          " of at least >= 0.3.0" 
    sys.stderr.write(msg)
    logger.error( msg )
    sys.exit(1)

#SciPy
import numpy

#lazyflow
from lazyflow import rtype
from lazyflow.request import Request
from lazyflow.stype import ArrayLike
from lazyflow.utility import slicingtools, Tracer, OrderedSignal, Singleton
from lazyflow.slot import InputSlot, OutputSlot, Slot
from lazyflow.operator import Operator, InputDict, OutputDict, OperatorMetaClass
from lazyflow.operatorWrapper import OperatorWrapper
from lazyflow.metaDict import MetaDict

class Graph(object):
    """
    A Graph instance is shared by all connected operators and contains any 
    bookkeeping or globally accessible state needed by all operators/slots in the graph.
    """
    def __init__(self):
        self._setup_depth = 0
        self._sig_setup_complete = None
        self._lock = threading.Lock()

    def call_when_setup_finished(self, fn):
        # The graph is considered in "setup" mode if any slot is executing a function that affects the state of the graph.
        # See slot.py for details.  Such operations typically invoke a chain reaction of setup operations.
        # The entire setup is "finished" when the initially invoked setup function returns.
        """
        See comment above.
        
        If the graph is not in the middle of a setup operation as described above,
        immediately call the given callback.  Otherwise, save the callback and 
        execute it when the setup operation completes.  The callback is executed 
        only once, and then it is discarded.
        """
        if self._setup_depth == 0:
            # Not setting up.  Call immediately
            fn()
        else:
            # Subscribe to the next completion.
            self._sig_setup_complete.subscribe(fn)
    
    class SetupDepthContext(object):
        """
        A context manager to manage the "depth" of a setup operation.
        When the depth reaches zero, the graph's `_sig_setup_complete` signal is emitted.
        """
        def __init__(self, g):
            self._graph = g
            
        def __enter__(self):
            if self._graph:
                with self._graph._lock:
                    if self._graph._setup_depth == 0:
                        self._graph._sig_setup_complete = OrderedSignal()
                    self._graph._setup_depth += 1

        def __exit__(self, *args):
            if self._graph:
                sig_setup_complete = None
                with self._graph._lock:
                    self._graph._setup_depth -= 1
                    if self._graph._setup_depth == 0:
                        sig_setup_complete = self._graph._sig_setup_complete
                        # Reset.
                        self._graph._sig_setup_complete = None
                if sig_setup_complete:
                    sig_setup_complete()
