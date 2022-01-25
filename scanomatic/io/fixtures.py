import os
from typing import Optional, cast
from scanomatic.io.jsonizer import JSONSerializationError, dump, load_first
from scanomatic.io.logger import get_logger

from scanomatic.models.factories.fixture_factories import FixtureFactory
from scanomatic.models.fixture_models import FixtureModel

from .paths import Paths


class FixtureSettings:
    def __init__(self, name, dir_path=None, overwrite=False):
        self._logger = get_logger("Fixture {0}".format(name))
        path_name = Paths().get_fixture_path(name, only_name=True)
        if dir_path:
            conf_rel_path = Paths().fixture_conf_file_rel_pattern.format(
                path_name,
            )
            self._conf_path = os.path.join(dir_path, conf_rel_path)
        else:
            self._conf_path = Paths().get_fixture_path(name)
        self.model = self._load_model(name, overwrite)

    def _load_model(self, name, overwrite=False) -> FixtureModel:
        if overwrite:
            return FixtureFactory.create(path=self._conf_path, name=name)

        try:
            val = load_first(self._conf_path)
        except JSONSerializationError:
            self._logger.error(
                "Trying to load an outdated fixture at {0}, this won't work".format(  # noqa: E501
                    self._conf_path,
                ),
            )
            return FixtureFactory.create(path=self._conf_path, name=name)
        else:
            if val is None:
                return FixtureFactory.create(path=self._conf_path, name=name)
            else:
                return val

    def get_marker_positions(self) -> list[tuple[float, float]]:
        return list(zip(
            self.model.orientation_marks_x,
            self.model.orientation_marks_y
        ))

    @property
    def path(self) -> str:
        return self._conf_path

    def update_path_to_local_copy(self, local_directory) -> None:
        self._conf_path = os.path.join(
            local_directory,
            Paths().experiment_local_fixturename,
        )

    def get_marker_path(self) -> Optional[str]:
        paths = Paths()
        if self.model.orientation_mark_path:
            marker_paths: tuple[str, ...] = (
                self.model.orientation_mark_path,
                os.path.join(
                    paths.images,
                    os.path.basename(self.model.orientation_mark_path)
                ),
                paths.marker,
            )
        else:
            marker_paths = (paths.marker,)

        for path in marker_paths:
            try:
                with open(path, 'rb') as _:
                    self._logger.info("Using marker at '{0}'".format(path))
                    return path
            except IOError:
                self._logger.warning(
                    f"The designated orientation marker file does not exist ({path})",  # noqa: E501
                )
        return None

    def save(self) -> None:
        dump(
            self.model,
            self.path,
            merge=True,
        )


class Fixtures:
    def __init__(self):
        self._fixtures: Optional[dict[str, FixtureSettings]] = None
        self.update()

    def __getitem__(self, fixture: str) -> Optional[FixtureSettings]:
        if fixture in self:
            return cast(
                dict[str, FixtureSettings],
                self._fixtures,
            )[fixture]
        return None

    def __contains__(self, name: str) -> bool:
        return self._fixtures is not None and name in self._fixtures

    def update(self) -> None:
        directory = Paths().fixtures
        extension = ".config"

        list_fixtures = [
            x.split(extension, 1)[0] for x in
            [
                fixture for fixture in os.listdir(directory)
                if fixture.lower().endswith(extension)
            ]
        ]
        self._fixtures = {}
        for f in list_fixtures:
            if f.lower() != "fixture":
                fixture = FixtureSettings(f, directory)
                self._fixtures[fixture.model.name] = fixture

    def get_names(self) -> tuple[str, ...]:
        if self._fixtures is None:
            return tuple()

        return tuple(sorted(self._fixtures.keys()))

    def fill_model(self, model) -> None:
        fixture_name = model['fixture']
        if fixture_name in self:
            fixture = cast(
                FixtureSettings,
                self[fixture_name],
            )
            model['im-original-scale'] = fixture.model.scale
            model['fixture-file'] = fixture.path

        else:
            model['im-original-scale'] = 1.0
            model['im-scale'] = 1.0
            model['fixture-file'] = Paths().get_fixture_path(
                model['fixture'],
                only_name=True,
            )
