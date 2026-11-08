
from functools import lru_cache

from flask import current_app
from supabase import create_client


@lru_cache(maxsize=1)
def _get_supabase_client(url, secret_key):
    if not url or not secret_key:
        raise RuntimeError("Supabase storage configuration is missing.")

    return create_client(url, secret_key)


def _get_storage():
    url = current_app.config.get("SUPABASE_URL")
    secret_key = current_app.config.get("SUPABASE_SECRET_KEY")
    bucket = current_app.config.get("SUPABASE_BUCKET")

    if not bucket:
        raise RuntimeError("Supabase bucket name is missing.")

    client = _get_supabase_client(url, secret_key)
    return client.storage.from_(bucket)


def upload_file(storage_key, file_data, content_type):
    storage = _get_storage()

    return storage.upload(
        path=storage_key,
        file=file_data,
        file_options={
            "content-type": content_type or "application/octet-stream",
            "upsert": "false"
        }
    )


def download_file(storage_key):
    storage = _get_storage()
    return storage.download(storage_key)


def delete_file(storage_key):
    storage = _get_storage()
    return storage.remove([storage_key])
