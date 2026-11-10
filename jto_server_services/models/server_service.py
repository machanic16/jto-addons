import time
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

STALE_AFTER = timedelta(minutes=10)
# A turn on/off request the host control agent hasn't picked up in this time is dropped.
CONTROL_TIMEOUT = timedelta(minutes=2)
# How long the button waits for the agent before giving the page back.
CONTROL_WAIT_SECONDS = 25
# Containers that run this Odoo: never turned on/off from Odoo itself.
PROTECTED_TARGETS = {"odoo20-odoo-1", "odoo20-db-1", "odoo20-nginx-1"}


class ServerService(models.Model):
    _name = "server.service"
    _description = "Server Service"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("business", "Business"),
            ("media", "Media"),
            ("security", "Security cameras"),
            ("photos", "Photos"),
            ("system", "System"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )
    url = fields.Char("URL", required=True, help="Address to open the service.")
    check_url = fields.Char(
        "Check URL",
        help="Address the status checker tests, if different from the URL. "
        "Use http(s)://... or tcp://host:port. Leave empty to test the URL.",
    )
    access = fields.Selection(
        [
            ("public", "Public internet"),
            ("tailnet", "Tailnet only"),
            ("lan", "Home network"),
            ("local", "This server only"),
        ],
        required=True,
        default="tailnet",
    )
    port = fields.Integer()
    runtime = fields.Selection(
        [("docker", "Docker"), ("systemd", "System service"), ("other", "Other")],
        default="docker",
    )
    runtime_ref = fields.Char(
        "Container / unit", help="Docker container or systemd unit name."
    )
    notes = fields.Text()

    # Main account of the service. Values live only in the database (never in
    # module data: this repo is public). Admin-only, like the whole model.
    login = fields.Char("User", groups="base.group_system", copy=False)
    password = fields.Char(groups="base.group_system", copy=False)

    state = fields.Selection(
        [("unknown", "Unknown"), ("up", "Up"), ("down", "Down")],
        string="Status",
        default="unknown",
        readonly=True,
    )
    last_check = fields.Datetime("Last checked", readonly=True)
    last_result = fields.Char("Last result", readonly=True)

    # Turn on/off, carried out on the host by ~/odoo20/server-services-checker/service_control.py
    power = fields.Selection(
        [
            ("running", "Running"),
            ("partial", "Partly running"),
            ("stopped", "Stopped"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        readonly=True,
        help="Whether the containers / system services are running, as seen by the host agent.",
    )
    control_request = fields.Selection(
        [("start", "Turning on..."), ("stop", "Turning off...")],
        string="Pending action",
        readonly=True,
        copy=False,
    )
    control_requested_at = fields.Datetime(readonly=True, copy=False)
    control_message = fields.Char("Last on/off result", readonly=True, copy=False)
    can_control = fields.Boolean(compute="_compute_can_control")

    @api.depends("runtime", "runtime_ref")
    def _compute_can_control(self):
        for service in self:
            service.can_control = bool(service._control_targets())

    def _control_targets(self):
        """Container / unit names this service can be turned on/off with (Odoo's own excluded)."""
        self.ensure_one()
        if self.runtime not in ("docker", "systemd") or not self.runtime_ref:
            return []
        names = [n.strip() for n in self.runtime_ref.split(",")]
        return [n for n in names if n and n not in PROTECTED_TARGETS]

    def _control_target(self):
        self.ensure_one()
        return {"id": self.id, "runtime": self.runtime, "targets": self._control_targets()}

    def action_turn_on(self):
        return self._request_control("start")

    def action_turn_off(self):
        return self._request_control("stop")

    def _request_control(self, action):
        services = self.filtered("can_control")
        if not services:
            raise UserError(self.env._("This service can't be turned on or off from Odoo."))
        services.write(
            {
                "control_request": action,
                "control_requested_at": fields.Datetime.now(),
                "control_message": False,
            }
        )
        # Commit so the host agent sees the request, then wait for it to be carried out.
        self.env.cr.commit()
        deadline = time.monotonic() + CONTROL_WAIT_SECONDS
        rows = None
        while time.monotonic() < deadline:
            time.sleep(1)
            # Fresh cursor: this request's own transaction keeps an older snapshot.
            with self.env.registry.cursor() as cr:
                cr.execute(
                    "SELECT name, control_request, control_message FROM server_service WHERE id = ANY(%s)",
                    [services.ids],
                )
                rows = cr.fetchall()
            if not any(request for _name, request, _message in rows):
                break
        else:
            rows = None
        if rows:
            failed = [f"{name}: {message}" for name, _r, message in rows if (message or "").startswith("Failed")]
            if not failed:
                return {"type": "ir.actions.client", "tag": "soft_reload"}
            message, kind = "\n".join(failed), "danger"
        else:
            message, kind = self.env._("Still working on it: the list updates once it's done."), "warning"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": kind, "sticky": kind == "danger",
                       "next": {"type": "ir.actions.client", "tag": "soft_reload"}},
        }

    def _apply_control_result(self, ok, message):
        self.write(
            {
                "control_request": False,
                "control_requested_at": False,
                "control_message": (message if ok else f"Failed: {message}")[:250],
            }
        )

    def _checker_target(self):
        self.ensure_one()
        return {"id": self.id, "name": self.name, "check_url": self.check_url or self.url}

    def _apply_check_result(self, ok, detail):
        self.write(
            {
                "state": "up" if ok else "down",
                "last_check": fields.Datetime.now(),
                "last_result": (detail or "")[:250],
            }
        )

    @api.model
    def _cron_mark_stale(self):
        """Statuses older than 10 minutes mean the checker stopped: don't show them as up."""
        limit = fields.Datetime.now() - STALE_AFTER
        self.search(
            [("state", "!=", "unknown"), "|", ("last_check", "=", False), ("last_check", "<", limit)]
        ).write({"state": "unknown", "last_result": "No recent check: is the checker running?"})
        self.search(
            [("control_request", "!=", False), ("control_requested_at", "<", fields.Datetime.now() - CONTROL_TIMEOUT)]
        )._apply_control_result(False, "the control agent didn't answer: is it running?")
