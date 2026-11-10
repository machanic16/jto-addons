{
    "name": "Server Services",
    "summary": "List of every service running on the server, with its URL, live status and on/off buttons",
    "version": "20.0.1.2.0",
    "category": "Administration",
    "author": "machanic16",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.access.csv",
        "views/server_service_views.xml",
        "data/server_service_data.xml",
        "data/ir_cron.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
}
