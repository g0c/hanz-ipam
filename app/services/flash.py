# v1.0.3
# Servis za prikazivanje kratkotrajnih (flash) obavijesti korisniku.

import urllib.parse
from fastapi.responses import RedirectResponse

def flash(response: RedirectResponse, message: str):
    """
    Dodaje kratkotrajni kolačić u odgovor koji Jinja2 predložak čita i prikazuje kao obavijest.
    """
    # URL kodiramo poruku kako bi se izbjegli problemi s hrvatskim znakovima (č, ć, ž, š, đ)
    encoded_message = urllib.parse.quote(message)
    
    # max_age=5 sekundi je dovoljno za jedan redirect. 
    # path="/" osigurava da je poruka vidljiva na bilo kojoj stranici nakon preusmjeravanja.
    response.set_cookie(key="flash", value=encoded_message, max_age=5, path="/")
    
    return response