from flask import Blueprint, jsonify

from ..io.rpc_client import get_client
from .general import convert_path_to_url, json_abort


blueprint = Blueprint('status_api', __name__)


@blueprint.route("/server")
def status_server():
    rpc_client = get_client()
    if rpc_client.online:
        return jsonify(**rpc_client.get_status())
    return json_abort(503, reason="System not ready")


@blueprint.route("/queue")
def status_queue():
    rpc_client = get_client()
    if rpc_client.online:
        return jsonify(queue=rpc_client.get_queue_status())
    return json_abort(503, reason="System not ready")


@blueprint.route("/jobs")
def status_jobs():
    rpc_client = get_client()
    if rpc_client.online:
        data = rpc_client.get_job_status()
        for item in data:
            if item['type'] == "Feature Extraction Job":
                item['label'] = convert_path_to_url("", item['label'])
            if 'log_file' in item and item['log_file']:
                item['log_file'] = convert_path_to_url(
                    "/logs/project",
                    item['log_file'],
                )
        return jsonify(jobs=data)
    return json_abort(503, reason="System not ready")


@blueprint.route("/scanners")
@blueprint.route("/scanners/<status_query>")
def status_scanners(status_query=None):
    rpc_client = get_client()
    if rpc_client.online:
        if status_query is None or status_query.lower() == 'all':
            return jsonify(scanners=rpc_client.get_scanner_status())
        if status_query.lower() == 'free':
            return jsonify(
                scanners={
                    s['socket']: s['scanner_name']
                    for s in rpc_client.get_scanner_status()
                    if 'owner' not in s or not s['owner']
                },
            )
        try:
            return jsonify(
                scanner=next((
                    s for s in rpc_client.get_scanner_status()
                    if status_query in s['scanner_name']
                )),
            )
        except StopIteration:
            return json_abort(
                400,
                reason=f"Unknown scanner or query '{status_query}'",
            )
    return json_abort(503, reason="System not ready")
