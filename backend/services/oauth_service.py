import os
import urllib.parse
import httpx
from typing import Dict, Any, Optional

# --- Helper to load and validate environment variables dynamically ---
def get_env_var(key: str, default: str = "") -> str:
    val = os.environ.get(key, default)
    return val.strip() if val else default

# Dynamic Configuration Loaders
def get_google_config():
    client_id = get_env_var("GOOGLE_CLIENT_ID")
    client_secret = get_env_var("GOOGLE_CLIENT_SECRET")
    redirect_uri = get_env_var("GOOGLE_REDIRECT_URI", "https://dynamic-scheduler-ten.vercel.app/api/auth/google/callback")
    return client_id, client_secret, redirect_uri

def get_github_config():
    client_id = get_env_var("GITHUB_CLIENT_ID")
    client_secret = get_env_var("GITHUB_CLIENT_SECRET")
    redirect_uri = get_env_var("GITHUB_REDIRECT_URI", "https://dynamic-scheduler-ten.vercel.app/api/auth/github/callback")
    return client_id, client_secret, redirect_uri

def get_microsoft_config():
    client_id = get_env_var("MICROSOFT_CLIENT_ID")
    client_secret = get_env_var("MICROSOFT_CLIENT_SECRET")
    redirect_uri = get_env_var("MICROSOFT_REDIRECT_URI", "https://dynamic-scheduler-ten.vercel.app/api/auth/microsoft/callback")
    return client_id, client_secret, redirect_uri

# --- Google OAuth Flow ---
def get_google_auth_url(state: str = "state_google") -> str:
    client_id, _, redirect_uri = get_google_config()
    
    has_client_id = bool(client_id)
    print(f"[OAuth Diagnostic] GOOGLE_CLIENT_ID exists: {has_client_id} | Redirect URI: {redirect_uri}")

    if not client_id:
        raise ValueError("GOOGLE_CLIENT_ID environment variable is missing or empty. Please configure GOOGLE_CLIENT_ID in your environment settings.")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

async def exchange_google_code(code: str) -> Dict[str, Any]:
    client_id, client_secret, redirect_uri = get_google_config()
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials missing on backend server.")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, data=payload)
        res.raise_for_status()
        return res.json()

async def get_google_user_info(access_token: str) -> Dict[str, Any]:
    userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(userinfo_url, headers=headers)
        res.raise_for_status()
        data = res.json()
        return {
            "provider_user_id": data.get("sub"),
            "email": data.get("email"),
            "name": data.get("name") or data.get("email").split("@")[0],
            "picture": data.get("picture")
        }

# --- GitHub OAuth Flow ---
def get_github_auth_url(state: str = "state_github") -> str:
    client_id, _, redirect_uri = get_github_config()
    
    has_client_id = bool(client_id)
    print(f"[OAuth Diagnostic] GITHUB_CLIENT_ID exists: {has_client_id} | Redirect URI: {redirect_uri}")

    if not client_id:
        raise ValueError("GITHUB_CLIENT_ID environment variable is missing or empty. Please configure GITHUB_CLIENT_ID in your environment settings.")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
        "state": state
    }
    return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

async def exchange_github_code(code: str) -> Dict[str, Any]:
    client_id, client_secret, redirect_uri = get_github_config()
    if not client_id or not client_secret:
        raise ValueError("GitHub OAuth credentials missing on backend server.")

    token_url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, json=payload, headers=headers)
        res.raise_for_status()
        return res.json()

async def get_github_user_info(access_token: str) -> Dict[str, Any]:
    user_url = "https://api.github.com/user"
    emails_url = "https://api.github.com/user/emails"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "FastAPI-OAuth-App"
    }
    async with httpx.AsyncClient() as client:
        user_res = await client.get(user_url, headers=headers)
        user_res.raise_for_status()
        user_data = user_res.json()

        email = user_data.get("email")
        if not email:
            emails_res = await client.get(emails_url, headers=headers)
            if emails_res.status_code == 200:
                emails_data = emails_res.json()
                primary_email = next((e["email"] for e in emails_data if e.get("primary")), None)
                email = primary_email or (emails_data[0]["email"] if emails_data else None)

        return {
            "provider_user_id": str(user_data.get("id")),
            "email": email or f"github_{user_data.get('id')}@user.github.com",
            "name": user_data.get("name") or user_data.get("login"),
            "picture": user_data.get("avatar_url")
        }

# --- Microsoft OAuth Flow ---
def get_microsoft_auth_url(state: str = "state_microsoft") -> str:
    client_id, _, redirect_uri = get_microsoft_config()
    
    has_client_id = bool(client_id)
    print(f"[OAuth Diagnostic] MICROSOFT_CLIENT_ID exists: {has_client_id} | Redirect URI: {redirect_uri}")

    if not client_id:
        raise ValueError("MICROSOFT_CLIENT_ID environment variable is missing or empty. Please configure MICROSOFT_CLIENT_ID in your environment settings.")

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "openid email profile User.Read",
        "state": state
    }
    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

async def exchange_microsoft_code(code: str) -> Dict[str, Any]:
    client_id, client_secret, redirect_uri = get_microsoft_config()
    if not client_id or not client_secret:
        raise ValueError("Microsoft OAuth credentials missing on backend server.")

    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
        "scope": "openid email profile User.Read"
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(token_url, data=payload)
        res.raise_for_status()
        return res.json()

async def get_microsoft_user_info(access_token: str) -> Dict[str, Any]:
    graph_url = "https://graph.microsoft.com/v1.0/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(graph_url, headers=headers)
        res.raise_for_status()
        data = res.json()

        email = data.get("mail") or data.get("userPrincipalName")
        return {
            "provider_user_id": data.get("id"),
            "email": email,
            "name": data.get("displayName") or email.split("@")[0],
            "picture": None
        }
