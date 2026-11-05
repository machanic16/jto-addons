LANDING_URL = "/joel-tovar"
SPANISH = "es_ES"


def post_init_hook(env):
    """Activate Spanish, offer it on the website and make the landing the homepage."""
    lang = env["res.lang"]._activate_lang(SPANISH)
    # Load this module's Spanish terms now that the language is active.
    env["ir.module.module"].search(
        [("name", "=", "jto_consultant_landing")]
    )._update_translations([SPANISH], overwrite=True)
    for website in env["website"].search([]):
        vals = {"homepage_url": LANDING_URL}
        if lang and lang not in website.language_ids:
            vals["language_ids"] = [(4, lang.id)]
        website.write(vals)


def uninstall_hook(env):
    """Give the site its default homepage back. Spanish stays active."""
    env["website"].search([("homepage_url", "=", LANDING_URL)]).write(
        {"homepage_url": False}
    )
