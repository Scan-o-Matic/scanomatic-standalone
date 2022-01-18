import warnings

import numpy as np
from scipy.ndimage import (  # type: ignore
    binary_dilation,
    binary_erosion,
    gaussian_filter,
    median_filter
)
from skimage import filters as ski_filter  # type: ignore

from scanomatic.data_processing.convolution import FilterArray


class AnalysisRecipeAbstraction:
    """Holds an instruction and/or a list of subinstructions."""

    def __init__(
        self,
        parent: "AnalysisRecipeAbstraction" = None,
        description: str = "",
    ):
        self.analysis_order: list["AnalysisRecipeAbstraction"] = [self]
        self.description = description
        if parent is not None:
            parent.add_analysis(self)

    def __str__(self) -> str:
        return self.description

    def __repr__(self) -> str:
        return "<{0} {1}>".format(id(self), self.description)

    def analyse(
        self,
        im: np.ndarray,
        filter_array: FilterArray,
        base_level: bool = True,
    ) -> None:
        if base_level:
            im = im.copy()
            filter_array[...] = False

        for analysis in self.analysis_order:
            if analysis is self:
                self._do(im, filter_array)
            else:
                analysis.analyse(im, filter_array, base_level=False)

    def add_analysis(
        self,
        analysis: "AnalysisRecipeAbstraction",
        pos: int = -1,
    ) -> None:
        if pos == -1:
            self.analysis_order.append(analysis)
        else:
            self.analysis_order.insert(pos, analysis)

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        pass


class AnalysisRecipeEmpty(AnalysisRecipeAbstraction):

    def __init__(self, parent: "AnalysisRecipeAbstraction" = None):

        super(AnalysisRecipeEmpty, self).__init__(
            parent,
            description="Recipe",
        )

        self.analysis_order = []


class AnalysisThresholdOtsu(AnalysisRecipeAbstraction):
    def __init__(
        self,
        parent: "AnalysisRecipeAbstraction",
        threshold_unit_adjust: float = 0.0,
    ):
        super(AnalysisThresholdOtsu, self).__init__(
            parent,
            description="Otsu Threshold",
        )

        self._thresholdUnitAdjust = threshold_unit_adjust

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        try:
            filter_array[...] = (
                im < ski_filter.threshold_otsu(im) + self._thresholdUnitAdjust
            )
        except (ValueError, TypeError) as error:
            warnings.warn(
                'Otsu method failed. Error was {}'.format(str(error))
            )
            filter_array[...] = False


class AnalysisRecipeErode(AnalysisRecipeAbstraction):
    kernel = np.array([
        [0, 0, 1, 0, 0],
        [0, 1, 1, 1, 0],
        [1, 1, 1, 1, 1],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 0, 0]
    ])

    def __init__(self, parent: "AnalysisRecipeAbstraction"):
        super(AnalysisRecipeErode, self).__init__(
            parent,
            description="Binary Erode",
        )

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        filter_array[...] = binary_erosion(filter_array, iterations=3)


class AnalysisRecipeErodeSmall(AnalysisRecipeAbstraction):
    kernel = np.array([
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0]
    ])

    def __init__(self, parent: "AnalysisRecipeAbstraction"):
        super(AnalysisRecipeErodeSmall, self).__init__(
            parent,
            description="Binary Erode (small)",
        )

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        binary_erosion(
            filter_array,
            origin=(1, 1),
            output=filter_array,
            structure=self.kernel,
        )


class AnalysisRecipeDilate(AnalysisRecipeAbstraction):
    kernel = np.array([
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 0],
        [0, 0, 1, 1, 1, 0, 0]
    ])

    def __init__(
        self,
        parent: "AnalysisRecipeAbstraction",
        iterations: int = 4,
    ):
        super(AnalysisRecipeDilate, self).__init__(
            parent,
            description="Binary Dilate",
        )
        self._iterations = iterations

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        filter_array[...] = binary_dilation(
            filter_array,
            iterations=self._iterations,
        )


class AnalysisRecipeGauss2(AnalysisRecipeAbstraction):
    def __init__(self, parent: "AnalysisRecipeAbstraction"):
        super(AnalysisRecipeGauss2, self).__init__(
            parent,
            description="Gaussian size 2",
        )

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        gaussian_filter(im, 2, output=im)


class AnalysisRecipeMedianFilter(AnalysisRecipeAbstraction):
    def __init__(self, parent: "AnalysisRecipeAbstraction"):
        super(AnalysisRecipeMedianFilter, self).__init__(
            parent,
            description="Median Filter",
        )

    def _do(self, im: np.ndarray, filter_array: FilterArray) -> None:
        median_filter(
            im,
            size=(3, 3),
            mode="nearest",
            output=im,
        )
