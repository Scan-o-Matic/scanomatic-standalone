from flask import Flask, jsonify

from ..io.rpc_client import _ClientProxy
from .general import convert_path_to_url, json_abort


def add_routes(app: Flask, rpc_client: _ClientProxy):

    @app.route("/api/status/server")
    def status_server():
        if rpc_client.online:
            return jsonify(**rpc_client.get_status())
        return json_abort(
            503,
            reason="System not yet ready",
        )

    @app.route("/api/status/queue")
    def status_queue():
        if rpc_client.online:
            return jsonify(queue=rpc_client.get_queue_status())
        return json_abort(
            503,
            reason="System not yet ready",
        )

    @app.route("/api/status/jobs")
    def status_jobs():
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
        return json_abort(
            503,
            reason="System not yet ready",
        )

    @app.route("/api/status/scanners")
    @app.route("/api/status/scanners/<status_query>")
    def status_scanners(status_query=None):
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
        return json_abort(
            503,
            reason="System not yet ready",
        )
