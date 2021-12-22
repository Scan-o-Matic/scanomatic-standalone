import glob
import os
import re
from typing import cast

from scanomatic.generics.abstract_model_factory import (
    AbstractModelFactory,
    email_serializer
)
from scanomatic.models import compile_project_model, fixture_models
from scanomatic.models.factories import fixture_factories


class CompileImageFactory(AbstractModelFactory):
    MODEL = compile_project_model.CompileImageModel
    STORE_SECTION_SERIALIZERS = {
        'index': int,
        'time_stamp': float,
        'path': str
    }

    @classmethod
    def create(cls, **settings) -> compile_project_model.CompileImageModel:
        model = cast(
            compile_project_model.CompileImageModel,
            super(CompileImageFactory, cls).create(**settings)
        )
        if not model.time_stamp:
            cls.set_time_stamp_from_path(model)

        if model.index < 0:
            cls.set_index_from_path(model)

        return model

    @classmethod
    def set_time_stamp_from_path(
        cls,
        model: compile_project_model.CompileImageModel,
    ):
        match = re.search(r'(\d+\.\d+)\.tiff$', model.path)
        if match:
            model.time_stamp = float(match.groups()[0])

    @classmethod
    def set_index_from_path(
        cls,
        model: compile_project_model.CompileImageModel,
    ) -> None:
        match = re.search(r'_(\d+)_(\d+\.\d+)\.tiff$', model.path)
        if match:
            model.index = int(match.groups()[0])


class CompileProjectFactory(AbstractModelFactory):
    MODEL = compile_project_model.CompileInstructionsModel
    _SUB_FACTORIES = {
        compile_project_model.CompileImageModel: CompileImageFactory,
    }
    STORE_SECTION_SERIALIZERS = {
        'compile_action': compile_project_model.COMPILE_ACTION,
        'images': (tuple, compile_project_model.CompileImageModel),
        'path': str,
        'start_condition': str,
        'email': email_serializer,
        'start_time': float,
        'fixture_type': compile_project_model.FIXTURE,
        'fixture_name': str,
        'overwrite_pinning_matrices': (tuple, tuple, int),
        'cell_count_calibration_id': str,
    }

    @classmethod
    def create(
        cls,
        **settings,
    ) -> compile_project_model.CompileInstructionsModel:
        return cast(
            compile_project_model.CompileInstructionsModel,
            super(CompileProjectFactory, cls).create(**settings),
        )

    @classmethod
    def dict_from_path_and_fixture(
        cls,
        path: str,
        fixture=None,
        is_local=None,
        compile_action=compile_project_model.COMPILE_ACTION.Initiate,
        **kwargs,
    ) -> dict:
        path = path.rstrip("/")

        if path != os.path.abspath(path):
            cls.get_logger().error("Not an absolute path, aborting")
            return {}

        if is_local is None:
            is_local = not fixture

        image_path = os.path.join(path, "*.tiff")

        images = [
            {'path': p, 'index': i}
            for i, p in enumerate(sorted(glob.glob(image_path)))
        ]

        return cls.to_dict(cls.create(
            compile_action=compile_action.name,
            images=images,
            fixture_type=(
                is_local and compile_project_model.FIXTURE.Local.name
                or compile_project_model.FIXTURE.Global.name
            ),
            fixture_name=fixture,
            path=path,
            **kwargs,
        ))


class CompileImageAnalysisFactory(AbstractModelFactory):
    MODEL = compile_project_model.CompileImageAnalysisModel
    _SUB_FACTORIES = {
        compile_project_model.CompileImageModel: CompileImageFactory,
        fixture_models.FixtureModel: fixture_factories.FixtureFactory
    }
    STORE_SECTION_SERIALIZERS = {
        'image': compile_project_model.CompileImageModel,
        'fixture': fixture_models.FixtureModel
    }

    @classmethod
    def create(
        cls,
        **settings,
    ) -> compile_project_model.CompileImageAnalysisModel:
        return cast(
            compile_project_model.CompileImageAnalysisModel,
            super(CompileImageAnalysisFactory, cls).create(**settings),
        )
