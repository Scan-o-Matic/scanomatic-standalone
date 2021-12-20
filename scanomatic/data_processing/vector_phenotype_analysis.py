import operator
from collections.abc import Callable
from itertools import product
from typing import Any

import numpy as np
import scipy.cluster.hierarchy as sch  # type: ignore
from matplotlib import pyplot as plt  # type: ignore
from scipy.signal.windows import gaussian  # type: ignore

from scanomatic.data_processing.growth_phenotypes import Phenotypes


def get_plate_phenotype_in_array(
    phenotypes,
    phenotype=Phenotypes.GrowthVelocityVector,
):

    data = phenotypes[..., phenotype.value]
    try:
        vector_length = max(v.size for v in data.ravel())
    except AttributeError:
        vector_length = 1

    arr = np.zeros(data.shape + (vector_length,), dtype=float)
    for coord in product(*tuple(
        range(dim_length) for dim_length in data.shape
    )):
        if vector_length > 1:
            arr[coord][:len(data[coord])] = data[coord]
        else:
            arr[coord] = data[coord]

    return arr


def get_linearized_positions(data: np.ndarray):
    return np.lib.stride_tricks.as_strided(
        data,
        shape=(data.shape[0] * data.shape[1],) + data.shape[2:],
        strides=(data.strides[1],) + data.strides[2:],
    )


def _resolve_neighbours_gauss(data: np.ndarray) -> np.ndarray:
    gauss = gaussian(data.shape[0] * 2, 3)
    for coord in zip(*np.where(np.isfinite(data) == False)):  # noqa: E712
        data[coord] = np.ma.masked_invalid(
            data[
                :,
                coord[1]
            ] * gauss[data.shape[0] - coord[0]: gauss.shape[0] - coord[0]],
        ).mean()

    return data


def _blank_missing_data(data: np.ndarray) -> np.ndarray:
    data[:, np.where(np.isfinite(data).sum(axis=0) == 0)] = 0
    return data


def _ensure_indata(f):
    def wrapped(*args, **kwargs):
        data = args[0]
        phenotype = kwargs.get('phenotype', Phenotypes.GrowthVelocityVector)

        if data.dtype is object:
            data = get_plate_phenotype_in_array(data, phenotype=phenotype)

        while data.ndim > 2:
            data = get_linearized_positions(data)

        args = list(args)
        args[0] = data

        return f(*args, **kwargs)

    return wrapped


@_ensure_indata
def get_pca_components(
    data: np.ndarray,
    resolve_nans_method: Callable = _resolve_neighbours_gauss,
    dims: int = 2,
):
    M = data.T.copy()
    print((np.isfinite(M) == False).sum())  # noqa: E712
    M = _blank_missing_data(M)
    print((np.isfinite(M) == False).sum())  # noqa: E712
    M = resolve_nans_method(M)
    print((np.isfinite(M) == False).sum())  # noqa: E712
    _, s, Vt = np.linalg.svd(M, full_matrices=False)
    V = Vt.T
    return tuple(s[dim]**(1./2) * V[:, dim] for dim in range(dims))


@_ensure_indata
def plot_heatmap_dendrogram_and_cluster(
    data: np.ndarray,
    distance_measure: str = 'euclidean',
    linkage_method: str = 'single',
    distance_kwargs: dict[str, Any] = {},
    dendrogram_kwargs: dict[str, Any] = {'no_labels': True},
    cluster_kwargs: dict[str, Any] = {'criterion': 'distance', 't': 0.9},
):

    print(type(data), type(distance_measure))
    if distance_measure == 'seuclidean' and not distance_kwargs.get('V', None):
        distance_kwargs['V'] = np.ma.masked_invalid(data).std(axis=0)

    distances = sch.distance.pdist(
        data,
        metric=distance_measure,
        **distance_kwargs,
    )

    fig = plt.figure()

    # Easy extension for clustering in both dimensions
    dendrogram = [None]
    linkage = [None]
    for id, (ax_placement, dendrogram_orientation) in enumerate(
        (([0.09, 0.1, 0.4, 0.8], 'right'),)
    ):
        ax = fig.add_axes(ax_placement)
        linkage[id] = sch.linkage(distances, method=linkage_method)
        dendrogram[id] = sch.dendrogram(
            linkage[id],
            orientation=dendrogram_orientation,
            **dendrogram_kwargs,
        )
        ax.axis('off')

    heat_ax = fig.add_axes([0.5, 0.1, 0.4, 0.8])
    idx1 = dendrogram[0]['leaves']
    clustered_data = data[idx1, :]
    im = heat_ax.matshow(
        clustered_data,
        aspect='auto',
        origin='lower',
        cmap=plt.cm.YlGnBu,
    )
    heat_ax.axis('off')

    axcolor = fig.add_axes([0.91, 0.1, 0.02, 0.8])
    plt.colorbar(im, cax=axcolor)
    return (
        fig,
        tuple(
            sch.fcluster(linkage[id], **cluster_kwargs)
            for id in range(len(linkage))
        )
    )


def plot_grouped_scatter_phenotypes(
    phenotype_x,
    phenotype_y,
    clustering,
    marker: str = 'o',
    **kwargs,
):
    uniques = np.unique(clustering)
    cluster_sizes = {label: (clustering == label).sum() for label in uniques}
    unique_order = zip(*sorted(
        iter(cluster_sizes.items()),
        key=operator.itemgetter(1)
    ))[0][::-1]
    fig = plt.figure()
    ax = fig.gca()

    for label in unique_order:
        ax.plot(
            phenotype_x[clustering == label],
            phenotype_y[clustering == label],
            marker=marker,
            linestyle="None",
            **kwargs,
        )

    return fig
