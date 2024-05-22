import requests
import json
import base64


def hprim2response(hprim):
    # encoded_hprim = base64.b64encode(hprim.encode("utf-8")).decode("utf-8")

    url = "https://api.deepia.fr/rule-engine/v1.0/rule-engine"
    payload = json.dumps({"hprim": hprim.decode("utf-8")})
    headers = {
        "Content-Type": "application/json",
        "x-api-key": "CD0jtGDbG6o9HjHpBGrK7MWfocH4DRz1eQCAbseg",
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    print(response.json())
    return response.json()
    # return data["ordonnance"], urgences
