import os
import time
from typing import Any, Optional, cast
from scanomatic.io.jsonizer import dump, dump_to_stream, loads

import scanomatic.io.rpc_client as rpc_client
from scanomatic.image_analysis import first_pass
from scanomatic.io.app_config import Config as AppConfig
from scanomatic.io.fixtures import Fixtures, FixtureSettings
from scanomatic.io.paths import Paths
from scanomatic.models.compile_project_model import (
    COMPILE_ACTION,
    FIXTURE,
    CompileImageModel,
    CompileInstructionsModel
)
from scanomatic.models.factories.analysis_factories import AnalysisModelFactory
from scanomatic.models.rpc_job_models import JOB_TYPE, RPCjobModel
from scanomatic.models.validators.validate import validate

from . import proc_effector

SOM_MAIL_BODY_NO_ANALYSIS = (
    """This is an automated email, please don't reply!

The project '{path}' on """ + AppConfig().computer_human_name +
    """ has completed. No downstream analysis requested.

All the best,

Scan-o-Matic"""
)
SOM_MAIL_BODY_ANALYSIS_REFUSED = (
    """This is an automated email, please don't reply!

The project '{path}' on """ + AppConfig().computer_human_name +
    """ has completed.

*** Downstream analysis was refused. ***

All the best,

Scan-o-Matic"""
)


