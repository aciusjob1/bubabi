from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, Http404
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
                # Fallback: try reading via URL (for Cloudinary)
                resp = requests.get(doc.file.url, timeout=10)
                file_content = resp.text
            except Exception:
                file_content = None

    context = {
        'document': doc,
        'mime_type': mime_type or 'application/octet-stream',
        'is_image': mime_type and mime_type.startswith('image/'),
        'is_pdf': mime_type == 'application/pdf',
        'is_text': doc.file.name.lower().endswith(('.txt', '.log', '.md', '.csv')) or (mime_type and mime_type.startswith('text/')),
        'file_content': file_content,
    }
    return render(request, 'view_document.html', context)


@login_required
def download_document(request, pk):
    """Secure file download — works with both local and Cloudinary storage."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    filename = doc.file.name.split("/")[-1]
    
    try:
        # Try local file first
        doc.file.open("rb")
        response = FileResponse(doc.file, content_type='application/octet-stream')
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        # Fallback: proxy download from Cloudinary URL
        try:
            resp = requests.get(doc.file.url, stream=True, timeout=30)
            response = HttpResponse(resp.content, content_type='application/octet-stream')
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            response["Content-Length"] = resp.headers.get('Content-Length', '')
            return response
        except Exception:
            raise Http404("File not available")


@login_required
def stream_document(request, pk):
    """Secure file streaming — works with both local and Cloudinary storage."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    mime_type, _ = mimetypes.guess_type(doc.file.name)
    filename = doc.file.name.split("/")[-1]
    
    try:
        # Try local file first
        doc.file.open("rb")
        response = FileResponse(doc.file, content_type=mime_type or "application/octet-stream")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
    except Exception:
        # Fallback: proxy from Cloudinary URL
        try:
            resp = requests.get(doc.file.url, stream=True, timeout=30)
            response = HttpResponse(resp.content, content_type=mime_type or "application/octet-stream")
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            response["Content-Length"] = resp.headers.get('Content-Length', '')
            return response
        except Exception:
            # Last resort: redirect to Cloudinary URL directly
            return redirect(doc.file.url)
