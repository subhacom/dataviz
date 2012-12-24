# traubdata.py --- 
# 
# Filename: traubdata.py
# Description: 
# Author: 
# Maintainer: 
# Created: Mon Nov 26 20:44:46 2012 (+0530)
# Version: 
# Last-Updated: Mon Dec 24 17:09:54 2012 (+0530)
#           By: subha
#     Update #: 708
# URL: 
# Keywords: 
# Compatibility: 
# 
# 

# Commentary: 
# 
# Class definition to wrap Traub model simulation data
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

import h5py as h5
import os
from operator import itemgetter
from collections import deque
print 'Working directory:', os.getcwd()
from datetime import datetime
import numpy as np
from collections import namedtuple
import random
import igraph as ig
import networkx as nx

import util

# This tuple is to be used for storing cell counts for each file
cellcount_tuple = namedtuple('cellcount',
                             ['SupPyrRS',
                              'SupPyrFRB',
                              'SupBasket',
                              'SupAxoaxonic',
                              'SupLTS',
                              'SpinyStellate',
                              'TuftedIB',
                              'TuftedRS',
                              'DeepBasket',
                              'DeepAxoaxonic',
                              'DeepLTS',
                              'NontuftedRS',
                              'TCR',
                              'nRT'],
                             verbose=False)


