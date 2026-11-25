from urllib.parse import quote

from django.conf import settings
from storages.backends.s3 import S3Storage
from storages.utils import clean_name


class SupabaseStorage(S3Storage):
    """Supabase Storage through the S3 protocol.

    Files are uploaded with the S3 API, but URLs point at Supabase's public CDN
    link, so the bucket must be set to "Public".
    """

    def url(self, name, parameters=None, expire=None, http_method=None):
        name = self._normalize_name(clean_name(name))
        return f"{settings.SUPABASE_URL}/storage/v1/object/public/{self.bucket_name}/{quote(name)}"
