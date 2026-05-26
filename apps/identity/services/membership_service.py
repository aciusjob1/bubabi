from django.db import transaction
from django.utils import timezone
from apps.core.exceptions import (
    InvalidStatusTransitionError,
    PermissionDeniedError
)
from apps.identity.models import Member, MemberStatusHistory
from apps.identity.constants import MemberStatus
from apps.audit.services.audit_service import AuditService


class MembershipService:

    # ─── Status Transitions ────────────────────────────────

    @transaction.atomic
    def transition_status(self, member, new_status,
                          changed_by, reason='', request=None):
        """
        The ONLY way to change a member's status.
        Validates the transition, records history,
        writes audit log — all in one atomic operation.
        """
        current_status = member.status
        allowed = MemberStatus.TRANSITIONS.get(current_status, [])

        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                f"Cannot move member from "
                f"'{current_status}' to '{new_status}'. "
                f"Allowed transitions: {allowed}"
            )

        # Snapshot before state
        before = {'status': current_status}

        # Apply transition
        member.status = new_status

        if new_status == MemberStatus.ACTIVE and not member.joined_at:
            member.joined_at = timezone.now()

        member.save()

        # Record history
        MemberStatusHistory.objects.create(
            member=member,
            from_status=current_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason
        )

        # Audit log
        AuditService.log(
            actor=changed_by,
            action=f'member.status.{new_status}',
            domain='membership',
            target=member,
            before_state=before,
            after_state={'status': new_status},
            reason=reason,
            request=request
        )

        return member

    # ─── Invitation ────────────────────────────────────────

    @transaction.atomic
    def invite_member(self, person, clan, email,
                      invited_by, phone='', request=None):
        """
        Creates a Member record in INVITED status.
        Person must exist and not be deceased.
        """
        if person.is_deceased:
            raise ValueError(
                "A deceased person cannot be invited as a member."
            )

        if Member.objects.filter(person=person, clan=clan).exists():
            raise ValueError(
                f"{person.full_name} is already a member of {clan.name}."
            )

        if invited_by.status != MemberStatus.ACTIVE:
            raise PermissionDeniedError(
                "Only active members can invite new members."
            )

        member = Member.objects.create_user(
            email=email,
            password=None,
            person=person,
            clan=clan,
            phone=phone,
            status=MemberStatus.INVITED,
            invited_by=invited_by
        )

        AuditService.log(
            actor=invited_by,
            action='member.invited',
            domain='membership',
            target=member,
            after_state={
                'email': email,
                'status': MemberStatus.INVITED
            },
            request=request
        )

        return member

    # ─── Convenience Transition Methods ───────────────────

    def approve_member(self, member, approved_by,
                       reason='', request=None):
        return self.transition_status(
            member, MemberStatus.ACTIVE,
            approved_by, reason, request
        )

    def suspend_member(self, member, suspended_by,
                       reason='', request=None):
        if not reason:
            raise ValueError(
                "A reason is required to suspend a member."
            )
        return self.transition_status(
            member, MemberStatus.SUSPENDED,
            suspended_by, reason, request
        )

    def remove_member(self, member, removed_by,
                      reason='', request=None):
        if not reason:
            raise ValueError(
                "A reason is required to remove a member."
            )
        return self.transition_status(
            member, MemberStatus.REMOVED,
            removed_by, reason, request
        )

    def reinstate_member(self, member, reinstated_by,
                         reason='', request=None):
        return self.transition_status(
            member, MemberStatus.ACTIVE,
            reinstated_by, reason, request
        )

    # ─── Queries ───────────────────────────────────────────

    def get_active_members(self, clan):
        return Member.objects.filter(
            clan=clan,
            status=MemberStatus.ACTIVE
        ).select_related('person')

    def get_elders(self, clan):
        return [
            m for m in self.get_active_members(clan)
            if m.is_elder
        ]

    def get_member_history(self, member):
        return member.status_history.all()