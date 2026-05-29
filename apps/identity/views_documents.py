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
        stream_url = doc.file.url  # Use direct URL for Cloudinary PDFs/images

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
    """Secure file download — proxies from Cloudinary/local storage."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    filename = doc.file.name.split("/")[-1]
    
    try:
        # Stream the file from the URL (works for both Cloudinary and local)
        resp = requests.get(doc.file.url, stream=True, timeout=60)
        resp.raise_for_status()
        
        response = StreamingHttpResponse(
            resp.iter_content(chunk_size=8192),
            content_type=resp.headers.get('Content-Type', 'application/octet-stream')
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = resp.headers.get('Content-Length', '')
        return response
    except requests.exceptions.ConnectionError:
        # Local file fallback
        try:
            doc.file.open("rb")
            response = FileResponse(doc.file, content_type='application/octet-stream')
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response
        except Exception:
            raise Http404("File not available")
    except Exception:
        raise Http404("File not available")


@login_required
def stream_document(request, pk):
    """Secure file streaming for inline preview."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    mime_type, _ = mimetypes.guess_type(doc.file.name)
    
    # Redirect directly to the file URL for Cloudinary (faster, avoids double download)
    return redirect(doc.file.url)
