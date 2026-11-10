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

    # --- Turn on/off: host-side agent (server-services-checker/service_control.py) ---

    @http.route("/server_services/control/poll", type="http", auth="public",
                methods=["GET"], csrf=False, save_session=False)
    def control_poll(self):
        """Every controllable service (to report power) and the pending on/off requests."""
        if not self._authorized():
            return request.make_json_response({"error": "forbidden"}, status=403)
        services = request.env["server.service"].sudo().search([]).filtered("can_control")
        return request.make_json_response({
            "services": [s._control_target() for s in services],
            "requests": [
                dict(s._control_target(), action=s.control_request)
                for s in services.filtered("control_request")
            ],
        })

    @http.route("/server_services/control/report", type="http", auth="public",
                methods=["POST"], csrf=False, save_session=False)
    def control_report(self):
        if not self._authorized():
            return request.make_json_response({"error": "forbidden"}, status=403)
        try:
            payload = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return request.make_json_response({"error": "invalid json"}, status=400)
        if not isinstance(payload, dict):
            return request.make_json_response({"error": "invalid json"}, status=400)
        Service = request.env["server.service"].sudo()
        powers = dict(Service._fields["power"].selection)
        for item in payload.get("power") or []:
            service = Service.browse(int(item.get("id", 0))).exists()
            if service and item.get("power") in powers and service.power != item["power"]:
                service.power = item["power"]
        for item in payload.get("done") or []:
            service = Service.browse(int(item.get("id", 0))).exists()
            if service:
                service._apply_control_result(bool(item.get("ok")), str(item.get("message", "")))
        return request.make_json_response({"ok": True})