class TraubData(object):
    """Wrapper for data files generated by traub model simulation

    members:

    fd: hdf5 file handle associated with this object

    cellcounts: cellcount_tuple containing the counts for each cell type

    timestamp: datetime.datetime timestamp of the simulation

    bg_stimulus: array representing timeseries for background stimulus

    probe_stimulus: array representing timeseries for probe stimulus

    simtime: duration of the simulation
    """
    def __init__(self, fname):
        netfilename = os.path.join(os.path.dirname(fname),
                                   os.path.basename(fname).replace('data_', 'network_').replace('.h5', '.h5.new'))
        self.fdata = None
        self.fnet = None
        try:
            self.fdata = h5.File(fname, 'r')
            self.fnet = h5.File(netfilename)
        except IOError as e:
            print e
            return
        self.__get_cellcounts()
        self.__get_timestamp()        
        self.__get_stimuli()
        self.spikes = dict([(cell, np.asarray(self.fdata['/spikes'][cell])) 
                            for cell in self.fdata['/spikes']])
        self.__get_schedinfo()
        self.__get_synapse()
        self.__get_stimulated_cells()
        self.colordict = util.load_celltype_colors()
        print 'Loaded', fname

    def __del__(self):
        if self.fdata is not None:
            self.fdata.close()
        if self.fnet is not None:
            self.fnet.close()

    def __get_cellcounts(self):
        if self.fdata is None:
            return
        try:
            cc = dict([(k, int(v)) for k, v in np.asarray(self.fdata['/runconfig/cellcount']) if k in cellcount_tuple._fields])                
            self.cellcounts = cellcount_tuple(**cc)
        except KeyError, e:
            print e           

    def __get_timestamp(self):
        try:
            ts = self.fdata.attrs['timestamp']
            self.timestamp = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        except (ValueError, KeyError):
            # Older files do not have the time stamp attribute
            # But all data files are named according to the scheme:
            # data_YYYYmmdd_HHMMSS_PID.h5
            tokens = os.path.basename(self.fdata.filename).split('_')
            ts = tokens[1] + tokens[2]
            self.timestamp = datetime.strptime(ts, '%Y%m%d%H%M%S')

    def __get_stimuli(self):
        try:
            self.bg_stimulus = np.asarray(self.fdata['/stimulus/stim_bg'])
            self.probe_stimulus = np.asarray(self.fdata['/stimulus/stim_probe'])
        except KeyError as e:
            print e
        
    def __get_schedinfo(self):
        schedinfo = dict(self.fdata['/runconfig/scheduling'])
        self.simtime = float(schedinfo['simtime'])
        self.simdt = float(schedinfo['simdt'])
        self.plotdt = float(schedinfo['plotdt'])

    def __get_synapse(self):
        try:
            self.synapse = np.asarray(self.fnet['/network/synapse'])
        except KeyError as e:
            print self.fdata.filename, 'encountered error'
            print e
            raise(e)
            
    def get_notes(self):
        return self.fdata.attrs['notes']
        
    def presynaptic(self, cellname):
        indices = np.char.startswith(self.synapse['dest'], cellname+'/')
        return list(set([row[0] for  \
                row in np.char.split(self.synapse['source'][indices], '/')]))

    def postsynaptic(self, cellname):
        indices = np.char.startswith(self.synapse['source'], cellname+'/')
        return list(set([row[0] for  \
                row in np.char.split(self.synapse['dest'][indices], '/')]))

    def __get_stimulated_cells(self):
        """Create the attributes `bg_cells` and `probe_cells` - lists
        of cells that received background stimulus and probe stimulus
        resepctively.
        
        """
        if hasattr(self, 'bg_cells'):
            return
        stiminfo = np.asarray(self.fnet['/stimulus/connection'])
        self.bg_cells = [ token[-2] \
                          for token in np.char.split(stiminfo[np.char.endswith(stiminfo['f0'], 'stim_bg')]['f1'], '/')]
        self.probe_cells = [token[-2] \
                            for token in np.char.split(stiminfo[np.char.endswith(stiminfo['f0'], 'stim_probe')]['f1'], '/')]

    def get_bg_stimulated_cells(self, celltype):
        """Get the cells which get input from a TCR cell receiving
        background stimulus"""
        post_cells = []
        for cell in self.bg_cells:
            post_cells += self.postsynaptic(cell)
        return [cell for cell in set(post_cells) if cell.startswith(celltype)]
        
    def get_probe_stimulated_cells(self, celltype):
        """Get the cells which get input from a TCR cell receiving
        probe stimulus"""
        post_cells = []
        for cell in self.probe_cells:
            post_cells += self.postsynaptic(cell)
        return [cell for cell in set(post_cells) if cell.startswith(celltype)]

    def bg_stimulus_spike_correlations(self, celltype, window):
        cells = self.get_bg_stimulated_cells(celltype)
        raise NotImplementedError('TODO: finish')

    def get_bgstim_times(self):
        indices = np.nonzero(np.diff(self.bg_stimulus))[0]
        return indices * self.simtime / len(self.bg_stimulus)

    def get_spiking_cell_hist(self, celltype, timerange=(0,1e9), binsize=5e-3):
        """Get the number of cells spiking in each time bin of width
        `binsize`.

        celltype: cell population to search

        timerange: 2-tuple (starttime, endtime) where only the region
        within this period is considered.

        binsize: the time interval within which spikes from two cells
        must fall to be called synchronous.

        Return (cellcount-histogram, bins).

        numpy.histogram function is used to compute the number of
        cells spiking in a bin. So the results depend on where you
        start the time. Ideally one should do a sliding to get the
        maximums.
        """
        tstart = 0
        if timerange[0] > tstart:
            tstart = timerange[0]
        tend = data.simtime
        if timerange[1] < tend:
            tend  = timerange[1]
        assert(tend > tstart)
        cells = np.asarray(self.spikes.keys())
        cells = cells[np.char.startswith(celltype)]
        bins = np.arange(tstart, tend, binsize)
        # Get the histograms of spikes for each cell
        histlist = [np.histogram(self.spikes[cell], bins)[0] for cell in cells]
        # If there was nonzero spike in the bin, the cell counts
        # towards firing cell in that bin
        histlist = [np.where(hist > 0, 1.0, 0.0) for hist in histlist]
        return (np.sum(histlist, axis=0), bins)

    def get_popspike_times(self, celltype, cutoff=0.5, timerange=(0,1e9), binsize=5e-3):
        """Return the centre of the bins in which more than `cutoff`
        fraction of cells of `celltype` fired.

        Get loose measure of popspike times for celltype.

        This sums up the number of cells firing in each bin and if
        this is more than `cutoff` fraction of the population, counts
        it as a population spike.
        """
        cellcounts = self.get_spiking_cell_hist(celltype, timerange, binsize)[0]
        fracs = cellcounts * 1.0 / self.cellcounts._asdict[celltype]
        indices = np.nonzero(fracs > cutoff)[0]
        return (indices+0.5) * binsize

    def get_burst_arrays(self, celltype, timerange=(0, 1e9), mincount=3, maxisi=15e-3):
        """Get bursts of spikes where two spikes within maxisi are
        considered part of the same burst.

        celltype: string or list of strings.  If it is a string, it is
        taken as celltype and data for all cells starting with this
        string is returned.  If a list of string, this is taken as
        name of cells and data for cells with these names is returned.
        
        Returns a dict of cells to bursts. bursts is a list of arrays
        containing spiketimes for members of the burst.

        """
        tstart = 0
        if timerange[0] > tstart:
            tstart = timerange[0]
        tend = self.simtime
        if timerange[1] < tend:
            tend = timerange[1]
        assert(tend > tstart)
        if isinstance(celltype, str):
            cell_spiketrain = [(cell, spiketrain[(spiketrain >= tstart) & (spiketrain < tend)])
                               for cell, spiketrain in self.spikes.items() 
                               if cell.startswith(celltype)]
        else:
            cell_spiketrain = []
            for cell in celltype:
                spiketrain = self.spikes[cell]
                spiketrain = spiketrain[(spiketrain >= tstart) & (spiketrain < tend)]
                cell_spiketrain.append((cell, spiketrain))
        burst_dict = dict([(cell, [spiketimes 
                                   for spiketimes in np.array_split(sp, np.where(np.diff(sp) > maxisi)[0]+1) 
                                   if len(spiketimes) >= mincount])
                           for cell, sp in cell_spiketrain])        
        return burst_dict

    def get_burstidx_dict(self, celltype, timerange=(0, 1e9), mincount=3, maxisi=15e-3):
        """Get a dictionary of cells to bursts in its spike train.

        The bursts are presented as a Nx2 array where each row is
        (start_index, length) and N is the total number of detected
        bursts.

        """
        tstart = 0
        if timerange[0] > tstart:
            tstart = timerange[0]
        tend = self.simtime
        if tend > timerange[1]:
            tend = timerange[1]
        assert(tend > tstart)
        if isinstance(celltype, str):
            cells = [cell for cell in self.spikes.keys() if cell.startswith(celltype)]
        else:
            cells = celltype
        burst_dict = {}
        for cell in cells:
            spikes = self.spikes[cell]
            spikes = spikes[(spikes >= tstart) & (spikes < tend)].copy()
            bursts = get_bursts(spikes, mincount, maxisi)  
            if not bursts.shape or bursts.shape[0] == 0:
                continue
            burst_dict[cell]
        return burst_dict

    def get_bursting_cells_hist(self, celltype, timerange=(0,1e9), binsize=100e-3, mincount=3, maxisi=15e-3):
        """Get histogram containing number of cells bursting in each
        bin of `binsize` width"""
        tstart = 0
        if timerange[0] > tstart:
            tstart = timerange[0]
        tend = self.simtime
        if timerange[1] < tend:
            tend = timerange[1]
        bins = np.arange(tstart, tend, binsize)
        burst_dict = self.get_burst_arrays(celltype, timerange=timerange, mincount=mincount, maxisi=maxisi)
        hists = [np.histogram([np.mean(burst) for burst in burst_train], bins)[0] for burst_train in burst_dict.values()]
        hists = [np.where(h > 0, 1.0, 0.0) for h in hists]
        return (np.sum(hists, axis=0), bins)

    def get_popburst_categories(self, cells, timerange=(0,1e9), mincount=3, maxisi=15e-3):
        """Get the population burst info for `cells`. The population
        burst info is a sequence categories where each category
        contains the (cellname, burst start, burst end) in increasing
        order of burst start for all overlapping bursts. Different
        categories represent non overlapping bursts.

        data: TraubData instance

        cells: str or list of str if a single string is specified, it is
        taken as the celltype and all cellnames starting with this string
        are included.

        If a list of strings, the entries are taken as exact cellnames.

        Return a list of lists. The inner lists are bursts that
        overlap in time. Each entry is a 3-tuple of (cell,
        burst_start_spiketime, burst_end_spiketime).

        """
        collected_burst_info = []
        pop_bursts = []
        if isinstance(cells, str):
            cells = [cell for cell in self.spikes.keys() if cell.startswith(cells)]
        for cell in cells:
            spiketrain = self.spikes[cell]
            spiketrain = spiketrain[(spiketrain >= timerange[0]) & (spiketrain < timerange[1])].copy()
            burst_info = get_bursts(spiketrain, mincount, maxisi)
            if burst_info is None or not burst_info.shape or burst_info.shape[0] == 0:
                continue
            for entry in burst_info:
                collected_burst_info.append((cell, spiketrain[entry[0]], spiketrain[entry[0]+entry[1]-1]))        
        # Sort the bursts by start spike time, the ends and cell names
        # get moved around with it
        sorted_burst_info = sorted(collected_burst_info, key=itemgetter(1))
        print len(sorted_burst_info)
        # First pass: go through the bursts and collect the
        # overlapping ones into categories
        catidx = 0
        categories = []
        current_index = catidx + 1
        current_index = 0
        while current_index < len(sorted_burst_info):
            categories.append([sorted_burst_info[current_index]])
            burst_end = sorted_burst_info[current_index][2]
            current_index += 1
            while current_index < len(sorted_burst_info) and \
                    sorted_burst_info[current_index][1] < burst_end:
                categories[-1].append(sorted_burst_info[current_index])
                if sorted_burst_info[current_index][2] > burst_end:
                    burst_end = sorted_burst_info[current_index][2]
                current_index += 1
        return categories

    def get_pop_ibi(self, cells, pop_frac=0.2, timerange=(0.0, 1e9), mincount=3, maxisi=15e-3):
        """Get the inter-population-burst-intervals for cells. The
        population burst start and end are calculated as
        mean_burst_centre - 2 * std and mean_burst_centre + 2 * std.

        cells - a string representing cell types or a sequence containing cell names.

        pop_frac: fraction of `cells` that must burst together to call
        it a population burst.

        timerange: time range of data to look at

        mincount: minimum number of spikes in  a burst

        maxisi: maximum inter spike interval for two spikes to be
        considered part of a burst.

        Returns a dictionary with the following key value pairs: 

        'odd_cells' -> list of cells that fire outside population bursts

        'pop_ibi' -> a tuple containing list of population burst start
        and burst end times.

        """
        if isinstance(cells, str):
            cells = [cell for cell in self.spikes.keys() if cell.startswith(cells)]
        tstart = 0.0
        if timerange[0] > tstart:
            tstart = timerange[0]
        tend = self.simtime
        if  timerange[1] < tend:
            tend = timerange[1]
        categories = self.get_popburst_categories(cells, (tstart, tend), mincount, maxisi)
        odd_cells = set()
        starts = []
        ends = []
        # TODO: select the odd cells more carefully ... most cells are
        # turning out to be odd cells
        for cat in categories:
            if len(cat) * 1.0 / len(cells) < pop_frac:
                odd_cells.update([entry[0] for entry in cat])
                continue
            # compute the centre of the population bursts
            mean = np.mean([entry[1:] for entry in cat])
            # Compute the width of the population bursts
            sd = np.std([entry[1:] for entry in cat])
            ends.append(cat[0][1])
            starts.append(max([entry[2] for entry in cat]))                    
            # plt.plot([starts[-1], mean, ends[-1]], [1.0, 1.0, 1.0], 'kx')
            # for burst in cat:
            #     plt.plot(burst[1], [2], 'b+')
            #     plt.plot(burst[2], [2], 'y+')
            # plt.plot([cat[0][1]], [2], 'rx')
            # plt.plot(max([b[2] for b in cat]), [2], 'gx')                
            # plt.show()
        if ends[0] < tstart:
            ends = ends[1:]
        else:
            starts = [tstart] + starts
        if starts[-1] >= tend:
            starts = starts[:-1]
        else:
            ends.append(tend)
        return {'odd_cells': odd_cells,
                'pop_ibi': (starts, ends)}

    def get_pop_spike_hist(self, celltype, binsize=5e-3, timerange=(0, 1e9)):
        """Calculate the population spike histogram.

        celltype: string representing cell type or a list of
        individual cell names

        binsize: size of histogram bins (5 ms default)

        timerange: tuple (start, end) the time range of simulation to
        be histogrammed.

        Returns: (cells, hist, bins) - where cells is the list of
        cells we histogrammed for, hist is the histogram of spike
        counts in each bin normalized by the product of bin size and
        cell count, hence number of spikes per second per cell in each
        bin and bins is an array containing bin boundaries.

        """
        cells = []
        if isinstance(celltype, str):
            cells = [cell for cell in self.spikes.keys() if cell.startswith(celltype)]
        tstart = 0
        tend = self.simtime
        if timerange[0] > tstart:
            tstart = timerange[0]
        if timerange[1] < tend:
            tend = timerange[1]
        assert(tstart < tend)
        spikes = []
        for cell in cells:
            spikes = np.r_[spikes, self.spikes[cell]]        
        bins = np.arange(tstart, tend, binsize)
        if bins[-1] < tend:
            bins = np.r_[bins, tend]
        hist, bins = np.histogram(spikes, bins)
        hist /= (bins * len(cells)) # Normalize to per cell per second
        return cells, hist, bins

    def get_cell_graph(self):
        if hasattr(self, 'cell_graph'):
            return self.cell_graph
        self.cell_graph = nx.MultiDiGraph()
        synapses = self.fnet['/network/synapse']
        pre_cells = [row[0] for row in np.char.split(synapses['source'], '/')]
        post_cells = [row[0] for row in np.char.split(synapses['dest'], '/')]
        weights = [g for g in synapses['Gbar']]        
        self.cell_graph.add_weighted_edges_from(zip(pre_cells, post_cells, weights))
        index = 0
        for e in self.cell_graph.edges_iter(data=True):
            e[2]['type'] = synapses['type'][index]
            index += 1
        for cell in self.cell_graph:
            celltype = cell.split('_')[0]
            self.cell_graph.node[cell]['color'] = self.colordict[celltype]
        return self.cell_graph

        

            
            
