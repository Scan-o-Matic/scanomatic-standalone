from typing import cast

import psutil

from scanomatic.io.logger import get_logger

from . import app_config


class Resource_Status:
    _LOGGER = get_logger("Hardware Status")
    _APP_CONFIG = app_config.Config()
    _passes = 0

    @classmethod
    def loggingLevel(cls, val: int) -> None:
        cls._LOGGER.setLevel(val)

    @staticmethod
    def currentPasses() -> int:
        return Resource_Status._passes

    @staticmethod
    def check_cpu() -> bool:
        """Checks the CPU status.

        Checks if enough cores (Analysis_Queue.MIN_FREE_CPU_CORES)
        fulfills the usage the criteria
        (Analysis_Queue.MIN_FREE_CPU_PERCENT).
        """

        cur_cpus = cast(
            list[float],
            psutil.cpu_percent(percpu=True),
        )

        free_cpus = [
            cpu < Resource_Status._APP_CONFIG.hardware_resource_limits.cpu_single_free  # noqa: E501
            for cpu in cur_cpus
        ]

        Resource_Status._LOGGER.info(
            "CPUs: "
            ", ".join([
                "(({0}%, {1})".format(
                    p,
                    ['FREE', 'TAKEN'][not f]
                ) for p, f in zip(cur_cpus, free_cpus)
            ]),
        )

        cpuOK = (
            sum(free_cpus)
            >= Resource_Status._APP_CONFIG.hardware_resource_limits.cpu_free_count  # noqa: E501
            and sum(100 - curCpu for curCpu in cur_cpus)
            > Resource_Status._APP_CONFIG.hardware_resource_limits.cpu_total_percent_free  # noqa: E501
        )

        Resource_Status._LOGGER.info(
            "CPUs: {0}".format(['OK', 'NOK'][not cpuOK]),
        )

        return cpuOK

    @staticmethod
    def check_mem() -> bool:
        """Checks if Phyical Memory status

        Checks if the memory percent usage is below
        Analysis_Queue,MAX_MEM_USAGE.
        """

        memUsage = psutil.virtual_memory().percent

        memOK = (
            (100 - memUsage)
            > Resource_Status._APP_CONFIG.hardware_resource_limits.memory_minimum_percent  # noqa: E501
        )

        Resource_Status._LOGGER.info(
            "MEM: {0}%, {1}".format(
                memUsage,
                ["OK", "NOT OK"][not memOK]
            ),
        )
        return memOK

    @staticmethod
    def check_resources(consume_checks: bool = False) -> bool:
        """Checks if both memory and cpu are OK for poping.

        At least MIN_SUCCESS_PASSES is needed for both checks
        in a row before True is passed
        """

        val = Resource_Status.check_mem() and Resource_Status.check_cpu()
        target = (
            Resource_Status._APP_CONFIG.hardware_resource_limits.checks_pass_needed  # noqa: E501
        )
        if val:
            Resource_Status._passes += 1
        else:
            Resource_Status._passes = 0

        Resource_Status._LOGGER.info(
            "System Resource check passed {0}/{1}".format(
                Resource_Status._passes,
                target,
            ),
        )

        ret = Resource_Status._passes >= target
        if ret and consume_checks:
            Resource_Status._passes = 0
        return ret
