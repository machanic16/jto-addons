from datetime import timedelta

from odoo import api, fields, models

STALE_AFTER = timedelta(minutes=10)


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

    state = fields.Selection(
        [("unknown", "Unknown"), ("up", "Up"), ("down", "Down")],
        string="Status",
        default="unknown",
        readonly=True,
    )
    last_check = fields.Datetime("Last checked", readonly=True)
    last_result = fields.Char("Last result", readonly=True)

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
