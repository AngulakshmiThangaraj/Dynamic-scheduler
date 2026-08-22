import os
import urllib.parse
import httpx
from typing import Dict, Any, Optional

# Google OAuth 2.0 Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

# GitHub OAuth 2.0 Configuration
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GITHUB_REDIRECT_URI = os.environ.get("GITHUB_REDIRECT_URI", "http://localhost:8000/api/auth/github/callback")

# Microsoft OAuth 2.0 Configuration
MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_REDIRECT_URI = os.environ.get("MICROSOFT_REDIRECT_URI", "http://localhost:8000/api/auth/microsoft/callback")

# --- Google OAuth Flow ---
def get_google_auth_url(state: str = "state_google") -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "consent"
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

async def exchange_google_code(code: str) -> Dict[str, Any]:
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": GOOGLE_REDIRECT_URI
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
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": GITHUB_REDIRECT_URI,
        "scope": "read:user user:email",
        "state": state
    }
    return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

async def exchange_github_code(code: str) -> Dict[str, Any]:
    token_url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": GITHUB_REDIRECT_URI
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
    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": MICROSOFT_REDIRECT_URI,
        "response_mode": "query",
        "scope": "openid email profile User.Read",
        "state": state
    }
    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"

async def exchange_microsoft_code(code: str) -> Dict[str, Any]:
    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    payload = {
        "client_id": MICROSOFT_CLIENT_ID,
        "client_secret": MICROSOFT_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": MICROSOFT_REDIRECT_URI,
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
