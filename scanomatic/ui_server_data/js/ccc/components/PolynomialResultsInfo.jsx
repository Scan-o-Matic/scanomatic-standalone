import PropTypes from 'prop-types';
import React from 'react';
import CCCPropTypes from '../prop-types';

export default function PolynomialResultsInfo({ polynomial }) {
  return (
    <div className="results">
      <h3>Cell Count Calibration Polynomial</h3>
      <ul className="list-group">
        <li className="list-group-item">
          <h4 className="list-group-item-heading">
            Polynomial
          </h4>
          <PolynomialEquation
            coefficients={polynomial.coefficients}
          />
        </li>
        <li className="list-group-item">
          <h4 className="list-group-item-heading">
            Colonies included
          </h4>
          {` ${polynomial.colonies} `}
          colonies
        </li>
      </ul>
    </div>
  );
}

PolynomialResultsInfo.propTypes = {
  polynomial: CCCPropTypes.polynomialShape,
};

PolynomialResultsInfo.defaultProps = {
  polynomial: undefined,
};

export function PolynomialEquation({ coefficients }) {
  let poly = [];
  const polyPower = coefficients.length - 1;
  coefficients.forEach((coeff, position) => {
    if (coeff !== 0) {
      const power = polyPower - position;
      const x = power === 0 ? null : <span className="variable">x</span>;
      const pwr = power === 0 || power === 1 ? null : <sup>{power}</sup>;
      poly.push((
        <span key={`power-${power}`}>
          <ScientificNotation value={coeff} precision={4} />
          {x}
          {pwr}
        </span>
      ));
    }
  });

  for (let i = poly.length - 1; i > 0; i -= 1) {
    poly.splice(i, 0, <span key={`plus-${i}`}> + </span>);
  }

  if (poly.length === 0) {
    poly = 0;
  }

  return (
    <p className="math">
      <span className="variable">y</span>
      {' = '}
      {poly}
    </p>
  );
}

PolynomialEquation.propTypes = {
  coefficients: PropTypes.arrayOf(PropTypes.number).isRequired,
};

export function numberAsScientific(value) {
  const exponent = Math.floor(Math.log10(Math.abs(value)));
  const coefficient = value * (10 ** -exponent);
  return { exponent, coefficient };
}

export function ScientificNotation({ value, precision }) {
  if (value === 0) {
    return <span>{value.toPrecision(precision)}</span>;
  }
  const { exponent, coefficient } = numberAsScientific(value);
  if (exponent > -2 && exponent < 3) {
    return <span>{value.toPrecision(precision)}</span>;
  }
  return (
    <span>
      {coefficient.toPrecision(precision)}
      &times;
      <span>
        10
        <sup>{exponent.toFixed(0)}</sup>
      </span>
    </span>
  );
}

ScientificNotation.propTypes = {
  value: PropTypes.number.isRequired,
  precision: PropTypes.number.isRequired,
};
