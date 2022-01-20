import PropTypes from 'prop-types';
import React from 'react';

import { GetFixturePlates } from '../api';
import CCCPropTypes from '../prop-types';
import CCCEditor from '../components/CCCEditor';

export default class CCCEditorContainer extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      plates: [],
      currentPlate: null,
      ready: false,
    };
    this.handleFinishUpload = this.handleFinishUpload.bind(this);
    this.handleFinishPlate = this.handleFinishPlate.bind(this);
  }

  componentDidMount() {
    GetFixturePlates(this.props.cccMetadata.fixtureName)
      .then((plates) => {
        this.setState({ ready: true, platesPerImage: plates.length });
      });
  }

  handleFinishUpload(newImage) {
    const currentState = this.state;
    const plates = [...currentState.plates];
    for (let i = 1; i <= currentState.platesPerImage; i += 1) {
      const newPlate = {
        imageId: newImage.id,
        imageName: newImage.name,
        plateId: i,
      };
      plates.push(newPlate);
    }
    const currentPlate = (
      currentState.currentPlate == null
        ? currentState.plates.length
        : currentState.currentPlate
    );
    this.setState({
      plates,
      currentPlate,
    });
  }

  handleFinishPlate() {
    const currentState = this.state;
    const currentPlate = (
      currentState.currentPlate < currentState.plates.length - 1
        ? currentState.currentPlate + 1
        : null
    );
    this.setState({ currentPlate });
  }

  render() {
    return (
      <CCCEditor
        cccMetadata={this.props.cccMetadata}
        plates={this.state.plates}
        currentPlate={this.state.currentPlate}
        onFinalizeCCC={this.props.onFinalizeCCC}
        onFinishUpload={this.handleFinishUpload}
        onFinishPlate={this.handleFinishPlate}
        ready={this.state.ready}
      />
    );
  }
}

CCCEditorContainer.propTypes = {
  cccMetadata: CCCPropTypes.cccMetadata.isRequired,
  onFinalizeCCC: PropTypes.func.isRequired,
};
