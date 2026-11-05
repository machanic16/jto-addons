import hmac
import json

from odoo import http
from odoo.http import request


class ServerServicesChecker(http.Controller):
    """Endpoints for the host-side status checker (cron script on the server).

    Protected by a secret token stored in the system parameter
    jto_server_services.checker_token and sent in the X-Checker-Token header.
    Blocked for public (Funnel) visitors by the nginx front proxy as well.
    """

    def _authorized(self):
        expected = request.env["ir.config_parameter"].sudo().get_str(
            "jto_server_services.checker_token"
        )
        given = request.httprequest.headers.get("X-Checker-Token", "")
        return bool(expected) and hmac.compare_digest(expected, given)

    @http.route("/server_services/checker/targets", type="http", auth="public",
                methods=["GET"], csrf=False, save_session=False)
    def targets(self):
        if not self._authorized():
            return request.make_json_response({"error": "forbidden"}, status=403)
        services = request.env["server.service"].sudo().search([])
        return request.make_json_response([s._checker_target() for s in services])

    @http.route("/server_services/checker/results", type="http", auth="public",
                methods=["POST"], csrf=False, save_session=False)
    def results(self):
        if not self._authorized():
            return request.make_json_response({"error": "forbidden"}, status=403)
        try:
            payload = json.loads(request.httprequest.get_data() or b"[]")
        except ValueError:
            return request.make_json_response({"error": "invalid json"}, status=400)
        Service = request.env["server.service"].sudo()
        updated = 0
        for item in payload if isinstance(payload, list) else []:
            service = Service.browse(int(item.get("id", 0))).exists()
            if service:
                service._apply_check_result(bool(item.get("ok")), str(item.get("detail", "")))
                updated += 1
        return request.make_json_response({"updated": updated})