def get_bursts(spikes, mincount=3, maxisi=15e-3):
    if len(spikes) < mincount:
        return np.array(0)
    ISI = np.diff(spikes)
    ISI_limit = np.diff(np.where(ISI < maxisi, 1, 0))
    begin_int = np.nonzero(ISI_limit == 1)[0] + 1
    if ISI[0] < maxisi:
        begin_int = np.r_[0, begin_int]
    end_int = np.nonzero(ISI_limit == -1)[0] + 1
    if len(end_int) < len(begin_int):
        end_int = np.r_[end_int, len(ISI)-1]
    return np.asarray([(start, end - start + 1) \
                                       for start, end in zip(begin_int, end_int) \
                                       if end - start + 1 >= mincount-1], dtype=int)
                           
        

def test_get_burstidx_dict():
    """Test the get_bursts function. Select five random data file and
    choose 3 random spiny stellates from each. Plot the spike trains
    along with burst start and burst ends. See if they match human
    judgement.

    """
    flist = []
    with open('exc_inh_files.txt') as flistfile:
        for line in flistfile:
            fname = line.strip()
            if len(fname) == 0 or fname.startswith('#'):
                continue
            flist.append(fname)
    # Take some random datasets
    flist = random.sample(flist, 10)
    datalist = [TraubData(fname) for fname in flist]
    for data in datalist:
        tstart = random.uniform(0, data.simtime - 1.0)        
        tend = tstart + 1.0        
        b = data.get_burstidx_dict('SpinyStellate', timerange=(tstart,  tend))
        # Select a few random bursts
        cells = random.sample(b.keys(), 3)
        print tstart, tend, cells
        for idx, cell in enumerate(cells):
            spikes = data.spikes[cell]
            spikes = spikes[(spikes >= tstart) & (spikes < tend)].copy()
            plt.plot(spikes, np.ones(len(spikes))*idx, 'b+')
            bursts = b[cell]
            print cell, bursts.shape
            if not bursts.shape or bursts.shape[0] == 0:
                print 'No bursts in this', cell, spikes
                continue
            print bursts
            plt.plot(spikes[bursts[:,0]], np.ones(len(bursts))*idx, 'gx')
            plt.plot(spikes[np.sum(bursts, axis=1)-1], np.ones(len(bursts))*idx, 'rx')
        plt.show()
        plt.close()

