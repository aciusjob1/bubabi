from django.db.models import Q
from collections import deque
from apps.identity.models import Person
from apps.genealogy.models import Family, Relationship, PersonFamilyMembership


class GenealogyService:
    """Service for genealogy and family tree operations."""

    # ══════════════════════════════════════════════
    # TREE BUILDING (for frontend visualisation)
    # ══════════════════════════════════════════════

    def get_family_tree(self, person, depth=4):
        """
        Return a recursive DESCENDANTS tree (children, grandchildren, etc).
        Structure: { name, birth_year, is_deceased, children: [...] }
        """
        if not person:
            return None
        return self._build_tree_node(person, depth)

    def _build_tree_node(self, person, depth):
        """Recursively build a tree node with children (going DOWN)."""
        if depth <= 0:
            return {
                'name': person.full_name,
                'birth_year': person.birth_date.year if person.birth_date else '',
                'is_deceased': bool(person.death_date),
                'children': [],
            }

        node = {
            'name': person.full_name,
            'birth_year': person.birth_date.year if person.birth_date else '',
            'is_deceased': bool(person.death_date),
            'children': [],
        }

        # Get children: persons where THIS person is listed as parent
        children_relations = Relationship.objects.filter(
            from_person=person,
            relation_type__in=['parent', 'father', 'mother']
        ).select_related('to_person')

        for rel in children_relations:
            node['children'].append(
                self._build_tree_node(rel.to_person, depth - 1)
            )

        return node

    def get_ancestor_tree(self, person, depth=4):
        """
        Return a recursive ANCESTORS tree going UPWARDS.
        Structure: { name, birth_year, is_deceased, parents: [...] }
        """
        if not person:
            return None
        return self._build_ancestor_node(person, depth)

    def _build_ancestor_node(self, person, depth):
        """Recursively build ancestor nodes going UP the family tree."""
        if depth <= 0:
            return {
                'name': person.full_name,
                'birth_year': person.birth_date.year if person.birth_date else '',
                'is_deceased': bool(person.death_date),
                'parents': [],
            }

        node = {
            'name': person.full_name,
            'birth_year': person.birth_date.year if person.birth_date else '',
            'is_deceased': bool(person.death_date),
            'parents': [],
        }

        # Get parents: persons listed as parent OF this person
        # Relationship: from_person=PARENT, to_person=THIS_PERSON
        parents = Relationship.objects.filter(
            to_person=person,
            relation_type__in=['parent', 'father', 'mother']
        ).select_related('from_person')

        for rel in parents:
            node['parents'].append(
                self._build_ancestor_node(rel.from_person, depth - 1)
            )

        return node

    # ══════════════════════════════════════════════
    # FAMILY FOUNDER DETECTION
    # ══════════════════════════════════════════════

    def get_family_founder(self, family):
        """Get the founding person of a family."""
        if family.founding_person:
            return family.founding_person

        # Find the oldest person in the family with no parents in the same family
        members = Person.objects.filter(
            family_memberships__family=family
        ).order_by('birth_date')

        for person in members:
            # Check if this person has parents in the same family
            has_parents_in_family = Relationship.objects.filter(
                to_person=person,
                relation_type__in=['parent', 'father', 'mother'],
                from_person__family_memberships__family=family
            ).exists()

            if not has_parents_in_family:
                return person

        return members.first()

    # ══════════════════════════════════════════════
    # DETAILED PERSON DATA (for info panels)
    # ══════════════════════════════════════════════

    def get_person_details(self, person):
        """Get complete details about a person including all relations."""
        if not person:
            return None

        details = {
            'person': {
                'id': person.id,
                'name': person.full_name,
                'gender': person.gender,
                'birth_date': person.birth_date,
                'death_date': person.death_date,
                'photo_url': person.profile_image.url if hasattr(person, 'profile_image') and person.profile_image else None,
            },
            'parents': [],
            'spouses': [],
            'children': [],
            'siblings': [],
            'families': [],
        }

        # Get parents
        parents = Relationship.objects.filter(
            to_person=person,
            relation_type__in=['parent', 'father', 'mother']
        ).select_related('from_person')

        for rel in parents:
            details['parents'].append({
                'id': rel.from_person.id,
                'name': rel.from_person.full_name,
                'gender': rel.from_person.gender,
                'relationship': rel.relation_type,
            })

        # Get children
        children = Relationship.objects.filter(
            from_person=person,
            relation_type__in=['parent', 'father', 'mother']
        ).select_related('to_person')

        for rel in children:
            details['children'].append({
                'id': rel.to_person.id,
                'name': rel.to_person.full_name,
                'gender': rel.to_person.gender,
            })

        # Get spouses
        spouses = Relationship.objects.filter(
            Q(from_person=person) | Q(to_person=person),
            relation_type='spouse'
        ).select_related('from_person', 'to_person')

        for rel in spouses:
            spouse = rel.to_person if rel.from_person == person else rel.from_person
            details['spouses'].append({
                'id': spouse.id,
                'name': spouse.full_name,
                'gender': spouse.gender,
            })

        # Get siblings (same parents)
        if details['parents']:
            parent_ids = [p['id'] for p in details['parents']]
            siblings = Relationship.objects.filter(
                from_person_id__in=parent_ids,
                relation_type__in=['parent', 'father', 'mother']
            ).exclude(to_person=person).select_related('to_person')

            seen = set()
            for rel in siblings:
                if rel.to_person.id not in seen:
                    seen.add(rel.to_person.id)
                    details['siblings'].append({
                        'id': rel.to_person.id,
                        'name': rel.to_person.full_name,
                        'gender': rel.to_person.gender,
                    })

        # Get families
        family_memberships = PersonFamilyMembership.objects.filter(
            person=person
        ).select_related('family')

        for fm in family_memberships:
            details['families'].append({
                'id': fm.family.id,
                'name': fm.family.name,
                'role': fm.get_role_in_family_display(),
            })

        return details

    # ══════════════════════════════════════════════
    # ANCESTORS & DESCENDANTS (flat lists)
    # ══════════════════════════════════════════════

    def get_ancestors(self, person, generations=4):
        """Get all ancestors of a person up to specified generations (flat list)."""
        ancestors = []
        current_level = [person]
        seen_ids = {person.id}

        for gen in range(generations):
            next_level = []
            for p in current_level:
                parents = Relationship.objects.filter(
                    to_person=p,
                    relation_type__in=['parent', 'father', 'mother']
                ).select_related('from_person')

                for rel in parents:
                    if rel.from_person.id not in seen_ids:
                        seen_ids.add(rel.from_person.id)
                        ancestors.append({
                            'person': rel.from_person,
                            'generation': gen + 1,
                            'relationship': rel.relation_type,
                        })
                        next_level.append(rel.from_person)

            current_level = next_level
            if not current_level:
                break

        return ancestors

    def get_descendants(self, person, generations=4):
        """Get all descendants of a person up to specified generations (flat list)."""
        descendants = []
        current_level = [person]
        seen_ids = {person.id}

        for gen in range(generations):
            next_level = []
            for p in current_level:
                children = Relationship.objects.filter(
                    from_person=p,
                    relation_type__in=['parent', 'father', 'mother']
                ).select_related('to_person')

                for rel in children:
                    if rel.to_person.id not in seen_ids:
                        seen_ids.add(rel.to_person.id)
                        descendants.append({
                            'person': rel.to_person,
                            'generation': gen + 1,
                            'relationship': rel.relation_type,
                        })
                        next_level.append(rel.to_person)

            current_level = next_level
            if not current_level:
                break

        return descendants

    # ══════════════════════════════════════════════
    # RELATIONSHIP PATH FINDER
    # ══════════════════════════════════════════════

    def find_relationship_path(self, person1, person2):
        """Find the relationship path between two people using BFS."""
        visited = {person1.id: None}
        queue = deque([person1])

        while queue:
            current = queue.popleft()

            if current.id == person2.id:
                path = []
                while current:
                    path.append(current)
                    current = visited.get(current.id)
                return list(reversed(path))

            relations = Relationship.objects.filter(
                Q(from_person=current) | Q(to_person=current)
            ).select_related('from_person', 'to_person')

            for rel in relations:
                neighbor = rel.to_person if rel.from_person == current else rel.from_person
                if neighbor.id not in visited:
                    visited[neighbor.id] = current
                    queue.append(neighbor)

        return None  # No path found
