"""Prepares, manipulates, and writes data for mbGDML.

Raises:
    KeyError: when the parsed output file does not have any energies.
"""

# MIT License
# 
# Copyright (c) 2020, Alex M. Maldonado
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import re
import numpy as np
from cclib.io import ccread
from cclib.parser.utils import convertor
from mbgdml import utils
from mbgdml.solvents import solvent

gdml_partition_size_names = [
    'monomer', 'dimer', 'trimer', 'tetramer', 'pentamer'
]

class PartitionCalcOutput():
    """Quantum chemistry output file for all MD steps of a single partition.

    Output file that contains electronic energies and gradients of the same
    partition from a single MD trajectory. For a single dimer partition of a
    n step MD trajectory would have n coordinates, single point energies,
    and gradients.

    Args:
        output_path (str): Path to computational chemistry output file that
            contains energies and gradients (preferably ab initio) of all
            MD steps of a single partition.

    Attributes:
        output_file (str): Path to quantum chemistry output file for a
            partition.
        output_name (str): The name of the quantum chemistry output file
            (includes extension).
        cluster (str): The label identifying the partition of the MD trajectory.
        temp (str): Set point temperautre for the MD thermostat.
        iter (int): Identifies the iteration of the MD iteration.
        partition (str): Identifies what solvent molecules are in the partition.
        partition_size (int): The number of solvent molecules in the partition.
        cclib_data (obj): Contains all data parsed from output file.
        atoms (np.array): A (n) array containing n atomic numbers.
        coords (np.array): A (m, n, 3) array containing the atomic coordinates
            of n atoms of m MD steps.
        grads (np.array): A (m, n, 3) array containing the atomic gradients
            of n atoms of m MD steps.
        forces (np.array): A (m, n, 3) array containing the atomic forces
            of n atoms of m MD steps.
        energies (np.array): A (m, n) array containing the energies of n atoms
            of m MD steps.
        solvent (obj): From Solvent class and contains solvent information.
    """

    def __init__(self, output_path):
        self.output_file = output_path
        self._get_label_info()
        self.cclib_data = ccread(self.output_file)
        self._get_gdml_data()
        self._get_solvent_info()
    
    def _get_label_info(self):
        """Gets info from output file name.

        Output file should be labeled in the following manner:
        'out-NumSolv-temperature-iteration-partition.out'.
            'NumSolv' tells us original sized solvent cluster (e.g., 4MeOH);
            'temperature' is the set point for the thermostat (e.g., 300K);
            'iteration' identifies the MD simulation (e.g., 2);
            'partition' identifies what solvent molecules are in the partition
                (e.g., CD).
        A complete example would be 'out-4MeOH-300K-2-CD.out'.
        """
        self.output_name = self.output_file.split('/')[-1]
        split_label = self.output_name.split('-')
        self.cluster = str(split_label[1])
        self.temp = str(split_label[2])
        self.iter = int(split_label[3])
        self.partition = str(split_label[4].split('.')[0])
        self.partition_size = int(len(self.partition))
    
    def _get_solvent_info(self):
        """Adds solvent information to object.
        """
        self.solvent = solvent(self.atoms.tolist())
    
    def _get_gdml_data(self):
        """Parses GDML-relevant data from partition output file.
        """
        try:
            self.atoms = self.cclib_data.atomnos
            self.coords = self.cclib_data.atomcoords
            self.grads = self.cclib_data.grads
            self.forces = np.negative(self.grads)
            if hasattr(self.cclib_data, 'mpenergies'):
                self.energies = self.cclib_data.mpenergies
            elif hasattr(self.cclib_data, 'scfenergies'):
                self.energies = self.cclib_data.scfenergies
            else:
                raise KeyError
        except:
            print('Something happened while parsing output file.')
            print('Please check ' + str(self.output_name) + ' output file.')
    
    # TODO write a function to create the proper GDML dataset and change write
    # GDML to input the GDML dataset

    def write_gdml_data(self, gdml_data_dir):
        """Writes and categorizes GDML file in a common GDML data directory.
        
        This should be the last function called after all necessary data is
        collected from the output file. 

        GDML file is categorized according to its solvent, partition size,
        temperature, and MD iteration in that order. These xyz files contain 
        all information needed to create a GDML native dataset
        (referred to as extended xyz files in GDML documentation).

        Args:
            gdml_data_dir (str): Path to common GDML data directory.
        """

        gdml_data_dir = utils.norm_path(gdml_data_dir)

        # Preparing directories.
        # /path/to/gdml-datasets/solventlabel/partitionsize/temp/iteration
        gdml_solvent = self.solvent.solvent_label
        gdml_solvent_dir = utils.norm_path(
            gdml_data_dir + gdml_solvent
        )
        gdml_partition_size_dir = utils.norm_path(
            gdml_solvent_dir + gdml_partition_size_names[self.partition_size - 1]
        )
        gdml_temp_dir = utils.norm_path(
            gdml_partition_size_dir + str(self.temp)
        )
        gdml_iter_dir = utils.norm_path(
            gdml_temp_dir + str(self.iter)
        )
        all_dir = [gdml_solvent_dir, gdml_partition_size_dir, gdml_temp_dir,
                   gdml_iter_dir]
        for directory in all_dir:
            try:
                os.chdir(directory)
            except:
                os.mkdir(directory)
                os.chdir(directory)
        
        # Writing GDML file.
        self.gdml_file = gdml_iter_dir + self.partition \
                         + '-' + self.cluster \
                         + '-' + self.temp \
                         + '-' + str(self.iter) \
                         + '-gdml.xyz'
        with open(self.gdml_file, 'w') as gdml_file:
            step_index = 0
            atom_list = utils.atoms_by_element(self.atoms)
            atom_num = self.solvent.solvent_molec_size \
                       * self.solvent.cluster_size
            while step_index < len(self.coords):

                # Number of atoms.
                gdml_file.write(str(atom_num) + '\n')

                # Comment with energy.
                step_energy = convertor(
                    self.energies[step_index][0], 'eV', 'kcal/mol'
                )
                gdml_file.write(str(step_energy) + '\n')

                # Atomic positions and gradients.
                atom_index = 0
                while atom_index < len(self.atoms):
                    atom_string = atom_list[atom_index] + '     '
                    coord_string = np.array2string(
                        self.coords[step_index][atom_index],
                        suppress_small=True, separator='     ',
                        formatter={'float_kind':'{:0.8f}'.format}
                    )[1:-1] + '     '
                    # Converts from Eh/bohr to kcal/(angstrom mol)
                    converted_forces = self.forces[step_index][atom_index] \
                                      * ( 627.50947414 / 0.5291772109)
                    grad_string = np.array2string(
                        converted_forces,
                        suppress_small=True, separator='     ',
                        formatter={'float_kind':'{:0.8f}'.format}
                    )[1:-1] + '     '

                    atom_line = ''.join([atom_string, coord_string, grad_string])

                    # Cleaning string for alignments with negative numbers and
                    # double-digit numbers.
                    atom_line = atom_line.replace(' -', '-') + '\n'
                    neg_double = re.findall(
                        ' -[0-9][0-9].[0-9]', atom_line.rstrip()
                    )
                    pos_double = re.findall(
                        ' [0-9][0-9].[0-9]', atom_line.rstrip()
                    )
                    for value in neg_double:
                        atom_line = atom_line.replace(value, value[1:])
                    for value in pos_double:
                        atom_line = atom_line.replace(value, value[1:])

                    gdml_file.write(atom_line)

                    atom_index += 1
            
                step_index += 1


# TODO write 
def sgdml_dataset_from_partition_calc():
    pass