from flask import Flask, jsonify
from matplotlib.pyplot import get

from ..io.rpc_client import _ClientProxy, get_client

from .general import convert_path_to_url, json_abort
from flask import g


def add_routes(app: Flask):

    @app.before_request
    def do_rpc():
        if 'rpc' not in g:
            g.rpc = get_client()

    @app.route("/api/status/server")
    def status_server():
        if g.rpc.online:
            return jsonify(**g.rpc.get_status())
        return json_abort(503, reason="System not ready")

    @app.route("/api/status/queue")
    def status_queue():
        if g.rpc.online:
            return jsonify(queue=g.rpc.get_queue_status())
        return json_abort(503, reason="System not ready")

    @app.route("/api/status/jobs")
    def status_jobs():
        if g.rpc.online:
            data = g.rpc.get_job_status()
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

    @app.route("/api/status/scanners")
    @app.route("/api/status/scanners/<status_query>")
    def status_scanners(status_query=None):
        if g.rpc.online:
            if status_query is None or status_query.lower() == 'all':
                return jsonify(scanners=g.rpc.get_scanner_status())
            if status_query.lower() == 'free':
                return jsonify(
                    scanners={
                        s['socket']: s['scanner_name']
                        for s in g.rpc.get_scanner_status()
                        if 'owner' not in s or not s['owner']
                    },
                )
            try:
                return jsonify(
                    scanner=next((
                        s for s in g.rpc.get_scanner_status()
                        if status_query in s['scanner_name']
                    )),
                )
            except StopIteration:
                return json_abort(
                    400,
                    reason=f"Unknown scanner or query '{status_query}'",
                )
        return json_abort(503, reason="System not ready")
