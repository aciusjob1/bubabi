from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
import mimetypes
from apps.identity.models import ClanDocument

@login_required
def registration_pending_view(request):
    """Show pending approval page after registration."""
    from apps.identity.models import Clan
    clan = Clan.objects.first()
    return render(request, 'registration/pending.html', {'clan': clan})

@xframe_options_exempt
@login_required
def view_document(request, pk):
    """Preview a document inline instead of downloading."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    mime_type, _ = mimetypes.guess_type(doc.file.name)
    
    file_content = None
    if doc.file.name.lower().endswith(('.txt', '.log', '.md', '.csv')):
        try:
            doc.file.open('rb')
            file_content = doc.file.read().decode('utf-8', errors='replace')
            doc.file.close()
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
    """Secure file download — enforces permission check."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    try:
        response = FileResponse(doc.file.open("rb"))
        filename = doc.file.name.split("/")[-1]
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception:
        raise Http404("File not available")

@login_required
def stream_document(request, pk):
    """Secure file streaming for inline preview — enforces permission check."""
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    mime_type, _ = mimetypes.guess_type(doc.file.name)
    try:
        response = FileResponse(doc.file.open("rb"), content_type=mime_type or "application/octet-stream")
        filename = doc.file.name.split("/")[-1]
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response
    except Exception:
        raise Http404("File cannot be streamed")
