from fastapi.responses import RedirectResponse

def flash(response: RedirectResponse, message: str):
    response.set_cookie("flash", message, max_age=3)
    return response