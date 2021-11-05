import PropTypes from 'prop-types';
import React from 'react';

import CCCPropTypes from '../prop-types';

export default class ImageUpload extends React.Component {
  constructor(props) {
    super(props);
    this.handleFileChange = this.handleFileChange.bind(this);
  }

  handleFileChange(event) {
    const { target: { files } } = event;
    this.props.onImageChange(files[0]);
  }

  render() {
    let inputOrProgress;
    if (this.props.progress) {
      const progressWidth =
                100 * (this.props.progress.now / this.props.progress.max);
      inputOrProgress = (
        <div>
          <div className="progress">
            <div
              className="progress-bar"
              style={{ width: `${progressWidth}%` }}
            />
          </div>
          {this.props.progress.text}
        </div>
      );
    } else {
      inputOrProgress = (
        <input type="file" onChange={this.handleFileChange} />
      );
    }
    return (
      <div className="ImageUpload">
        <h3>Process new image</h3>
        {inputOrProgress}
      </div>
    );
  }
}

ImageUpload.propTypes = {
  onImageChange: PropTypes.func.isRequired,
  progress: CCCPropTypes.progressShape,
};

ImageUpload.defaultProps = {
  progress: undefined,
};
