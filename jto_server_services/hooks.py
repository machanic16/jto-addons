import secrets


def post_init_hook(env):
    """Create the secret token the host-side status checker uses."""
    params = env["ir.config_parameter"].sudo()
    if not params.get_str("jto_server_services.checker_token"):
        params.set_str("jto_server_services.checker_token", secrets.token_urlsafe(32))