class CompileProjectEffector(proc_effector.ProcessEffector):

    TYPE = JOB_TYPE.Compile

    def __init__(self, job: RPCjobModel):

        self._compile_job: CompileInstructionsModel = job.content_model
        logging_target = (
            Paths().get_project_compile_log_path_from_compile_model(
                self._compile_job,
            )
        )
        super(CompileProjectEffector, self).__init__(
            job,
            logger_name="Compile Effector",
            logging_target=logging_target,
        )
        self._job_label = os.path.basename(self._compile_job.path)
        self._image_to_analyse = 0
        self._fixture_settings: Optional[FixtureSettings] = None
        self._compile_instructions_path: Optional[str] = None
        self._has_mailed_issues = False
        self._allowed_calls['progress'] = self.progress

    @property
    def progress(self) -> float:
        if self._compile_job.images:
            return self._image_to_analyse / len(self._compile_job.images)
        return 0

    def setup(self, job):

        self._logger.info("Setup called")

        self._compile_job = cast(
            CompileInstructionsModel,
            cast(
                RPCjobModel,
                loads(job),
            ).content_model,
        )
        self._job.content_model = self._compile_job

        if self._compile_job.images is None:
            self._compile_job.images = tuple()

        self._logger.info("Doing setup")
        self._logger.info(f"Action {self._compile_job.compile_action}")
        self._compile_instructions_path = (
            Paths().get_project_compile_instructions_path_from_compile_model(
                self._compile_job,
            )
        )
        if (
            self._compile_job.compile_action == COMPILE_ACTION.Initiate
            or self._compile_job.compile_action
            == COMPILE_ACTION.InitiateAndSpawnAnalysis
        ):

            # Empty files
            try:
                os.remove(self._compile_instructions_path)
            except OSError:
                pass

            dump(
                self._compile_job,
                self._compile_instructions_path
            )

        self._logger.info(
            f"{len(self._compile_job.images)} Images included in compilations",
        )
        self._tweak_path()
        self._load_fixture()
        self._allow_start = True

        if self._fixture_settings is None:
            self._logger.critical(
                "No fixture loaded, name probably not recognized or old fixture settings file",  # noqa: E501
            )
            self._stopping = True

        self._start_time = time.time()

    def _load_fixture(self):
        if self._compile_job.fixture_type is FIXTURE.Global:
            self._fixture_settings = Fixtures()[self._compile_job.fixture_name]
            if (
                self._fixture_settings
                and self._compile_job.compile_action in (
                    COMPILE_ACTION.Initiate,
                    COMPILE_ACTION.InitiateAndSpawnAnalysis
                )
            ):
                self._fixture_settings.update_path_to_local_copy(
                    os.path.dirname(self._compile_job.path),
                )
                self._fixture_settings.save()

        else:
            dir_path = os.path.dirname(self._compile_job.path)
            self._logger.info(
                f"Attempting to load local fixture copy in directory {dir_path}",  # noqa: E501
            )
            self._fixture_settings = FixtureSettings(
                Paths().experiment_local_fixturename,
                dir_path=dir_path,
            )

    def _tweak_path(self):
        self._compile_job.path = (
            Paths().get_project_compile_path_from_compile_model(
                self._compile_job
            )
        )

    def __next__(self) -> bool:
        if self.waiting:
            return super().__next__()

        if self._stopping:
            raise StopIteration()
        elif self._image_to_analyse < len(self._compile_job.images):
            self._analyse_image(
                self._compile_job.images[self._image_to_analyse]
            )
            self._image_to_analyse += 1
            return True
        elif (
            self._compile_job.compile_action
            is COMPILE_ACTION.AppendAndSpawnAnalysis
            or self._compile_job.compile_action
            is COMPILE_ACTION.InitiateAndSpawnAnalysis
        ):
            self._spawn_analysis()
            self.enact_stop()
            raise StopIteration
        else:
            self.enact_stop()
            raise StopIteration

    def _analyse_image(self, compile_image_model: CompileImageModel):
        assert self._fixture_settings is not None
        try:
            with self._compile_output_filehandle as fh:
                issues: dict[str, Any] = {}
                try:
                    image_model = first_pass.analyse(
                        compile_image_model,
                        self._fixture_settings,
                        issues=issues,
                    )
                    if validate(image_model):
                        dump_to_stream(
                            image_model,
                            fh,
                            as_if_appending=True,
                        )
                except first_pass.MarkerDetectionFailed:
                    self._logger.error(
                        "Failed to detect the markers on {0} using fixture {1}".format(  # noqa: E501
                            compile_image_model.path,
                            self._fixture_settings.model.path
                        ),
                    )
                except IOError:
                    self._logger.error(
                        "Could not output analysis of {0} to {1}".format(
                            compile_image_model.path,
                            fh.name,
                        ),
                    )
                if issues and not self._has_mailed_issues:
                    self._mail_issues(issues)

        except IOError:
            self._logger.critical(
                f"Could not write to project file {self._compile_job.path}",
            )

    def _mail_issues(self, issues: dict[str, Any]):
        self._has_mailed_issues = True
        self._mail(
            "Scan-o-Matic: Problems compiling project '{path}'",
            "This is an automated email, please don't reply!"
            "\n\n"
            "The project '{path}' on """ + AppConfig().computer_human_name +
            " has experienced a problems with compiling the current project."
            "\n\n" +
            (
                f"* Image seems rotated ({issues['rotation']} radians).\n"
                if 'rotation' in issues else ""
            ) +
            "* Part of calibrated fixture falls outside image ({0}).\n".format(
                issues['overflow'] if isinstance(issues['overflow'], str)
                else "Plate {0}".format(issues["overflow"])
            ) if 'overflow' in issues else ""
            "\n\n"
            "All the best,"
            "\n\n"
            "Scan-o-Matic",
            self._compile_job,
        )

    @property
    def _compile_output_filehandle(self):
        fh_mode = 'r+'
        if (
            (
                self._compile_job.compile_action is COMPILE_ACTION.Initiate
                or self._compile_job.compile_action
                is COMPILE_ACTION.InitiateAndSpawnAnalysis
            ) and self._image_to_analyse == 0
        ):
            fh_mode = 'w+'

        try:
            return open(self._compile_job.path, fh_mode)

        except IOError as e:
            self._stopping = True
            raise e

    def enact_stop(self) -> None:
        self._stopping = True
        self._mail(
            "Scan-o-Matic: Compilation of '{path}' completed",
            SOM_MAIL_BODY_NO_ANALYSIS,
            self._compile_job,
        )

    def _spawn_analysis(self) -> bool:
        assert self._fixture_settings is not None
        analysis_model = AnalysisModelFactory.create(
            chain=True,
            compile_instructions=self._compile_instructions_path,
            compilation=self._compile_job.path,
            email=self._compile_job.email,
            cell_count_calibration_id=(
                self._compile_job.cell_count_calibration_id
            ),
        )

        if self._compile_job.overwrite_pinning_matrices:
            analysis_model.pinning_matrices = (
                self._compile_job.overwrite_pinning_matrices
            )

        if (
            analysis_model.pinning_matrices
            and len(analysis_model.pinning_matrices)
            != len(self._fixture_settings.model.plates)
        ):

            self._logger.warning(
                "Suggested pinnings are {0} but known plates are {1}".format(
                   analysis_model.pinning_matrices,
                   [p.index for p in self._fixture_settings.model.plates],
                ),
            )

            accepted_indices = tuple(
                p.index for p in self._fixture_settings.model.plates
            )
            analysis_model.pinning_matrices = tuple(
                pm for i, pm in enumerate(analysis_model.pinning_matrices)
                if i + 1 in accepted_indices
            )
            self._logger.warning(
                "Reduced pinning matrices instructions to {0} because lacking plates in fixture".format(  # noqa: E501
                    analysis_model.pinning_matrices,
                ),
            )

        if rpc_client.get_client().create_analysis_job(
            AnalysisModelFactory.to_dict(analysis_model)
        ):
            self._logger.info("Enqueued analysis")
            return True

        else:

            self._mail(
                "Scan-o-Matic: Compilation of '{path}' completed",
                SOM_MAIL_BODY_ANALYSIS_REFUSED,
                self._compile_job
            )

            self._logger.warning("Enquing analysis was refused")
            return False
