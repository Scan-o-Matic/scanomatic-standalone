import PropTypes from 'prop-types';

const arrayOf2D = propType => PropTypes.arrayOf(PropTypes.arrayOf(propType));

const pinningFormat = PropTypes.shape({
  name: PropTypes.string.isRequired,
  nRows: PropTypes.number.isRequired,
  nCols: PropTypes.number.isRequired,
});

const cccMetadata = PropTypes.shape({
  id: PropTypes.string.isRequired,
  accessToken: PropTypes.string.isRequired,
  species: PropTypes.string.isRequired,
  reference: PropTypes.string.isRequired,
  fixtureName: PropTypes.string.isRequired,
  pinningFormat: pinningFormat.isRequired,
});

const plateShape = PropTypes.shape({
  imageId: PropTypes.string.isRequired,
  imageName: PropTypes.string.isRequired,
  plateId: PropTypes.number.isRequired,
});

const polynomialShape = PropTypes.shape({
  coefficients: PropTypes.arrayOf(PropTypes.number).isRequired,
  colonies: PropTypes.number.isRequired,
});

const resultsDataShape = PropTypes.shape({
  calculated: PropTypes.arrayOf(PropTypes.number).isRequired,
  independentMeasurements: PropTypes.arrayOf(PropTypes.number).isRequired,
});

const coloniesShape = PropTypes.shape({
  pixelValues: arrayOf2D(PropTypes.number).isRequired,
  pixelCounts: arrayOf2D(PropTypes.number).isRequired,
  independentMeasurements: PropTypes.arrayOf(PropTypes.number).isRequired,
  maxCount: PropTypes.number.isRequired,
  maxPixelValue: PropTypes.number.isRequired,
  minPixelValue: PropTypes.number.isRequired,
});

const colonyDataShape = PropTypes.shape({
  image: arrayOf2D(PropTypes.number),
  imageMin: PropTypes.number,
  imageMax: PropTypes.number,
  blob: arrayOf2D(PropTypes.bool),
  background: arrayOf2D(PropTypes.bool),
});

const correlationShape = PropTypes.shape({
  slope: PropTypes.number.isRequired,
  intercept: PropTypes.number.isRequired,
  stderr: PropTypes.number.isRequired,
});

const progressShape = PropTypes.shape({
  now: PropTypes.number.isRequired,
  max: PropTypes.number.isRequired,
  text: PropTypes.string.isRequired,
});

const selectedColonyShape = PropTypes.shape({
  row: PropTypes.number,
  col: PropTypes.number,
});

const gridShape = arrayOf2D(PropTypes.arrayOf(PropTypes.number));

export default {
  cccMetadata,
  pinningFormat,
  plateShape,
  polynomialShape,
  resultsDataShape,
  coloniesShape,
  colonyDataShape,
  correlationShape,
  progressShape,
  selectedColonyShape,
  gridShape,
};
