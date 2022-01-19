import PropTypes from 'prop-types';
import React from 'react';

import PlateEditorContainer from '../containers/PlateEditorContainer';
import ImageUploadContainer from '../containers/ImageUploadContainer';
import PolynomialConstructionContainer from '../containers/PolynomialConstructionContainer';
import CCCPropTypes from '../prop-types';
import CCCInfoBox from './CCCInfoBox';

export default function CCCEditor(props) {
  const {
    cccMetadata, currentPlate, onFinishPlate, onFinishUpload, onFinalizeCCC,
  } = props;
  return (
    <div>
      <div className="row">
        <div className="col-md-6">
          <h1>Initiated CCC</h1>
          <CCCInfoBox cccMetadata={cccMetadata} />
        </div>
      </div>
      {props.plates.map((plate, i) => (
        <PlateEditorContainer
          key={`${plate.imageId}:${plate.plateId}`}
          {...plate}
          cccMetadata={cccMetadata}
          onFinish={onFinishPlate}
          collapse={currentPlate !== i}
        />
      ))}
      <ImageUploadContainer
        cccMetadata={cccMetadata}
        onFinish={onFinishUpload}
      />
      <PolynomialConstructionContainer
        cccMetadata={cccMetadata}
        onFinalizeCCC={onFinalizeCCC}
      />
    </div>
  );
}

CCCEditor.propTypes = {
  cccMetadata: CCCPropTypes.cccMetadata.isRequired,
  plates: PropTypes.arrayOf(CCCPropTypes.plateShape).isRequired,
  currentPlate: PropTypes.number,
  onFinalizeCCC: PropTypes.func.isRequired,
  onFinishPlate: PropTypes.func.isRequired,
  onFinishUpload: PropTypes.func.isRequired,
};

CCCEditor.defaultProps = {
  currentPlate: undefined,
};
