from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, Http404, StreamingHttpResponse
from django.views.decorators.clickjacking import xframe_options_exempt
import mimetypes
import requests
from apps.identity.models import ClanDocument


@xframe_options_exempt
@login_required
def view_document(request, pk):
    """Preview a document inline."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    mime_type, _ = mimetypes.guess_type(doc.file.name)

    file_content = None
    if doc.file.name.lower().endswith(('.txt', '.log', '.md', '.csv')):
        try:
            doc.file.open('rb')
            file_content = doc.file.read().decode('utf-8', errors='replace')
            doc.file.close()
        except Exception:
            try:
                resp = requests.get(doc.file.url, timeout=10)
                file_content = resp.text
            except Exception:
                file_content = None

    # For PDF and images, use the stream URL directly
    stream_url = None
    if mime_type and (mime_type.startswith('image/') or mime_type == 'application/pdf'):
        try:
            import cloudinary.utils, time
            stream_url, _ = cloudinary.utils.cloudinary_url(
                doc.file.name, resource_type="raw",
                sign_url=True, expires_at=int(time.time()) + 600,
            )
        except Exception:
            stream_url = doc.file.url

    context = {
        'document': doc,
        'mime_type': mime_type or 'application/octet-stream',
        'is_image': mime_type and mime_type.startswith('image/'),
        'is_pdf': mime_type == 'application/pdf',
        'is_text': doc.file.name.lower().endswith(('.txt', '.log', '.md', '.csv')) or (mime_type and mime_type.startswith('text/')),
        'file_content': file_content,
        'stream_url': stream_url,
    }
    return render(request, 'view_document.html', context)


@login_required
def download_document(request, pk):
    """Secure download via Django with signed Cloudinary URL."""
    doc = get_object_or_404(
        ClanDocument,
        pk=pk,
        clan=request.user.clan,
        is_active=True
    )

    import cloudinary.utils
    import time
    import requests
    from django.http import HttpResponse

    file_url, _ = cloudinary.utils.cloudinary_url(
        doc.file.name,
        resource_type="raw",
        sign_url=True,
        expires_at=int(time.time()) + 60,
    )

    r = requests.get(file_url, stream=True)

    if r.status_code != 200:
        return HttpResponse("File not accessible", status=403)

    response = HttpResponse(
        r.content,
        content_type='application/octet-stream'
    )
    response['Content-Disposition'] = f'attachment; filename="{doc.name}"'

    return response

@login_required
def stream_document(request, pk):
    """Generate signed Cloudinary URL for inline viewing."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    try:
        import cloudinary
        import cloudinary.utils
        public_id = doc.file.name
        signed_url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            resource_type="raw",
            sign_url=True,
            expires_at=int(__import__("time").time()) + 600,
        )
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(signed_url)
    except Exception:
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(doc.file.url)
