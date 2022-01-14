import $ from 'jquery';
import 'bootstrap';
import 'bootstrap-toggle';
import * as d3 from 'd3';
import 'jquery-modal';
import 'jquery-treetable';
import 'jquery-ui';
// CSS
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap-toggle/css/bootstrap-toggle.css';
import 'jquery-ui-dist/jquery-ui.css';
import 'jquery-modal/jquery.modal.css';
import 'jquery-treetable/css/jquery.treetable.css';
import 'jquery-treetable/css/jquery.treetable.theme.default.css';

/* External dependencies */
window.$ = $;
window.jQuery = $;
window.d3 = d3;
export { default as Spinner } from 'spin';

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
  toggleManualRegridding,
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
  validateExperiment,
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
  getSharedValue,
  setVersionInformation,
  setSharedValue,
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
  addSymbolToSVG,
  getValidSymbol,
  plateMetaDataType,
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
