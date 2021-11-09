from dataclasses import asdict
from typing import Any, List, Dict, Optional, Union, Tuple

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
from scanomatic.io.meta_data import MetaData2


def check_none(
    key: str,
    value: Optional[Any],
    expect_none: bool,
) -> Optional[str]:
    if (value is None) is expect_none:
        return None
    return f"{key} expected {value} to {'' if value else 'not'} equal None"


def assert_state_none_fields(
    state: PhenotyperState,
    none_fields: Tuple[str, ...],
):
    errors = []
    for key, value in asdict(state).items():
        if err := check_none(key, value, key in none_fields):
            errors.append(err)
    assert errors == []


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
    @pytest.fixture
    def state(self):
        return PhenotyperState(
            np.array([]),
            np.array([]),
            normalized_phenotypes=np.ndarray([]),
            meta_data=MetaData2(tuple()),
            phenotype_filter=np.array([]),
            phenotype_filter_undo=tuple(),
            smooth_growth_data=np.ndarray([]),
            times_data=np.ndarray([]),
            vector_meta_phenotypes=np.array([]),
            vector_phenotypes=np.array([]),
        )

    @pytest.mark.parametrize("raw_growth_data,expect", (
        (np.ones((1, 10)), [Offsets.UpperRight()]),
        (np.arange(2), [Offsets.LowerRight(), Offsets.LowerRight()]),
    ))
    def test_init_makes_reference_surface_positions_when_not_matching(
        self,
        raw_growth_data: np.ndarray,
        expect: List[Offsets],
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
                np.array([
                    None,
                    np.ones((12, 24, 33)),
                    None,
                    np.ones((42, 9)),
                ], dtype=object),
            ).plate_shapes
        ) == (None, (12, 24), None, (42, 9))

    @pytest.mark.parametrize("plate,shape", ((0, None), (1, (12, 24))))
    def test_get_plate_shapes(
        self,
        plate: int,
        shape: Optional[Tuple[int, int]],
    ):
        assert PhenotyperState(
            None,
            np.array([
                None,
                np.ones((12, 24, 33)),
                None,
                np.ones((42, 9))
            ], dtype=object),
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
        (np.array([None, np.arange(3)], dtype=object), 0, False),
        (np.array([None, np.arange(3)], dtype=object), 1, True),
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
        phenotype: Union[str, Phenotypes, CurvePhaseMetaPhenotypes],
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
                {
                    Phenotypes.ColonySize48h: (
                        np.array([[0, 0], [1, 0]], dtype=int)
                    ),
                },
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
                {
                    Phenotypes.ColonySize48h: (
                        np.array([[0, 0], [1, 0]], dtype=int)
                    ),
                },
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
        (
            np.array([
                None,
                np.zeros((2, 3, 4)),
                np.zeros((3, 4, 5)),
            ], dtype=object),
            True,
        ),
        (
            np.array([
                np.zeros((1, 2, 3)),
                np.zeros((2, 3, 4)),
                np.zeros((3, 4, 5)),
            ], dtype=object),
            False,
        ),
        (
            np.array([
                np.zeros((1, 2, 3)),
                np.zeros((2, 3, 4)),
                None,
            ], dtype=object),
            False,
        ),
        (
            np.array([
                None,
                np.zeros((2, 3, 4)),
                np.zeros((2, 2, 2)),
            ], dtype=object),
            False,
        ),
    ))
    def test_has_smooth_growth_data(
        self,
        smooth_growth_data: Optional[np.ndarray],
        expect: bool,
    ):
        assert PhenotyperState(
            None,
            np.array([
                None,
                np.ones((2, 3, 4)),
                np.ones((3, 4, 5)),
            ], dtype=object),
            smooth_growth_data=smooth_growth_data,
        ).has_smooth_growth_data() is expect

    def test_get_phenotype_raises_unknown_phenotype(self):
        with pytest.raises(ValueError, match='has not been extracted'):
            PhenotyperState(None, np.arange(3)).get_phenotype(
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
            )

    @pytest.mark.parametrize(
        "phenotypes,vector_meta_phenotypes,normalized_phenotypes,"
        "phenotype_filter,settings,phenotype,filtered,norm_state,"
        "reference_values,kwargs,expect",
        (
            (  # Unfiltered
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3)},
                ]),
                None,
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
                [None, np.arange(6).reshape(2, 3)],
            ),
            (  # Filtered
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3)},
                ]),
                None,
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                True,
                NormState.Absolute,
                None,
                {},
                [
                    None,
                    FilterArray(
                        np.arange(6).reshape(2, 3),
                        np.arange(6).reshape(2, 3) < 2,
                    ),
                ],
            ),
            (  # NormalizedRelative (though norm not exists)
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3)},
                ]),
                None,
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                True,
                NormState.NormalizedRelative,
                None,
                {},
                [None, None],
            ),
            (  # NormalizedAbsoluteBatched (though norm not exists)
                np.array([
                    None,
                    {
                        Phenotypes.ColonySize48h:
                            np.arange(6).reshape(2, 3).astype(float)
                    },
                ]),
                None,
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                True,
                NormState.NormalizedAbsoluteBatched,
                None,
                {},
                [None, None],
            ),
            (  # NormalizedAbsoluteNonBatched (though norm not exists)
                np.array([
                    None,
                    {
                        Phenotypes.ColonySize48h:
                            np.arange(6).reshape(2, 3).astype(float)
                    },
                ]),
                None,
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                True,
                NormState.NormalizedAbsoluteNonBatched,
                [10, 11],
                {},
                [None, None],
            ),
            (  # kwarg overriding normstate to be Absolute
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3)},
                ]),
                None,
                None,
                np.array([
                    None,
                    {Phenotypes.ColonySize48h: np.arange(6).reshape(2, 3) < 2},
                ]),
                PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
                Phenotypes.ColonySize48h,
                False,
                NormState.NormalizedAbsoluteNonBatched,
                None,
                {'normalized': False},
                [
                    None,
                    np.arange(6).reshape(2, 3),
                ],
            ),
        ),
    )
    def test_get_phenotype(
        self,
        phenotypes: Optional[np.ndarray],
        vector_meta_phenotypes: Optional[np.ndarray],
        normalized_phenotypes: Optional[np.ndarray],
        phenotype_filter: Optional[np.ndarray],
        settings: PhenotyperSettings,
        phenotype: Union[Phenotypes, CurvePhaseMetaPhenotypes],
        filtered: bool,
        norm_state: NormState,
        reference_values: Optional[Tuple[float, ...]],
        kwargs: Dict[str, Any],
        expect: List[Optional[Union[FilterArray, np.ndarray]]],
    ):
        actual = PhenotyperState(
            phenotypes,
            np.arange(2),
            vector_meta_phenotypes=vector_meta_phenotypes,
            normalized_phenotypes=normalized_phenotypes,
            phenotype_filter=phenotype_filter,
        ).get_phenotype(
            settings,
            phenotype,
            filtered,
            norm_state,
            reference_values,
            **kwargs,
        )
        errors = []
        for i, (actual_plate, expect_plate) in enumerate(zip(actual, expect)):
            if actual_plate is None and expect_plate is None:
                continue
            if isinstance(actual_plate, FilterArray):
                if actual_plate.equals(expect_plate):
                    continue
                errors.append(
                    f"Index {i} mismatch {actual_plate} != {expect_plate}",
                )
            elif isinstance(expect_plate, FilterArray):
                if not expect_plate.equals(actual_plate):
                    continue
                errors.append(
                    f"Index {i} mismatch {actual_plate} != {expect_plate}",
                )
            else:
                try:
                    np.testing.assert_equal(actual_plate, expect_plate)
                except AssertionError:
                    errors.append(
                        f"Index {i} mismatch {actual_plate} != {expect_plate}",
                    )
        assert errors == []

    def test_get_reference_median(self):
        plate = np.random.standard_normal((10, 10))
        plate[1::2, 1::2] += 11
        assert PhenotyperState(
            np.array([
                None,
                {},
                {Phenotypes.ColonySize48h: np.array([])},
                {Phenotypes.ColonySize48h: plate},
            ]),
            np.zeros((4, 10, 10)),
        ).get_reference_median(
            PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
            Phenotypes.ColonySize48h,
        ) == (None, None, None, pytest.approx(11, abs=1.))

    @pytest.mark.parametrize("keep_filter,expect_filters_none", (
        (False, True),
        (True, False),
    ))
    def test_wipe_extracted_phenotypes(
        self,
        keep_filter: bool,
        expect_filters_none: bool,
        state: PhenotyperState,
    ):
        state.wipe_extracted_phenotypes(keep_filter)
        assert_state_none_fields(
            state,
            (
                    'phenotypes',
                    'vector_phenotypes',
                    'vector_meta_phenotypes',
            ) + (
                ('phenotype_filter', 'phenotype_filter_undo') if
                expect_filters_none else tuple()
            )
        )

    def test_init_remove_filter_and_undo_actions_clears_filter_if_no_phenotypes(  # noqa: E501
        self,
        state: PhenotyperState,
    ):
        state.phenotypes = None
        state.init_remove_filter_and_undo_actions(
            PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
        )
        assert_state_none_fields(
            state,
            (
                'phenotypes',
                'phenotype_filter',
                'phenotype_filter_undo',
            ),
        )

    def test_init_remove_filter_and_undo_no_filter(
        self,
        state: PhenotyperState,
    ):
        state.phenotype_filter = None
        state.init_remove_filter_and_undo_actions(
            PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
        )
        assert_state_none_fields(state, tuple())

    def test_init_remove_filter_and_undo_no_undo(self, state: PhenotyperState):
        state.phenotype_filter_undo = None
        state.init_remove_filter_and_undo_actions(
            PhenotyperSettings(1, 2, 3, PhenotypeDataType.Trusted, 4, 5),
        )
        assert_state_none_fields(state, tuple())
