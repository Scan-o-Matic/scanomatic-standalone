from flask import jsonify, request

from scanomatic.io.jsonizer import dumps
from scanomatic.io.app_config import Config
from scanomatic.io.power_manager import POWER_MANAGER_TYPE
from scanomatic.models.validators.validate import get_invalid_names, validate

from .general import json_abort


def add_routes(app):

    @app.route("/api/settings", methods=['post'])
    def _settings_api():

        app_conf = Config()

        data_object = request.get_json(silent=True, force=True)
        if not data_object:
            data_object = request.values

        app_conf.number_of_scanners = data_object["number_of_scanners"]
        app_conf.power_manager.number_of_sockets = data_object[
            "power_manager"
        ]["sockets"]
        app_conf.power_manager.host = data_object["power_manager"]["host"]
        app_conf.power_manager.mac = data_object["power_manager"]["mac"]
        app_conf.power_manager.name = data_object["power_manager"]["name"]
        app_conf.power_manager.password = data_object[
            "power_manager"
        ]["password"]
        app_conf.power_manager.host = data_object["power_manager"]["host"]
        if "type" in data_object["power_manager"]:
            app_conf.power_manager.type = POWER_MANAGER_TYPE[
                data_object["power_manager"]["type"]
            ]
        app_conf.computer_human_name = data_object["computer_human_name"]
        app_conf.mail.warn_scanning_done_minutes_before = data_object[
            "mail"
        ]["warn_scanning_done_minutes_before"]
        settings = app_conf.application_settings
        app_conf.reload_settings()
        if validate(settings):
            app_conf.save_current_settings()
        else:
            bad_data = list(get_invalid_names(settings))
            return json_abort(400, reason="Bad data for {0}".format(bad_data))
        return jsonify()
