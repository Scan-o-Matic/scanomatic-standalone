from typing import Any, Optional, Union

import numpy as np
import pytest

from scanomatic.data_processing.growth_phenotypes import Phenotypes
from scanomatic.data_processing.norm import NormState, Offsets
from scanomatic.data_processing.phases.features import CurvePhaseMetaPhenotypes
from scanomatic.data_processing.pheno.state import (
    PhenotyperSettings,
    PhenotyperState
)
from scanomatic.data_processing.phenotypes import PhenotypeDataType
from scanomatic.generics.phenotype_filter import FilterArray


class TestPhenotyperSettings:
    def test_raises_on_even_kernal_size(self):
        with pytest.raises(AssertionError):
            PhenotyperSettings(4, 1.0, 3, None, 2.0, 3.0)

    def test_serialized_no_inclusion(self):
        assert PhenotyperSettings(5, 1.0, 3, None, 2.0, 3.0).serialized() == [
            5,
            1.0,
            3,
            None,
            2.0,
            3.0,
        ]

    def test_serialized_with_inclusion(self):
        assert PhenotyperSettings(
            5,
            1.0,
            3,
            PhenotypeDataType.All,
            2.0,
            3.0,
        ).serialized() == [
            5,
            1.0,
            3,
            "All",
            2.0,
            3.0,
        ]

