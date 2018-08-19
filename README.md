# Open Tag Manager

## (0) What is this

Open Tag Manager is OpenSource Tag Manager and Action Tracker. You can reach raw data.

Copyright

see ./LICENSE

## (1) General Setup

### Upload basic contents

Upload basic contents (`collect.html` and `otm.js`) to any CDN.

- `collect.html`: A blank HTML contents to track user behavior.
- `otm.js`: Open Tag Manage base script file.

`script/upload.py` can upload to Amazon S3 easily. Make 2 buckets to S3, and execute following script.

```
yarn install
NODE_ENV=NODE_ENV npm run build
python client_apis/chalicelib/upload.py --collect-bucket=COLLECT_BUCKET --script-bucket=SCRIPT_BUCKET
```

## (2) Web API Setup

### (2-1)  Make DynamoDB table

Create client_apis/.chalice/config.json OTM_SESSION_DYNAMODB_TABLE DynamoDB Table to manage API session
Primary key: session_id (STRING)

### (2-2) Create Root User Password

```
python client_apis/set_root_password.py
```

and use this to ROOT_PASSWORD_HASH

### (2-3) Create Chalice Config

```
cp client_apis/.chalice/config.json.sample client_apis/.chalice/config.json
```

and modifiy this.

- `ROOT_PASSWORD_HASH`: set root password hash that is created by (2-2)
- `OTM_BUCKET`: otm script bucket
- `OTM_URL`: otm url
- `COLLECT_URL`: collect url
- `OTM_SESSION_DYNAMODB_TABLE`: otm session db table name (Dynamo)
- `OTM_STATS_BUCKET`: otm stats bucket name
- `OTM_STATS_PREFIX`: otm stats prefix
- `STATS_BATCH_JOB_QUEUE`: otm job queue name
- `STATS_BATCH_JOB_DEFINITION`: otm job definition
- `STATS_CONFIG_BUCKET`: otm config bucket
- `STATS_GCLOUD_KEY_NAME`: gcloud key name
- `STATS_BQ_DATASET`: BigQuery dataset name
- `STATS_BQ_TABLE_PREFIX`: BigQuery table prefix (e.g. `otm`)

### (2-4) Create Chalice Policy

```
cp client_apis/.chalice/policy-sample.json client_apis/.chalice/policy-ENV.json
```

and modifiy this.

### (2-5) Change app name and session table name

modifiy client_apis/app.py following value to your environment.

```
app = Chalice(app_name=“open_tag_manager”)
session_table = dynamodb.Table(‘otm_session’)
```

### (2-6) Deploy Chalice

```
AWS_PROFILE=AWS_PROFILE chalice deploy --no-autogen-policy
```

and get CHALICE_API_URL.

## (3) Web Client Setup

### (3-1) Build
NODE_ENV=NODE_ENV API_BASE_URL=CHALICE_API_URL ASSETS_PUBLIC_PATH=S3_WEB_URL BASE_PATH=URL_PATH npm run build

### (3-2) Deploy
AWS_PROFILE=AWS_PROFILE aws s3 sync ./dist/ s3://OTM_BUCKET/client/ --acl=public-read

### (3-3) Access

https://OTM_BUCKET/client/


## (Z) for Development

### Web API: Local Run

```
cd client_apis
pip install chalice
export AWS_PROFILE=xxxx
chalice local
```

### Client: Local Run

```
cd client
yarn install
yarn run start
```

Open `http://localhost:8080`

