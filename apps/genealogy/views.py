from apps.identity.views import elder_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from apps.genealogy.models import Family, PersonFamilyMembership, Relationship
from apps.genealogy.constants import FamilyRole, RelationType
from apps.genealogy.services.genealogy_service import GenealogyService
from apps.identity.models import Person, Member


@login_required
def family_list_view(request, person_pk=None):
    """List all families and optionally show family tree for a person."""
    from apps.genealogy.services.genealogy_service import GenealogyService
    import json
    
    clan = request.user.clan
    gsvc = GenealogyService()
    
    families = Family.objects.filter(clan=clan).select_related('founding_person')
    for family in families:
        family.member_count = family.members.count()
        family.founder = gsvc.get_family_founder(family)
    
    # Handle person selection for tree view
    person_pk = person_pk or request.GET.get('person')
    selected_person = None
    tree_data = None
    ancestors_tree = None
    descendants_tree = None
    person_details = None
    selected_member = None
    
    if person_pk:
        try:
            from apps.identity.models import Person
            selected_person = Person.objects.get(pk=person_pk)
            selected_member = selected_person.memberships.first()
            
            ancestors = gsvc.get_ancestor_tree(selected_person, depth=4)
            ancestors_tree = json.dumps(ancestors) if ancestors else None
            
            descendants = gsvc.get_family_tree(selected_person, depth=4)
            descendants_tree = json.dumps(descendants) if descendants else None
            tree_data = descendants_tree
            person_details = gsvc.get_person_details(selected_person)
        except (Person.DoesNotExist, ValueError):
            pass
    
    all_persons = Person.objects.filter(family_memberships__family__clan=clan).distinct()
    
    return render(request, 'family_tree.html', {
        'families': families,
        'all_persons': all_persons,
        'tree_data': tree_data,
        'ancestors_tree': ancestors_tree,
        'descendants_tree': descendants_tree,
        'selected_person': selected_person,
        'selected_member': selected_member,
        'person_details': person_details,
    })


@login_required
def family_detail_view(request, family_id):
    """View a specific family with its members."""
    family = get_object_or_404(Family, id=family_id, clan=request.user.clan)
    memberships = PersonFamilyMembership.objects.filter(family=family).select_related('person')
    return render(request, 'family_detail.html', {'family': family, 'memberships': memberships})


@login_required
def add_family_view(request):
    """Create a new family house."""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        founding_person_id = request.POST.get('founding_person')
        
        if name:
            family = Family.objects.create(
                clan=request.user.clan,
                name=name,
                description=description,
                founding_person_id=founding_person_id or None
            )
            if family.founding_person:
                PersonFamilyMembership.objects.create(
                    person=family.founding_person,
                    family=family,
                    role_in_family=FamilyRole.FOUNDER
                )
            messages.success(request, f"Family '{family.name}' created!")
            return redirect('family-tree')
    
    persons = Person.objects.all().order_by('full_name')
    return render(request, 'forms/add_family.html', {'persons': persons})


@login_required
def add_family_member_view(request, family_id):
    """Add a person to a family."""
    family = get_object_or_404(Family, id=family_id, clan=request.user.clan)
    current_memberships = PersonFamilyMembership.objects.filter(family=family).select_related('person')
    current_person_ids = current_memberships.values_list('person_id', flat=True)
    available_persons = Person.objects.exclude(id__in=current_person_ids).order_by('full_name')
    
    if request.method == 'POST':
        person_id = request.POST.get('person_id')
        role = request.POST.get('role', FamilyRole.MEMBER)
        
        if person_id:
            try:
                person = Person.objects.get(id=person_id)
                PersonFamilyMembership.objects.create(person=person, family=family, role_in_family=role)
                messages.success(request, f"{person.full_name} added to '{family.name}'.")
            except Person.DoesNotExist:
                messages.error(request, "Invalid person.")
        return redirect('family-tree')
    
    return render(request, 'forms/add_family_member.html', {
        'family': family,
        'current_memberships': current_memberships,
        'available_persons': available_persons,
        'family_roles': FamilyRole.choices,
    })


@login_required
def remove_family_member_view(request, membership_id):
    """Remove a person from a family."""
    membership = get_object_or_404(PersonFamilyMembership, id=membership_id, family__clan=request.user.clan)
    if request.method == 'POST':
        membership.delete()
        messages.success(request, "Member removed from family.")
    return redirect('family-tree')


@login_required
@elder_required
def add_relationship_view(request):
    """Create a relationship between two persons."""
    persons = Person.objects.all().order_by('full_name')
    
    if request.method == 'POST':
        from_person_id = request.POST.get('from_person')
        to_person_id = request.POST.get('to_person')
        relation_type = request.POST.get('relation_type')
        
        if from_person_id and to_person_id and relation_type:
            try:
                from_person = Person.objects.get(id=from_person_id)
                to_person = Person.objects.get(id=to_person_id)
                Relationship.objects.create(
                    from_person=from_person,
                    to_person=to_person,
                    relation_type=relation_type,
                    recorded_by=request.user
                )
                messages.success(request, f"Relationship created: {from_person.full_name} -> {relation_type} -> {to_person.full_name}")
            except Person.DoesNotExist:
                messages.error(request, "Invalid person selected.")
        return redirect('family-tree')
    
    return render(request, 'forms/add_relationship.html', {
        'persons': persons,
        'relation_types': RelationType.choices,
    })


@login_required
@elder_required
def delete_relationship_view(request, relationship_id):
    """Delete a relationship."""
    relationship = get_object_or_404(Relationship, id=relationship_id)
    if request.method == 'POST':
        relationship.delete()
        messages.success(request, "Relationship deleted.")
    return redirect('family-tree')


@login_required
def person_genealogy_view(request, person_id):
    """View a person's genealogy."""
    person = get_object_or_404(Person, id=person_id)
    gsvc = GenealogyService()
    tree_data = gsvc.get_family_tree(person, depth=3)
    relationships = Relationship.objects.filter(
        Q(from_person=person) | Q(to_person=person)
    ).select_related('from_person', 'to_person')
    memberships = PersonFamilyMembership.objects.filter(person=person).select_related('family')
    
    return render(request, 'person_genealogy.html', {
        'person': person,
        'tree_data': tree_data,
        'relationships': relationships,
        'memberships': memberships,
    })
