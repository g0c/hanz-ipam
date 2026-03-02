# v1.0.1
import urllib.parse
from fastapi.templating import Jinja2Templates

# Kreiramo centralni objekt za predloške
templates = Jinja2Templates(directory="app/templates")

# Registriramo filter za dekodiranje hrvatskih znakova (unquote)
# Ovo sada vrijedi za cijelu aplikaciju!
templates.env.filters["unquote"] = urllib.parse.unquote