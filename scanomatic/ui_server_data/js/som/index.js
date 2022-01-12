// export * from 'bootstrap';
// export * from 'bootstrap-toggle';
// export d3 from 'd3';
// export $ from 'jquery';
// export * from 'jquery-modal';
// export * from 'jquery-treetable';
// export * from 'jquery-ui';
// export Spinner from 'spin';

/* Scan-o-Matic API */

export {
  analysisToggleLocalFixture,
  createSelector,
  hideGridImage,
  loadGridImage,
  setFixturePlateListing,
  setRegriddingSourceDirectory,
  setAnalysisDirectory,
  setFilePath,
  Analyse,
  Extract,
  BioscreenExtract,
} from './analysis';

export {
  compileToggleLocalFixture,
  setFixtureStatus,
  setOnAllImages,
  setProjectDirectory,
  toggleManualSelectionBtn,
  Compile,
} from './compile';

export {
  cacheDescription,
  formatMinutes,
  formatTime,
  setActivePlate,
  setAux,
  setAuxTime,
  setExperimentRoot,
  setPoetry,
  updateFixture,
  updateScans,
  StartExperiment,
} from './experiment';

export {
  addFixture,
  clearAreas,
  detectMarkers,
  drawFixture,
  getFixture,
  getFixtures,
  setCanvas,
  RemoveFixture,
  SaveFixture,
  SetAllowDetect,
} from './fixtures';

export { LoadGrayscales } from './grayscales';

export {
  setVersionInformation,
  InputEnabled,
} from './helpers';

export {
  BrowsePath,
  BrowseProjectsRoot,
  GetAPILock,
  GetExperimentGrowthData,
  GetExport,
  GetMarkExperiment,
  GetNormalizeProject,
  GetPhenotypesPlates,
  GetPlateData,
  GetProjectRuns,
  GetReferenceOffsets,
  GetRunPhenotypePath,
  GetRunPhenotypes,
  RemoveLock,
} from './qc_normAPIHelper';

export { default as DrawCurves } from './qc_normDrawCurves';

export {
  getValidSymbol,
  DrawPlate,
} from './qc_normDrawPlate';

export { default as getFreeScanners } from './scanners';

export {
  dynamicallyLimitScanners,
  toggleVisibilities,
  UpdateSettings,
} from './settings';

export {
  jobsStatusFormatter,
  queueStatusFormatter,
  scannerStatusFormatter,
  serverStatusFormatter,
  stopDialogue,
  updateStatus,
} from './status';


/* External dependencies */

window.$ = require('jquery');
window.d3 = require('d3');

// export * from 'bootstrap';
// export * from 'bootstrap-toggle';
export * from 'jquery-modal';
export * from 'jquery-treetable';
export * from 'jquery-ui';
export { Spinner } from 'spin';
