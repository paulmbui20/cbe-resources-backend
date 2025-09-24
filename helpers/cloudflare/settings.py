import logging
import os

logger = logging.getLogger(__name__)


CLOUDFLARE_R2_CONFIG_OPTIONS = {}

bucket_name = os.getenv("CLOUDFLARE_R2_BUCKET")
endpoint_url = os.getenv("CLOUDFLARE_R2_BUCKET_ENDPOINT")
access_key = os.getenv("CLOUDFLARE_R2_ACCESS_KEY")
secret_key = os.getenv("CLOUDFLARE_R2_SECRET_KEY")

if all([bucket_name, endpoint_url, access_key, secret_key]):
    CLOUDFLARE_R2_CONFIG_OPTIONS = {
        "bucket_name": os.getenv("CLOUDFLARE_R2_BUCKET"),
        "default_acl": "public-read",  # "private"
        "signature_version": "s3v4",
        "endpoint_url": os.getenv("CLOUDFLARE_R2_BUCKET_ENDPOINT"),
        "access_key": os.getenv("CLOUDFLARE_R2_ACCESS_KEY"),
        "secret_key": os.getenv("CLOUDFLARE_R2_SECRET_KEY"),
    }