class TestPhenotyperState:
    @pytest.mark.parametrize("raw_growth_data,expect", (
        (np.ones((1, 10)), [Offsets.UpperRight()]),
        (np.arange(2), [Offsets.LowerRight(), Offsets.LowerRight()]),
    ))
    def test_init_makes_reference_surface_positions_when_not_matching(
        self,
        raw_growth_data: np.ndarray,
        expect: list[Offsets],
    ):
        np.testing.assert_equal(
            PhenotyperState(
                None,
                raw_growth_data,
                reference_surface_positions=[Offsets.UpperRight()],
            ).reference_surface_positions,
            expect,
        )

    def test_enumerate_plates(self):
        assert tuple(
            PhenotyperState(None, np.zeros((4, 10))).enumerate_plates,
        ) == (0, 1, 2, 3)

    def test_plate_shapes(self):
        assert tuple(
            PhenotyperState(
                None,
                np.array([None, np.ones((12, 24, 33)), None, np.ones((42, 9))]),
            ).plate_shapes
        ) == (None, (12, 24), None, (42, 9))

    @pytest.mark.parametrize("plate,shape", ((0, None), (1, (12, 24))))
    def test_get_plate_shapes(
        self,
        plate: int,
        shape: Optional[tuple[int, int]],
    ):
        assert PhenotyperState(
            None,
            np.array([None, np.ones((12, 24, 33)), None, np.ones((42, 9))]),
        ).get_plate_shape(plate) == shape

    @pytest.mark.parametrize("raw_growth_data,phenotypes,expect", (
        (
            np.arange(3),
            None,
            False,
        ),
        (
            np.arange(3),
            np.arange(2),
            False,
        ),
        (
            np.arange(3),
            np.arange(3),
            True,
        ),
    ))
    def test_has_reference_surface_positions(
        self,
        raw_growth_data: np.ndarray,
        phenotypes: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            raw_growth_data,
        ).has_reference_surface_positions() is expect

    @pytest.mark.parametrize("phenotype_filter_undo,phenotypes,expect", (
        (
            np.arange(3),
            None,
            False,
        ),
        (
            None,
            np.arange(3),
            False,
        ),
        (
            np.arange(3),
            np.arange(2),
            False,
        ),
        (
            np.arange(3),
            np.arange(3),
            True,
        ),
    ))
    def test_has_phenotype_filter_undo(
        self,
        phenotype_filter_undo: Optional[np.ndarray],
        phenotypes: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            np.arange(3),
            phenotype_filter_undo=phenotype_filter_undo
        ).has_phenotype_filter_undo() is expect

    @pytest.mark.parametrize("phenotypes,plate,expect", (
        (None, 42, False),
        (np.array([None, np.arange(3)]), 0, False),
        (np.array([None, np.arange(3)]), 1, True),
    ))
    def test_has_phenotypes_for_plate(
        self,
        phenotypes: Optional[np.ndarray],
        plate: int,
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            np.arange(3),
        ).has_phenotypes_for_plate(plate) is expect

    @pytest.mark.parametrize("phenotypes,phenotype,expect", (
        (None, Phenotypes.GrowthLag, False),
        (np.array([None, {}]), Phenotypes.GrowthLag, False),
        (
            np.array([None, {Phenotypes.ColonySize48h: np.arange(3)}]),
            Phenotypes.GrowthLag,
            False,
        ),
        (
            np.array([{Phenotypes.GrowthLag: np.arange(3)}]),
            Phenotypes.GrowthLag,
            True,
        ),
    ))
    def test_has_phenotype_on_any_plate(
        self,
        phenotypes: Optional[np.ndarray],
        phenotype: Phenotypes,
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            np.arange(3),
        ).has_phenotype_on_any_plate(phenotype) is expect

    @pytest.mark.parametrize(
        "phenotypes,vector_meta_phenotypes,phenotype,expect",
        (
            (None, None, 'GrowthLag', False),
            (None, None, 'MeaningOfLife', False),
            (
                np.array([{Phenotypes.GrowthLag: np.arange(3)}]),
                None,
                'GrowthLag',
                True,
            ),
            (
                np.array([{Phenotypes.GrowthLag: np.arange(3)}]),
                None,
                Phenotypes.GrowthLag,
                True,
            ),
            (
                np.array([{Phenotypes.GrowthLag: np.arange(3)}]),
                None,
                Phenotypes.ChapmanRichardsFit,
                False,
            ),
            (
                np.array([{Phenotypes.GrowthLag: np.arange(3)}]),
                None,
                CurvePhaseMetaPhenotypes.Collapses,
                False,
            ),
            (
                None,
                np.array([{CurvePhaseMetaPhenotypes.Collapses: np.arange(3)}]),
                CurvePhaseMetaPhenotypes.Collapses,
                True,
            ),
            (
                None,
                np.array([{CurvePhaseMetaPhenotypes.Collapses: np.arange(3)}]),
                'Collapses',
                True,
            ),
        )
    )
    def test_has_phenotype(
        self,
        phenotypes: Optional[np.ndarray],
        vector_meta_phenotypes: Optional[np.ndarray],
        phenotype: Union[str,Phenotypes, CurvePhaseMetaPhenotypes],
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            np.arange(3),
            vector_meta_phenotypes=vector_meta_phenotypes,
        ).has_phenotype(phenotype) is expect

    @pytest.mark.parametrize("phenotype,normalized_phenotypes,expect", (
        (Phenotypes.ColonySize48h, None, False),
        (
            Phenotypes.ColonySize48h,
            np.array([None, {}]),
            False,
        ),
        (
            Phenotypes.ColonySize48h,
            np.array([None, {Phenotypes.ColonySize48h: np.arange(3)}]),
            True,
        ),
    ))
    def test_has_normalized_phenotype(
        self,
        phenotype: Phenotypes,
        normalized_phenotypes: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            None,
            np.arange(3),
            normalized_phenotypes=normalized_phenotypes
        ).has_normalized_phenotype(phenotype) is expect

    @pytest.mark.parametrize("normalized_phenotypes,expected", (
        (None, False),
        (np.array([]), False),
        (np.array([None, {}]), False),
        (
            np.array([None, {Phenotypes.ColonySize48h: np.array([])}]),
            False,
        ),
        (
            np.array([None, {Phenotypes.ColonySize48h: np.arange(3)}]),
            True,
        )
    ))
    def test_has_normalized_data(
        self,
        normalized_phenotypes: Optional[np.ndarray],
        expected: bool,
    ):
        assert PhenotyperState(
            None,
            np.arange(3),
            normalized_phenotypes=normalized_phenotypes,
        ).has_normalized_data() is expected

    @pytest.mark.parametrize("phenotypes,phenotype_filter,expect", (
        (None, None, False),
        (np.arange(3), None, False),
        (None, np.arange(3), False),
        (np.arange(2), np.arange(3), False),
        (np.arange(3), np.arange(3), True),
    ))
    def test_has_phenotype_filter(
        self,
        phenotypes: Optional[np.ndarray],
        phenotype_filter: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            phenotypes,
            np.arange(3),
            phenotype_filter=phenotype_filter,
        ).has_phenotype_filter() is expect

    @pytest.mark.parametrize("phenotype_filter,plate,expect", (
        (None, 3, False),
        (np.array([None, {}]), 0, False),
        (np.array([None, {}]), 1, False),
        (
            np.array([
                None,
                {Phenotypes.ColonySize48h: np.zeros((4, 4), dtype=int)},
            ]),
            1,
            False,
        ),
        (
            np.array([
                None,
                {Phenotypes.ColonySize48h: np.array([[0, 0], [1, 0]], dtype=int)},
            ]),
            1,
            True,
        ),
    ))
    def test_has_any_colony_removed_from_plate(
        self,
        phenotype_filter: Optional[np.ndarray],
        plate: int,
        expect: bool,
    ):
        assert PhenotyperState(
            None,
            np.arange(3),
            phenotype_filter=phenotype_filter,
        ).has_any_colony_removed_from_plate(plate) is expect

    @pytest.mark.parametrize("phenotype_filter,expect", (
        (None, False),
        (np.array([None]), False),
        (np.array([{}]), False),
        (
            np.array([
                None,
                {Phenotypes.ColonySize48h: np.zeros((4, 4), dtype=int)},
            ]),
            False,
        ),
        (
            np.array([
                {Phenotypes.ColonySize48h: np.zeros((4, 4), dtype=int)},
                {Phenotypes.ColonySize48h: np.array([[0, 0], [1, 0]], dtype=int)},
            ]),
            True,
        ),
    ))
    def test_has_any_colony_removed(
        self,
        phenotype_filter: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            None,
            np.arange(3),
            phenotype_filter=phenotype_filter,
        ).has_any_colony_removed() is expect

    @pytest.mark.parametrize("smooth_growth_data,expect", (
        (None, False),
        (np.array([None, np.zeros((2, 3, 4)), np.zeros((3, 4, 5))]), True),
        (
            np.array([
                np.zeros((1, 2, 3)),
                np.zeros((2, 3, 4)),
                np.zeros((3, 4, 5)),
            ]),
            False,
        ),
        (
            np.array([
                np.zeros((1, 2, 3)),
                np.zeros((2, 3, 4)),
                None,
            ]),
            False,
        ),
        (np.array([None, np.zeros((2, 3, 4)), np.zeros((2, 2, 2))]), False),
    ))
    def test_has_smooth_growth_data(
        self,
        smooth_growth_data: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            None,
            np.array([None, np.ones((2, 3, 4)), np.ones((3, 4, 5))]),
            smooth_growth_data=smooth_growth_data,
        ).has_smooth_growth_data() is expect

    def test_get_phenotype_raises_unknown_phenotype(self):
        with pytest.raises(ValueError, match='has not been extracted'):
            PhenotyperState(None, np.arange(3)).get_phenotype(
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
            )

    @pytest.mark.parametrize(
        "phenotypes,vector_meta_phenotypes,phenotype_filter,settings,"
        "phenotype,filtered,norm_state,reference_values,kwargs,expect",
        (
            (
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3)},
                ]),
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                False,
                NormState.Absolute,
                None,
                {},
                [],
            ),
        ),
    )
    def test_get_phenotype(
        self,
        phenotypes: Optional[np.ndarray],
        vector_meta_phenotypes: Optional[np.ndarray],
        phenotype_filter: Optional[np.ndarray],
        settings: PhenotyperSettings,
        phenotype: Union[Phenotypes, CurvePhaseMetaPhenotypes],
        filtered: bool,
        norm_state: NormState,
        reference_values: Optional[tuple[float, ...]],
        kwargs: dict[str, Any],
        expect: list[Optional[Union[FilterArray, np.ndarray]]],
    ):
        np.testing.assert_equal(
            PhenotyperState(
                phenotypes,
                np.arange(2),
                vector_meta_phenotypes=vector_meta_phenotypes,
                phenotype_filter=phenotype_filter,
            ).get_phenotype(
                settings,
                phenotype,
                filtered,
                norm_state,
                reference_values,
                **kwargs,
            ),
            expect,
        )
