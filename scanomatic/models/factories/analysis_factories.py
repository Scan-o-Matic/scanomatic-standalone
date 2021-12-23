import os
from typing import Mapping, Optional, cast
from collections.abc import Sequence

import scanomatic.models.analysis_model as analysis_model
from scanomatic.data_processing.calibration import (
    get_polynomial_coefficients_from_ccc
)
from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer,
)


class GridModelFactory(AbstractModelFactory):
    MODEL = analysis_model.GridModel
    STORE_SECTION_SERIALIZERS = {
        'use_utso': bool,
        "median_coefficient": float,
        "manual_threshold": float,
        "gridding_offsets": list,
        "reference_grid_folder": str,
        "grid": (tuple, tuple, float)
    }

    @classmethod
    def create(cls, **settings) -> analysis_model.GridModel:
        return cast(analysis_model.GridModel, super().create(**settings))


class AnalysisModelFactory(AbstractModelFactory):
    MODEL = analysis_model.AnalysisModel
    _SUB_FACTORIES = {
        analysis_model.GridModel: GridModelFactory
    }
    STORE_SECTION_SERIALIZERS = {
        'compilation': str,
        'compile_instructions': str,
        'pinning_matrices': (tuple, tuple, int),
        'use_local_fixture': bool,
        'email': email_serializer,
        'stop_at_image': int,
        'output_directory': str,
        'focus_position': tuple,
        'suppress_non_focal': bool,
        'animate_focal': bool,
        'one_time_positioning': bool,
        'one_time_grayscale': bool,
        'grid_images': list,
        'grid_model': analysis_model.GridModel,
        'image_data_output_measure': analysis_model.MEASURES,
        'image_data_output_item': analysis_model.COMPARTMENTS,
        'chain': bool,
        'plate_image_inclusion': (tuple, str),
        'cell_count_calibration': (tuple, float),
        'cell_count_calibration_id': str,
    }

    @classmethod
    def create(cls, **settings) -> analysis_model.AnalysisModel:
        if (
            not settings.get('cell_count_calibration_id', None)
            and not settings.get('cell_count_calibration', None)
        ):
            settings['cell_count_calibration_id'] = 'default'

        if (not settings.get('cell_count_calibration', None)):
            settings['cell_count_calibration'] = (
                get_polynomial_coefficients_from_ccc(
                    settings['cell_count_calibration_id'],
                )
            )
        return cast(analysis_model.AnalysisModel, super().create(**settings))

    @classmethod
    def set_absolute_paths(cls, model: analysis_model.AnalysisModel):
        base_path = os.path.dirname(model.compilation)
        model.compile_instructions = cls._get_absolute_path(
            model.compile_instructions,
            base_path,
        )
        model.output_directory = cls._get_absolute_path(
            model.output_directory,
            base_path,
        )

    @classmethod
    def _get_absolute_path(cls, path: str, base_path: str) -> str:
        if os.path.abspath(path) != path:
            return os.path.join(base_path, path)
        return path

    @classmethod
    def all_keys_valid(cls, keys):
        # Remove outdated but allowed
        keys = tuple(key for key in keys if key != 'xml_model')

        # Add introduced but not mandatory
        keys = set(keys).union((
            'cell_count_calibration_id',
            'cell_count_calibration',
        ))
        return super().all_keys_valid(keys)

    @classmethod
    def set_default(
        cls,
        model: analysis_model.AnalysisModel,
        fields: Optional[list[analysis_model.AnalysisModelFields]] = None,
    ) -> None:
        if cls.verify_correct_model(model):
            default_model = cls.MODEL()

            for attr, val in default_model:
                try:
                    field = analysis_model.AnalysisModelFields[attr]
                    if (fields is None or field in fields):
                        setattr(model, attr, val)
                except KeyError:
                    pass


class AnalysisFeaturesFactory(AbstractModelFactory):
    MODEL = analysis_model.AnalysisFeatures
    STORE_SECTION_SERIALIZERS = {
        "index": object,
        "data": object,
        "shape": (tuple, int)
    }

    @classmethod
    def create(
        cls,
        children=None,
        data_type=None,
        **settings,
    ) -> analysis_model.AnalysisFeatures:
        return cast(
            analysis_model.AnalysisFeatures,
            super().create(**settings),
        )

    @classmethod
    def deep_to_dict(cls, model_or_data):
        if isinstance(model_or_data, cls.MODEL):
            return {
                k: cls.deep_to_dict(model_or_data[k]) for k in
                cls.to_dict(model_or_data)
            }
        elif isinstance(model_or_data, Mapping):
            return {
                k: cls.deep_to_dict(model_or_data[k]) for k in model_or_data
            }
        elif isinstance(model_or_data, Sequence):
            return [cls.deep_to_dict(v) for v in model_or_data]
        else:
            return model_or_data
