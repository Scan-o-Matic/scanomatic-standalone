import os
import time

import scanomatic.data_processing.phenotyper as phenotyper
import scanomatic.io.image_data as image_data
from scanomatic.io.jsonizer import dump, loads
import scanomatic.io.paths as paths
import scanomatic.models.factories.features_factory as feature_factory
from scanomatic.io.app_config import Config as AppConfig
from scanomatic.models.features_model import FeaturesModel
from scanomatic.models.rpc_job_models import JOB_TYPE, RPCjobModel

from . import proc_effector

SOM_MAIL_BODY = (
    """This is an automated email, please don't reply!

The project '{analysis_directory}' on """ + AppConfig().computer_human_name +
    """ has completed. Downstream analysis exists. All is done.
Hope you find cool results!

All the best,

Scan-o-Matic"""
)


class PhenotypeExtractionEffector(proc_effector.ProcessEffector):
    TYPE = JOB_TYPE.Features

    def __init__(self, job):

        self._paths = paths.Paths()
        self._feature_job: FeaturesModel = job.content_model
        logging_target = os.path.join(
            self._feature_job.analysis_directory,
            paths.Paths().phenotypes_extraction_log,
        )
        super(PhenotypeExtractionEffector, self).__init__(
            job,
            logger_name="Phenotype Extractor '{0}'".format(job.id),
            logging_target=logging_target,
        )

        self._job_label = self._feature_job.analysis_directory
        self._progress: float = 0.
        self._times = None
        self._data = None
        self._analysis_base_path = None
        self._phenotyper = None

    @property
    def progress(self) -> float:
        return 1. if self._progress is None else self._progress

    def setup(self, job):
        if self._started:
            self._logger.warning("Can't setup when started")
            return False

        job: RPCjobModel = loads(job)
        self._feature_job: FeaturesModel = job.content_model
        self._job.content_model = self._feature_job

        if feature_factory.FeaturesFactory.validate(self._feature_job) is True:
            dump(
                self._feature_job,
                os.path.join(
                    self._feature_job.analysis_directory,
                    paths.Paths().phenotypes_extraction_instructions,
                ),
                overwrite=True,
            )
        else:
            self._logger.warning("Can't setup, instructions don't validate")
            return False

        self._logger.info("Loading files image data from '{0}'".format(
            self._feature_job.analysis_directory,
        ))

        if (
            self._feature_job.extraction_data
            is feature_factory.features_model.FeatureExtractionData.State
        ):
            self._times = None
            self._data = None
        else:
            times, data = image_data.ImageData.read_image_data_and_time(
                self._feature_job.analysis_directory,
            )

            if (
                times is None
                or data is None
                or 0 in list(map(len, (times, data)))
            ):
                self._logger.error(
                    "Could not filter image times to match data or no data. "
                    "Do you have the right directory, it should be an analysis directory?"  # noqa: E501
                )

                self.add_message(
                    "There is no image data in given directory or "
                    "the image data is corrupt"
                )

                self._running = False
                self._stopping = True
                return False

            self._times = times
            self._data = data

        self._analysis_base_path = self._feature_job.analysis_directory

        self._allow_start = True

    def __next__(self) -> bool:
        if self.waiting:
            return super().__next__()

        if self._stopping:
            self._progress = None
            self._running = False

        if self._iteration_index is None:
            self._setup_extraction_iterator()

        if not self._paused and self._running:
            try:
                self._progress = next(self._phenotype_iterator)
            except StopIteration:
                self._running = False
                self._progress = None
            self._logger.info(
                "One phenotype extraction iteration completed. "
                f"Resume {self._running}"
            )

        if not self._running:
            if not self._stopping:
                self._phenotyper.save_state(
                    self._analysis_base_path,
                    ask_if_overwrite=False,
                )
                self._phenotyper.save_phenotypes(
                    dir_path=self._analysis_base_path,
                    ask_if_overwrite=False,
                )

            self._mail(
                "Scan-o-Matic: Feature extraction of '{analysis_directory}' completed",  # noqa: E501
                SOM_MAIL_BODY,
                self._feature_job,
            )

            raise StopIteration

        return True

    def _setup_extraction_iterator(self):
        self._start_time = time.time()
        if (
            self._feature_job.extraction_data
            is feature_factory.features_model.FeatureExtractionData.State
        ):
            self._phenotyper = phenotyper.Phenotyper.LoadFromState(
                self._feature_job.analysis_directory,
            )
        else:
            self._phenotyper = phenotyper.Phenotyper(
                raw_growth_data=self._data,
                times_data=self._times,
            )
        self._phenotype_iterator = self._phenotyper.iterate_extraction(
            self._feature_job.try_keep_qc,
        )
        self._iteration_index = 1
        self._logger.info("Starting phenotype extraction")
