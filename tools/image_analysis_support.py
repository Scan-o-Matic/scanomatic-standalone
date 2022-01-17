from scanomatic.generics import Model


class VersionChangesModel(Model):
    def __init__(self, **kwargs):
        self.first_pass_change_1: float = 0.997
        self.oldest_allow_fixture: float = 0.9991
        super().__init__()


def get_active_plates(
    meta_data: dict,
    suppress_analysis: bool,
    graph_watch: Sequence,
    versions: VersionChangesModel,
):
    """Makes list of only relevant plates according to how
    analysis was started"""

    plate_position_keys = []

    if meta_data['Version'] >= versions.first_pass_change_1:
        v_offset = 1
    else:
        v_offset = 0

    for i in range(len(meta_data['Pinning Matrices'])):
        if (
            (suppress_analysis is False or graph_watch[0] == i)
            and meta_data['Pinning Matrices'][i] is not None
        ):
            plate_position_keys.append("plate_{0}_area".format(i + v_offset))

    plates = len(plate_position_keys)

    return plates, plate_position_keys
