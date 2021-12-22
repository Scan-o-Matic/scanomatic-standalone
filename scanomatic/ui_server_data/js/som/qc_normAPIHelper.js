import * as d3 from 'd3';

import { getLastSegmentOfPath } from './qc_normHelper';
// var baseUrl = "http://localhost:5000";
const baseUrl = '';
const BrowseRootPath = `${baseUrl}/api/results/browse`;
const NormalizeRefOffsets = `${baseUrl}/api/results/normalize/reference/offsets`;
const NormalizeProjectUrl = `${baseUrl}/api/results/normalize`;
const branchSymbol = '¤';

// let lock;

export function BrowseProjectsRoot(callback) {
  const path = BrowseRootPath;

  d3.json(path, (error, json) => {
    if (error) {
      callback(null);
      return console.warn(error);
    }
    const { names, urls } = json;
    const len = names.length;
    const projects = [];
    for (let i = 0; i < len; i += 1) {
      const projectUrl = urls[i];
      let projectName;
      if (names[i] == null) {
        projectName = `[${getLastSegmentOfPath(projectUrl)}]`;
      } else {
        projectName = names[i];
      }
      const project = { name: projectName, url: projectUrl };
      projects.push(project);
    }
    callback(projects);
    return null;
  });
}

export function BrowsePath(url, callback) {
  const path = baseUrl + url.replace(branchSymbol, '');

  d3.json(path, (error, json) => {
    if (error) return console.warn(error);

    const { names, urls } = json;
    const isProject = json.is_project;
    const len = names.length;
    const paths = [];
    for (let i = 0; i < len; i += 1) {
      const folder = getLastSegmentOfPath(urls[i]);
      const filePath = { name: `${names[i]} [${folder}]`, url: urls[i] };
      paths.push(filePath);
    }
    let projectDetails = '';
    if (isProject) {
      projectDetails = {
        analysis_date: json.analysis_date,
        analysis_instructions: json.analysis_instructions,
        change_date: json.change_date,
        extraction_date: json.extraction_date,
        phenotype_names: json.phenotype_names,
        phenotype_normalized_names: json.phenotype_normalized_names,
        project_name: json.project_name,
        project: json.project,
        add_lock: json.add_lock,
        remove_lock: json.remove_lock,
        export_phenotypes: json.export_phenotypes,
      };
    }
    const browse = { isProject, paths, projectDetails };
    callback(browse);
    return null;
  });
}

export function GetProjectRuns(url, callback) {
  const path = baseUrl + url;

  d3.json(path, (error, json) => {
    if (error) return console.warn(error);

    const { names, urls } = json;
    const len = names.length;
    const projects = [];
    for (let i = 0; i < len; i += 1) {
      const folder = getLastSegmentOfPath(urls[i]);
      const project = { name: `${names[i]} [${folder}]`, url: urls[i] };
      projects.push(project);
    }
    callback(projects);
    return null;
  });
}

function addCacheBuster(first) {
  if (first === true) { return `?buster=${Math.random().toString(36).substring(7)}`; }
  return `&buster=${Math.random().toString(36).substring(7)}`;
}

export function GetAPILock(url, callback) {
  if (url) {
    const path = `${baseUrl + url}/${addCacheBuster(true)}`;
    d3.json(path, (error, json) => {
      if (error) {
        return console.warn(error);
      }

      let permissionText;
      let lock;
      if (json.success === true) {
        lock = json.lock_key;
        permissionText = 'Read/Write';
      } else {
        permissionText = 'Read Only';
        lock = null;
      }
      const lockData = {
        lock_key: lock,
        lock_state: permissionText,
      };
      callback(lockData);
      return null;
    });
  }
}

function addKeyParameter(key) {
  if (key) { return `?lock_key=${key}${addCacheBuster()}`; }
  return '';
}

export function GetRunPhenotypePath(url, key, callback) {
  const path = baseUrl + url + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    const phenoPath = json.phenotype_names;
    callback(phenoPath);
    return null;
  });
}

export function RemoveLock(url, key, callback) {
  const path = baseUrl + url + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json.success);
    return null;
  });
}

export function GetRunPhenotypes(url, key, callback) {
  const path = baseUrl + url + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    const phenotypes = [];
    for (let i = 0; i < json.phenotypes.length; i += 1) {
      phenotypes.push({ name: json.names[i], url: json.phenotype_urls[i] });
    }
    callback(phenotypes);
    return null;
  });
}

