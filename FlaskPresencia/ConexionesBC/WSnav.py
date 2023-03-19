#pip install adal
#pip install requests
import adal as ad
import requests as req
import json

def get_access_token(tenant, IdCLIENT, SecretClient):
    authority_url = 'https://login.microsoftonline.com/'+tenant
    context = ad.AuthenticationContext(authority_url)
    token = context.acquire_token_with_client_credentials(
    resource='https://api.businesscentral.dynamics.com/',
    client_id=IdCLIENT,
    client_secret=SecretClient,
    )
    return token["accessToken"]

def getConnectionBC(tenant,IdCLIENT,SecretClient, funcion, empresa, datos):
    url = "https://api.businesscentral.dynamics.com/v2.0/"+tenant+"/sandbox3/ODataV4/Marcajes_"+funcion+"?company="+empresa

    headers = {
        'Authorization': 'Bearer ' + get_access_token(tenant, IdCLIENT, SecretClient),
        'Content-Type': 'application/json'
    }
    response = req.request("POST", url, headers=headers, data=datos)
    return response.text
