# hdfattributemodel.py --- 
# 
# Filename: hdfattributemodel.py
# Description: 
# Author: subha
# Maintainer: 
# Created: Fri Jul 31 20:48:19 2015 (-0400)
# Version: 
# Last-Updated: Thu Sep 17 15:16:32 2015 (-0400)
#           By: Subhasis Ray
#     Update #: 121
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# 
# 
# 

# Change log:
# 
# 
# 
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street, Fifth
# Floor, Boston, MA 02110-1301, USA.
# 
# 

# Code:

import numpy as np
import h5py as h5
from pyqtgraph import QtCore

class HDFAttributeModel(QtCore.QAbstractTableModel):
    """Model class to handle HDF5 attributes of an HDF5 object"""
    columns = ['Attribute name', 'Value', 'Type']
    def __init__(self, node, parent=None):
        """`node` is an HDF5 object"""
        super(HDFAttributeModel, self).__init__(parent=parent)
        self.node = node
        
    def rowCount(self, index):
        return len(self.node.attrs)

    def columnCount(self, index):
        return len(HDFAttributeModel.columns)

    def headerData(self, section, orientation, role):        
        if role != QtCore.Qt.DisplayRole or orientation == QtCore.Qt.Vertical:
            return None
        return HDFAttributeModel.columns[section]

    def data(self, index, role):
        """For tooltips return the data type of the attribute value.  For
        display role, return attribute name (key)for column 0 and
        value for column 1.

        """
        if (not index.isValid()) or \
           (role not in (QtCore.Qt.ToolTipRole, QtCore.Qt.DisplayRole)):
            return None              
        for ii, name in enumerate(self.node.attrs):
            if ii == index.row():
                break
        if role == QtCore.Qt.ToolTipRole:
            value = self.node.attrs[name]
            # if isinstance(value, bytes) or isinstance(value, str):
            #     return 'string: scalar'
            if isinstance(value, np.ndarray):
                return '{}: {}'.format(value.dtype, value.shape)
            elif isinstance(value, h5.Reference):
                if value.typecode == 0:
                    return 'ObjectRef: scalar'
                else:
                    return 'RegionRef: scalar'
            return '{}: scalar'.format(type(value).__name__)
        elif role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return name
            try:
                value = self.node.attrs[name]
            except OSError:
                print('Failed to read attribute', name, 'of', self.node)
                return
            if index.column() == 1:                
                # in Python 3 we have to decode the bytes to get
                # string representation without leading 'b'. However,
                # on second thought, it is not worth converting the
                # strings - for large datasets it will be slow, and if
                # we do the conversion for attributes but not for
                # datasets it gets confusing for the user.
                return str(value)
                
                # if isinstance(value, bytes):
                #     return value.decode('utf-8')
                # elif isinstance(value, np.ndarray) and value.dtype.type == np.string_:
                #     return str([entry.decode('utf-8') for entry in value])                    
                # return str(value)                
            elif index.column() == 2:
                return type(value).__name__                
        return None


if __name__ == '__main__':
    import sys
    import h5py as h5
    app = QtGui.QApplication(sys.argv)
    window = QMainWindow()
    tabview = QtGui.QTableView(window)
    fd = h5.File('poolroom.h5')
    model = HDFAttributeModel(fd)
    tabview.setModel(model)
    widget = QtGui.QWidget(window)
    widget.setLayout(QHBoxLayout())
    widget.layout().addWidget(tabview)
    window.setCentralWidget(widget)
    window.show()
    sys.exit(app.exec_())


# 
# hdfattributemodel.py ends here
