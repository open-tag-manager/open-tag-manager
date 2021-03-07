# OTM Client

## Build

TBD

## Local development

Fistly, make development infrastructure by using `deploy.py`. Read `../README.md`.

And start api locally:

```
cd ../client_apis
DEBUG=1 AWS_PROFILE="YOUR_AWS_PROFILE" chalice local
```

And run following command for client development:

```
AWS_DEFAULT_REGION="YOUR_REGION" \
COGNITO_IDENTITY_POOL_ID="YOUR_REGION:YOUR_ID" \
COGNITO_USER_POOL_ID="YOUR_REGION_YOUR_ID" \
COGNITO_USER_POOL_WEB_CLIENT_ID="YOUR_CLIENT_ID" \
yarn run dev
```