def test_get_pop_burst_categories():
    """Test the performance of pop_ibi function."""
    datalist = get_test_data()
    for data in datalist:
        tstart = random.uniform(0, data.simtime-2.0)
        tend = tstart + 2.0
        cats = data.get_popburst_categories('SpinyStellate', timerange=(tstart, tend))
        print data.fdata.filename, cats
        for idx, category in enumerate(cats):
            for burst in category:
                plt.plot(burst[1], [idx], 'b+')
                plt.plot(burst[2], [idx], 'y+')
            plt.plot([category[0][1]], [idx], 'rx')
            plt.plot(max([b[2] for b in category]), [idx], 'gx')                
        plt.xlabel('Spike time (s)')
        plt.ylabel('Category #')
        plt.title('Categories of overlapping bursts\nBlue +: start of burst, Yellow +: end of burst\n')
        plt.show()
        plt.close() # release the resources

def get_test_data(num=3):
    """Peak up `num` random files from data files listed in
    `exc_inh_files.txt` and return a list of TraubData object for the
    same"""
    flist = []
    with open('exc_inh_files.txt') as flistfile:
        for line in flistfile:
            fname = line.strip()
            if len(fname) == 0 or fname.startswith('#'):
                continue
            flist.append(fname)
    # Take some random datasets
    flist = random.sample(flist, num)
    datalist = [TraubData(fname) for fname in flist]
    return datalist
    
