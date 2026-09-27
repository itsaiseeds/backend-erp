import os

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, HttpResponseNotFound
from django.utils._os import safe_join


def flutter_catch_all(request, path=""):
    """Serve the Flutter web app for /sales-admin/* routes."""
    build_dir = os.path.join(settings.BASE_DIR, "admin_saiseeds", "build", "web")

    # Serve the requested file directly (JS, CSS, images, etc.). ``safe_join``
    # refuses any path that resolves outside build_dir -- ``..`` segments, an
    # absolute path (``//etc/passwd`` would make os.path.join drop build_dir)
    # or their percent-encoded forms, which arrive here already decoded.
    if path:
        try:
            file_path = safe_join(build_dir, path)
        except SuspiciousFileOperation:
            return HttpResponseNotFound()
        if os.path.isfile(file_path):
            # FileResponse guesses the content type from the file name.
            return FileResponse(open(file_path, "rb"))

    # For all other routes, serve index.html (Flutter handles client-side routing)
    index_path = os.path.join(build_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(open(index_path, "rb"), content_type="text/html")

    return HttpResponseNotFound(
        "Flutter build not found. Run: cd admin_saiseeds && flutter build web --release"
    )
