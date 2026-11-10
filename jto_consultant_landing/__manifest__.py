{
    "name": "JTO Consultant Landing Page",
    "summary": "Bilingual (English/Spanish) landing page for business consultant Joel Tovar",
    "version": "20.0.1.0.0",
    "category": "Website",
    "author": "machanic16",
    "license": "LGPL-3",
    "depends": ["website", "website_crm"],
    "data": [
        "views/landing_page.xml",
        "data/website_page.xml",
        "views/contactus_crm.xml",
        "views/header_phone.xml",
        "views/footer.xml",
        "views/header_sign_in.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "jto_consultant_landing/static/src/scss/landing.scss",
            "jto_consultant_landing/static/src/js/video_modal.js",
        ],
    },
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
    "application": False,
}
