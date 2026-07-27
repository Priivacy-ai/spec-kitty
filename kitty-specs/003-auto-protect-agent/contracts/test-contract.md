# API Contract: User Authentication Service

## Overview
This document defines the contract for the User Authentication Service API.

## Endpoints

### POST /auth/login
Authenticates a user and returns access tokens.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "mfa_code": "string (optional)"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "user": {
    "id": "string",
    "username": "string",
    "email": "string"
  }
}
```

## Status Codes

| Code | Description |
|------|-------------|
| 200 | Successful authentication |
| 401 | Invalid credentials |
| 403 | Account locked or MFA required |
| 429 | Too many login attempts |

## Security Requirements

1. All endpoints must use **HTTPS**
2. Passwords must be hashed using **bcrypt**
3. Tokens must be **JWT** with RS256 signing
4. MFA using **TOTP** when enabled

> **Note:** This is a test contract for demonstration purposes.