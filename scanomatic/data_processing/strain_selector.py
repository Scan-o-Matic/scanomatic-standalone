from typing import Sequence

import numpy as np

from scanomatic.data_processing.growth_phenotypes import Phenotypes
from scanomatic.data_processing.pheno.state import (
    PhenotyperSettings,
    PhenotyperState
)
from scanomatic.generics.phenotype_filter import FilterArray


def scan(plate_meta_data, column, value_function):
    return value_function(plate_meta_data[column])


SelectionType = Sequence[tuple[int, ...]]


class StrainSelector:
    """Quick and easy access to sub-selection of phenotype results.

    Attributes:
        StrainSelector.selection: The positions included in the sub-selection
        StrainSelector.raw_growth_data: The non-smooth growth data for the
            sub-selection
        StrainSelector.smooth_growth_data: The smooth growth data
        StrainSelector.phenotype_names: The names of the phenotypes extracted.
        StrainSelector.meta_data: Getting the meta-data
        StrainSelector.get_phenotype: Getting data for a certain phenotype

    Examples:

        You can add two selections to make the union of the selections
        Let `s1` and `s2` be `StrainSelector` instances.
        ```s_combined = s1 + s2```

        You can extend a current `StrainSelector` in place too making it
        the union of itself and the other.
        ```s1 += s2```

    See Also:
        .phenotyper.Phenotyper.find_in_meta_data:
            The search method for creating subselections based on meta-data.
    """
    def __init__(
        self,
        phenotyper_state: PhenotyperState,
        phenotyper_settings: PhenotyperSettings,
        selection: SelectionType,
    ):
        """Create a sub-selection accessor.

        Args:
            phenotyper: a `PhenotyperState`
            selection: a list of coordinate tuples with length equal to the
                number of plates in `phenotyper`. The coordinate tuples should
                be two length, with a tuple in each position (representing
                outer and inner indices of coordinates respectively).
        """
        self.__phenotyper_state = phenotyper_state
        self.__phenotyper_settings = phenotyper_settings
        self.__selection = selection

    def __add__(self, other: "StrainSelector") -> "StrainSelector":
        if other.__phenotyper_state == self.__phenotyper_state:
            return StrainSelector(
                self.__phenotyper_state,
                self.__phenotyper_settings,
                tuple(
                    StrainSelector.__joined(s1, s2)
                    for s1, s2 in zip(self.__selection, other.__selection)
                )
            )
        else:
            raise ValueError("Other does not have matching phenotyper")

    def __iadd__(self, other: "StrainSelector") -> "StrainSelector":

        if other.__phenotyper_state == self.__phenotyper_state:
            self.__selection = tuple(
                StrainSelector.__joined(s1, s2)
                for s1, s2 in zip(self.__selection, other.__selection)
            )
        else:
            raise ValueError("Other does not have matching phenotyper")

    @staticmethod
    def __joined(
        selection1: SelectionType,
        selection2: SelectionType,
    ) -> SelectionType:
        if selection1 and selection2:
            return selection1[0] + selection2[0], selection1[1] + selection2[1]
        elif selection1:
            return selection1
        else:
            return selection2

    def __filter(self, data) -> tuple:
        return tuple(
            (d[f] if d is not None else None)
            for d, f in zip(data, self.__selection)
        )

    @property
    def analysed_phenotypes(self):
        for p in Phenotypes:
            if (
                self.__phenotyper_settings.phenotypes_inclusion(p)
                and self.__phenotyper_state.has_phenotype_on_any_plate(p)
            ):
                yield p

    @property
    def selection(self) -> SelectionType:
        return self.__selection

    @property
    def raw_growth_data(self):
        return self.__filter(self.__phenotyper_state.raw_growth_data)

    @property
    def smooth_growth_data(self):
        return self.__filter(self.__phenotyper_state.smooth_growth_data)

    @property
    def phenotype_names(self):
        return [
            phenotype.name for phenotype in
            self.__phenotyper_state.analysed_phenotypes
        ]

    @property
    def phenotypes(self) -> np.ndarray:
        phenotypes = {}
        for phenotype in self.__phenotyper_state.analysed_phenotypes:
            phenotypes[phenotype] = self.get_phenotype(phenotype)

        return np.array(
            tuple(
                tuple(
                    phenotypes[p][i] for p in
                    self.__phenotyper_state.analysed_phenotypes
                ) for i, _ in enumerate(self.__selection)
            ),
        )

    @property
    def vector_phenotypes(self):
        # TODO: something here
        raise NotImplementedError()

    @property
    def meta_data(self):
        md = self.__phenotyper_state.meta_data
        return [
            tuple(md.get_data_from_numpy_where(i, s) if s else None)
            for i, s in enumerate(self.__selection)
        ]

    def get_phenotype(self, phenotype, **kwargs) -> list[FilterArray]:
        """Get the phenotypes for the sub-selection.

        For more information see `.pheno.state.PhenotyperState.get_phenotype`.

        Args:
            phenotype:
                The phenotype to get data on
            kwargs:
                Further keyword arguments are passed along to
                `PhenotyperState.get_phenotype`


        Returns: list of phenotype arrays for FilterArrays.
        """
        return self.__filter(
            self.__phenotyper_state.get_phenotype(
                self.__phenotyper_settings,
                phenotype,
                **kwargs,
            ),
        )
