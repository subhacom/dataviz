# hdftreewidget.py --- 
# 
# Filename: hdftreewidget.py
# Description: 
# Author: subha
# Maintainer: 
# Created: Fri Jul 24 20:54:11 2015 (-0400)
# Version: 
# Last-Updated: Sat Aug  8 20:20:42 2015 (-0400)
#           By: subha
#     Update #: 239
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
"""Defines class to display HDF5 file tree.

"""

from collections import defaultdict

from PyQt5.QtCore import (Qt, pyqtSignal)
from PyQt5.QtWidgets import (QTreeView, QWidget)

from hdftreemodel import HDFTreeModel
from hdfdatasetwidget import HDFDatasetWidget
from hdfattributewidget import HDFAttributeWidget

class HDFTreeWidget(QTreeView):
    """Convenience class to display HDF file trees. 

    HDFTreeWidget wraps an HDFTreeModel and displays it.
    In addition it allows opening multiple files from a list.

    Signals
    -------

    datasetWidgetCreated(QWidget): emitted by createDatasetWidget slot
    after a new dataset widget is created with the created
    widget. This provides a way to send it back to the DataViz widget
    (top level widget and caller of the slot) for incorporation into
    the main window.

    datasetWidgetClosed(QWidget): this is emitted for each of the
    widgets showing datasets under a given file tree when the file is
    closed. This allows the toplevel widget to close the corresponding
    mdi child window.

    attributeWidgetCreated(QWidget): same as datasetWidgetCreated but
    for the widget displaying HDF5 attributes.

    attributeWidgetClosed(QWidget): same as datasetWidgetClosed but
    for the widget displaying HDF5 attributes.

    """
    datasetWidgetCreated = pyqtSignal(QWidget)
    datasetWidgetClosed = pyqtSignal(QWidget)
    attributeWidgetCreated = pyqtSignal(QWidget)
    attributeWidgetClosed = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        model = HDFTreeModel([])
        self.setModel(model)
        self.openDatasetWidgets = defaultdict(set)
        self.openAttributeWidgets = defaultdict(set)
        

    def openFiles(self, files):
        """Open the files listed in argument.

        files: list of file paths. For example, output of
               QFileDialog::getOpenFileNames

        """
        for fname in files:
            self.model().openFile(fname)
        
    def closeFiles(self):
        """Close the files selected in the model.

        If there are datasets in the file that are being displayed via
        a `HDFDatasetWidget`, then it emits a datasetWidgetClosed
        signal with the HDFDatasetWidget as a parameter for each of
        them. Same for `HDFAttributeWidget`s.

        """
        indices = self.selectedIndexes()
        for index in indices:
            item = self.model().getItem(index)            
            filename = item.h5node.file.filename
            if self.model().closeFile(index):
                for datasetWidget in self.openDatasetWidgets[filename]:
                    self.datasetWidgetClosed.emit(datasetWidget)
                self.openDatasetWidgets[filename].clear()
                for attributeWidget in self.openAttributeWidgets[filename]:
                    self.attributeWidgetClosed.emit(attributeWidget)
                self.openAttributeWidgets[filename].clear()

    def createDatasetWidget(self, index):
        """Returns a dataset widget for specified index.

        Emits datasetWidgetCreated(newWidget).

        """
        item = self.model().getItem(index)
        if (item is not None) and item.isDataset():
            # TODO maybe avoid duplicate windows for a dataset
            widget = HDFDatasetWidget(dataset=item.h5node)            
            self.openDatasetWidgets[item.h5node.file.filename].add(widget)
            self.datasetWidgetCreated.emit(widget)
            
    def createAttributeWidget(self, index):
        """Creates an attribute widget for specified index.

        Emits attributeWidgetCreated(newWidget)
        """
        item = self.model().getItem(index)
        if item is not None:
            # TODO maybe avoid duplicate windows for a attributes of a
            # single node
            widget = HDFAttributeWidget(node=item.h5node)            
            self.openAttributeWidgets[item.h5node.file.filename].add(widget)
            self.attributeWidgetCreated.emit(widget)

    def showAttributes(self):
        """Create an attribute widget for currentItem"""
        self.createAttributeWidget(self.currentIndex())

    def showDataset(self):
        """Create dataset widget for currentItem"""
        self.createDatasetWidget(self.currentIndex())


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import (QApplication, QMainWindow)
    app = QApplication(sys.argv)
    window = QMainWindow()
    widget = HDFTreeWidget()
    window.setCentralWidget(widget)
    widget.openFiles(['poolroom.h5'])
    window.show()
    sys.exit(app.exec_())

# 
# hdftreewidget.py ends here