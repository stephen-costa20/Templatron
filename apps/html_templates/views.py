import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.dateparse import parse_date

from .models import Component, ComponentFile

@ensure_csrf_cookie
def home(request):
    """
    Renders the page; JS will fetch() the components to populate the grid.
    """
    return render(request, 'html_templates/HOME.html')

@require_http_methods(['GET', 'POST'])
def html_templates_list_create(request):
    if request.method == 'GET':
        data = [c.to_dict() for c in Component.objects.all()]
        return JsonResponse({'results': data})

    # POST: create new component
    # Accepts either JSON (paste mode) or multipart (upload mode)
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        # multipart: expect fields plus optional code_file and extra files[]
        name = request.POST.get('name', '').strip() or 'Untitled'
        section = request.POST.get('section', '').strip()
        tags = request.POST.get('tags', '').strip()
        description = request.POST.get('description', '').strip()
        notes = request.POST.get('notes', '').strip()
        instructions = request.POST.get('instructions', '').strip()
        status = request.POST.get('status', 'not_started').strip()

        code_text = request.POST.get('code_text', '').strip()
        code_file = request.FILES.get('code_file')
        if not code_text and code_file:
            code_text = code_file.read().decode('utf-8', errors='ignore')

        if not code_text:
            return HttpResponseBadRequest('Code is required.')

        comp = Component.objects.create(
            name=name, section=section, tags=tags, code=code_text,
            description=description, notes=notes, instructions=instructions, status=status
        )

        # optional multiple file attachments
        for f in request.FILES.getlist('files'):
            ComponentFile.objects.create(component=comp, file=f)

        return JsonResponse(comp.to_dict(), status=201)

    # JSON
    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        return HttpResponseBadRequest('Invalid JSON')

    name = (payload.get('name') or 'Untitled').strip()
    section = (payload.get('section') or '').strip()
    tags_list = payload.get('tags') or []
    tags = ','.join(t.strip() for t in tags_list if t.strip())
    code = (payload.get('code') or '').strip()
    description = (payload.get('description') or '')
    notes = (payload.get('notes') or '')
    instructions = (payload.get('instructions') or '')
    status = (payload.get('status') or 'not_started').strip()

    if not code:
        return HttpResponseBadRequest('Code is required.')

    comp = Component.objects.create(
        name=name, section=section, tags=tags, code=code,
        description=description, notes=notes, instructions=instructions, status=status
    )
    return JsonResponse(comp.to_dict(), status=201)

@require_http_methods(['GET', 'PATCH', 'DELETE'])
def html_templates_detail(request, pk):
    comp = get_object_or_404(Component, pk=pk)

    if request.method == 'GET':
        data = comp.to_dict()
        data['files'] = [f.to_dict() for f in comp.files.all()]
        return JsonResponse(data)

    if request.method == 'PATCH':
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            return HttpResponseBadRequest('Invalid JSON')

        # update editable fields
        for field in ['name', 'section', 'description', 'notes', 'instructions', 'code', 'status']:
            if field in payload:
                setattr(comp, field, payload[field])

        if 'tags' in payload:
            tags_list = payload.get('tags') or []
            comp.tags = ','.join(t.strip() for t in tags_list if t.strip())

        # allow date override (optional)
        if 'dateISO' in payload:
            d = parse_date(payload['dateISO'])
            if d:
                comp.date_added = d

        comp.save()
        return JsonResponse(comp.to_dict(), status=200)

    # DELETE
    comp.delete()
    return JsonResponse({'ok': True})

@require_http_methods(['POST'])
def html_templates_upload_files(request, pk):
    comp = get_object_or_404(Component, pk=pk)
    created = []
    for f in request.FILES.getlist('files'):
        obj = ComponentFile.objects.create(component=comp, file=f)
        created.append(obj.to_dict())
    return JsonResponse({'files': created}, status=201)