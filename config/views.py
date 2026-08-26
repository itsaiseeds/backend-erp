import os
from django.http import FileResponse, HttpResponseNotFound
from django.conf import settings


def flutter_catch_all(request, path=""):
    """Serve the Flutter web app for /sales-admin/* routes."""
    build_dir = os.path.join(settings.BASE_DIR, "web", "build", "web")

    # Try to serve the requested file directly (JS, CSS, images, etc.)
    if path:
        file_path = os.path.join(build_dir, path)
        if os.path.isfile(file_path):
            # Determine content type
            content_type = "application/octet-stream"
            if file_path.endswith(".js"):
                content_type = "application/javascript"
            elif file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".html"):
                content_type = "text/html"
            elif file_path.endswith(".json"):
                content_type = "application/json"
            elif file_path.endswith(".png"):
                content_type = "image/png"
            elif file_path.endswith(".svg"):
                content_type = "image/svg+xml"
            elif file_path.endswith(".ico"):
                content_type = "image/x-icon"
            elif file_path.endswith(".woff"):
                content_type = "font/woff"
            elif file_path.endswith(".woff2"):
                content_type = "font/woff2"
            elif file_path.endswith(".ttf"):
                content_type = "font/ttf"

            return FileResponse(open(file_path, "rb"), content_type=content_type)

    # For all other routes, serve index.html (Flutter handles client-side routing)
    index_path = os.path.join(build_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(open(index_path, "rb"), content_type="text/html")

    return HttpResponseNotFound(
        "Flutter build not found. Run: cd web && flutter build web --release"
    )