export function GetPhenotypesPlates(url, key, callback) {
  const path = baseUrl + url + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    const plates = [];
    for (let i = 0; i < json.urls.length; i += 1) {
      plates.push({ index: json.plate_indices[i], url: json.urls[i] });
    }
    callback(plates);
    return null;
  });
}
function GetGtPlateData(url, placeholder, key, isNormalized, callback) {
  const path = baseUrl + url.replace(placeholder, 'GenerationTime') + addKeyParameter(key);

  if (isNormalized === true) callback(null);
  console.log(`Metadata GTWhen Path:${path}`);
  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json.data);
    return null;
  });
}

function GetGtWhenPlateData(url, placeholder, key, isNormalized, callback) {
  const path = baseUrl + url.replace(placeholder, 'GenerationTimeWhen') + addKeyParameter(key);

  if (isNormalized === true) callback(null);
  console.log(`Metadata GTWhen Path:${path}`);
  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json.data);
    return null;
  });
}

function GetYieldPlateData(url, placeholder, key, isNormalized, callback) {
  const path = baseUrl + url.replace(placeholder, 'ExperimentGrowthYield') + addKeyParameter(key);

  if (isNormalized === true) callback(null);
  console.log(`Metadata yield path:${path}`);
  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json.data);
    return null;
  });
}

export function GetPlateData(
  url,
  isNormalized,
  metaDataPath,
  phenotypePlaceholderMetaDataPath,
  key,
  callback,
) {
  const path = baseUrl + url + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }

    if (json.success === false) {
      alert(`Could not display the data! \n${json.reason}`);
      callback(null);
    } else {
      GetGtPlateData(
        metaDataPath,
        phenotypePlaceholderMetaDataPath,
        key,
        isNormalized,
        (gtData) => {
          GetGtWhenPlateData(
            metaDataPath,
            phenotypePlaceholderMetaDataPath,
            key,
            isNormalized,
            (gtWhenData) => {
              GetYieldPlateData(
                metaDataPath,
                phenotypePlaceholderMetaDataPath,
                key,
                isNormalized,
                (yieldData) => {
                  const qIdxCols = json.qindex_cols;
                  const qIdxRows = json.qindex_rows;
                  const qIdxSort = [];
                  if (qIdxCols.length === qIdxRows.length) {
                    let idx = 0;
                    for (let i = 0; i < qIdxRows.length; i += 1) {
                      qIdxSort.push({ idx, row: qIdxRows[i], col: qIdxCols[i] });
                      idx += 1;
                    }
                  }
                  const plate = {
                    plate_data: json.data,
                    plate_phenotype: json.phenotype,
                    plate_qIdxSort: qIdxSort,
                    Plate_metadata: {
                      plate_BadData: json.BadData,
                      plate_Empty: json.Empty,
                      plate_NoGrowth: json.NoGrowth,
                      plate_UndecidedProblem: json.UndecidedProblem,
                    },
                    Growth_metaData: {
                      gt: isNormalized === true ? null : gtData,
                      gtWhen: isNormalized === true ? null : gtWhenData,
                      yld: isNormalized === true ? null : yieldData,
                    },
                  };
                  callback(plate);
                },
              );
            },
          );
        },
      );
    }
    return null;
  });
}

export function GetExperimentGrowthData(plateUrl, key, callback) {
  const path = baseUrl + plateUrl + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json);
    return null;
  });
}

export function GetMarkExperiment(plateUrl, key, callback) {
  const path = baseUrl + plateUrl + addKeyParameter(key);

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json);
    return null;
  });
}

export function GetNormalizeProject(projectPath, key, callback) {
  const path = `${NormalizeProjectUrl}/${projectPath}${addKeyParameter(key)}`;

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }
    callback(json);
    return null;
  });
}

export function GetExport(url, callback) {
  const path = baseUrl + url;

  $.ajax({
    url: path,
    type: 'POST',
    dataType: 'json',
    contentType: 'application/json',
    success(data) {
      console.log(`API:${JSON.stringify(data)}`);
      callback(data);
    },
    error(data) {
      console.log(`API ERROR: ${JSON.stringify(data)}`);
      callback(data);
    },
  });
}

export function GetReferenceOffsets(callback) {
  const path = NormalizeRefOffsets;

  d3.json(path, (error, json) => {
    if (error) {
      return console.warn(error);
    }

    const names = json.offset_names;
    const values = json.offset_values;
    const len = names.length;
    const offsets = [];
    for (let i = 0; i < len; i += 1) {
      const ofset = { name: names[i], value: values[i] };
      offsets.push(ofset);
    }
    callback(offsets);
    return null;
  });
}
