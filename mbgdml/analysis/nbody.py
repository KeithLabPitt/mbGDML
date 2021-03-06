# MIT License
# 
# Copyright (c) 2020-2021, Alex M. Maldonado
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
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

"""Analyses for mbGDML models."""

import logging
import numpy as np
import matplotlib.pyplot as plt
from mbgdml.utils import norm_path
from mbgdml.utils import atoms_by_element
logging.getLogger("matplotlib").setLevel(logging.ERROR)

class NBody:
    """Probing individual n-body contributions of force fields.
    """

    def __init__(self):
        pass

    def force_similarity(self, predict_force, true_force):
        """Compute cosine distance of two force vectors.

        Computes 1 - cosine_similarity. Two exact vectors will thus have a
        similarity of 0, orthogal vectors will be 1, and equal but opposite
        will be 2.
        
        Parameters
        ----------
        predict_force : `numpy.ndarray`
            Array of the predicted force vector by GDML.
        true_force : `numpy.ndarray`
            Array of the true force vector of the same shape as predict_force
        
        Returns
        -------
        `float`
            Similarity (accuracy) of predicted force vector for an atom. 0.0 is 
            perfect similarity and the further away from zero the less similar 
            (accurate).
        
        """
        similarity = np.dot(predict_force, true_force) / \
                     (np.linalg.norm(predict_force) * \
                      np.linalg.norm(true_force))
        similarity = float(1 - similarity)
        return similarity
    
    def cluster_force_similarity(self, predict_set, structure_index):
        """Computes the cosine distance of each atomic force of a single
        structure for all n-body corrections.

        Parameters
        ----------
        predict_set : `mbgdml.data.mbGDMLPredictset`
            Object with loaded predict set.
        structure_index : `int`
            Index of the structure in the predict set arrays.

        Returns
        -------
        `numpy.ndarray`
            Cosine similarities of all possible n-body corrections of a single
            structure in the shape of ``(n_z, nbodies)`` where ``n_z`` is the
            number of atoms in the structure and ``nbodies`` is the number of
            n-body corrections in the predict set.
        """
        F = {}
        F_index = 1
        while f'F_{F_index}' in predict_set.predictset.keys():
            _, F_nbody = predict_set.nbody_predictions(F_index)
            F[f'F_{F_index}'] = F_nbody[structure_index]
            F_index += 1
        F_true = predict_set.F_true[structure_index]
        similarities = np.zeros((F_true.shape[0], F_index - 1))
        atom = 0
        while atom < F_true.shape[0]:
            F_index = 1
            while f'F_{F_index}' in F:
                similarities[atom][F_index - 1] = self.force_similarity(
                    F_true[atom], F[f'F_{F_index}'][atom]
                )
                F_index += 1
            atom += 1
        return similarities
    
    def average_force_similarity(self, predict_set, structure_list):
        """Computes average force similarity over multiple structures.

        Parameters
        ----------
        predict_set : `mbgdml.data.mbGDMLPredictset`
            Object with loaded predict set.
        structure_list : `list`
            Indices of structures to include in the heatmap. To select all
            structures, one could use
            ``list(range(0, predict_set.F_true.shape[0]))`` for example.
        
        Returns
        -------
        `numpy.ndarray`
            Average cosine distances of all possible n-body corrections over
            selected structures in the shape of ``(n_z, nbodies)`` where ``n_z``
            is the number of atoms in the structure and ``nbodies`` is the
            number of n-body corrections in the predict set.
        """
        sim_list = []
        for struct in structure_list:
            sim_list.append(self.cluster_force_similarity(
                predict_set, struct
            ))
        if len(structure_list) != 1:
            sim_mean = np.zeros(sim_list[0].shape)
            for atom in list(range(0, sim_list[0].shape[0])):
                for n_body in list(range(0, sim_list[0].shape[1])):
                    mean_array = np.array([])
                    for struct in structure_list:
                        mean_array = np.append(
                            mean_array,
                            sim_list[structure_list[struct]][atom][n_body]
                        )
                    sim_mean[atom][n_body] = np.mean(mean_array)
        return sim_mean


class NBodyHeatMaps(NBody):
    """Heat maps for n-body contribution accuracy.
    """

    def __init__(self):
        pass

    def create_heatmap(
        self, similarity, y_labels, num_nbody, name, data_labels,
        save_dir
    ):
        """
        Generates matplotlib heatmap figure.

        Parameters
        ----------
        similarity : `numpy.ndarray`
            Cosine distances in n x m array where n is the order of n-body
            contributions, and m is the number of atoms.
        y_labels : `list` [`str`]
            Labels of the y axis of the heat map.
        num_nbody : `list` [`str`]
            Maximum number of n-body contributions to include.
        name : `str`
            File name to save the heatmap.
        data_labels : `bool`
            Whether or not to include values of cosine distance inside
            heatmap cells.
        """
        fig, heatmap = plt.subplots(figsize=(3, 4), constrained_layout=True)
        #norm = mpl.colors.Normalize(vmin=0, vmax=2.0)
        #im = heatmap.imshow(similarity, cmap='Reds', vmin=0.0, vmax=2.0, norm=norm)
        im = heatmap.imshow(similarity, cmap='Reds')
        # Customizing plot.
        heatmap.set_xticks(np.arange(len(num_nbody)))
        heatmap.set_xticklabels(num_nbody)
        heatmap.set_xlabel('n-body order')
        heatmap.set_yticks(np.arange(len(y_labels)))
        heatmap.set_yticklabels(y_labels)
        heatmap.set_ylabel('atoms')
        # Customizing colorbar
        fig.colorbar(im, orientation='vertical')
        if data_labels:
            # Loop over data dimensions and create text annotations.
            for i in range(len(y_labels)):
                for j in range(len(num_nbody)):
                    num = np.around(similarity[i, j], decimals=2)
                    heatmap.text(j, i, num,
                                ha="center", va="center", color="black")
        plt.savefig(f'{save_dir}{name}.png', dpi=600, bbox_inches='tight')
        plt.close()
    
    def force_heatmap(
        self, predict_set, structure_list, base_name, save_dir,
        data_labels=False
    ):
        """Computes and saves force heat map of predict set.

        Parameters
        ----------
        predict_set : `mbgdml.data.mbGDMLPredictset`
            Object with loaded predict set.
        structure_list : `list`
            Indices of structures to include in the heatmap.
        base_name : `str`
            First part of saved file name.
        save_dir : `str`
            Path to save the heatmap to as a png.
        data_labels : `bool`, optional
            Whether or not to include values of cosine distance inside
            heatmap cells.
        """
        save_dir = norm_path(save_dir)
        sim_mean = self.average_force_similarity(predict_set, structure_list)
        atoms = atoms_by_element(predict_set.z.tolist())
        num_nbody = list(range(1, np.shape(sim_mean)[1] + 1))
        num_nbody = [str(i) for i in num_nbody]
        name = f'{base_name}-average'
        self.create_heatmap(
            sim_mean,
            atoms,
            num_nbody,
            name,
            data_labels,
            save_dir
        )


class NBodyMD(NBody):

    def __init__(self):
        pass

    
    