import http.client as HTTPStatus
from datetime import timedelta
from hashlib import sha256

from flask import current_app
from flask_restful import Resource, abort, inputs, reqparse
from werkzeug.datastructures import FileStorage

from scanomatic.io.scanstore import UnknownProjectError
from scanomatic.models.scan import Scan


class ScanCollection(Resource):
    reqparser = reqparse.RequestParser()
    reqparser.add_argument(
        'project',
        type=inputs.regex(r'^\w+(/\w+)*$'),
        required=True,
    )
    reqparser.add_argument('scan_index', type=inputs.natural, required=True)
    reqparser.add_argument('timedelta', type=inputs.natural, required=True)
    reqparser.add_argument(
        'image',
        type=FileStorage,
        location='files',
        required=True,
    )
    reqparser.add_argument('digest', type=str, required=True)

    def post(self):
        args = self.reqparser.parse_args()
        self._validate_image(args.image, args.digest)
        args.image.seek(0)
        scan = Scan(
            image=args.image,
            index=args.scan_index,
            timedelta=timedelta(seconds=args.timedelta),
        )
        try:
            current_app.config['scanstore'].add_scan(args.project, scan)
        except UnknownProjectError:
            abort(HTTPStatus.BAD_REQUEST)
        return '', HTTPStatus.CREATED

    def _validate_image(self, image, digest):
        message = {}
        if image.content_type != 'image/tiff':
            message['image'] = (
                f'Unexpected image format {image.content_type}'
            )
        image_digest = sha256(image.read()).hexdigest()
        if digest != image_digest:
            message['digest'] = (
                f'invalid image digest: expected {image_digest}, got {digest}'
            )
        if message:
            abort(HTTPStatus.BAD_REQUEST, message=message)
