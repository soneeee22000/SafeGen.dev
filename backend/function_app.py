"""SafeGen — Azure Functions application entry point.

Registers all function blueprints. Each blueprint is defined in
the functions/ directory and handles a specific API route.
"""

import azure.functions as func

from functions.audit import bp as audit_bp
from functions.ingest_rules import bp as ingest_rules_bp
from functions.list_rules import bp as list_rules_bp
from functions.metrics import bp as metrics_bp
from functions.validate import bp as validate_bp

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Register function blueprints
app.register_functions(validate_bp)
app.register_functions(ingest_rules_bp)
app.register_functions(list_rules_bp)
app.register_functions(audit_bp)
app.register_functions(metrics_bp)