def test_pop_ibi():
    """Test the computation of population interburst intervals"""
    datalist = get_test_data()
    timerange = (1.0, 20.0)
    for data in datalist:
        ibi_data = data.get_pop_ibi('SpinyStellate', timerange=timerange, pop_frac=0.1)
        cells = [ss for ss in data.spikes.keys() if ss.startswith('SpinyStellate')]
        print 'all cells', len(cells)
        odd_cells = set(ibi_data['odd_cells'])
        print odd_cells
        print 'odd cells', len(odd_cells)
        cells = set(cells) - odd_cells
        print 'good cells', len(cells)
        for index, cell in enumerate(cells):
            spikes = data.spikes[cell]
            spikes = spikes[(spikes >= timerange[0]) & (spikes < timerange[1])].copy()
            plt.plot(spikes, np.ones(len(spikes)) * index, 'b+', alpha=0.4)
        for index, cell in enumerate(odd_cells):
            spikes = data.spikes[cell]
            spikes = spikes[(spikes >= timerange[0]) & (spikes < timerange[1])].copy()
            plt.plot(spikes, np.ones(len(spikes)) * (index+len(cells)), 'c+', alpha=0.4)
        plt.bar(ibi_data['pop_ibi'][0], 
                height=np.ones(len(ibi_data['pop_ibi'][0])) * (len(cells) + len(odd_cells)+1), 
                width=np.array(ibi_data['pop_ibi'][1]) - np.array(ibi_data['pop_ibi'][0]), 
                alpha=0.2)
        # plt.plot(ibi_data['pop_ibi'][0], np.ones(len(ibi_data['pop_ibi'][0]))*(index+1), 'gx')
        # plt.plot(ibi_data['pop_ibi'][1], np.ones(len(ibi_data['pop_ibi'][1]))*(index+1), 'rx')
        plt.show()
        plt.close()
        
    
    
from matplotlib import pyplot as plt

if __name__ == '__main__':
    # for testing
    # test_get_burstidx_dict()
    # test_get_pop_burst_categories()
    test_pop_ibi()
# 
# traubdata.py ends here
