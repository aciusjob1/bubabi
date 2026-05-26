from django.shortcuts import render, redirect
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from apps.governance.models import Vote, VoteCast, MemberRole
from apps.governance.forms import VoteForm, AssignRoleForm
from apps.governance.constants import VoteChoice, VoteStatus
from django.shortcuts import render, redirect, get_object_or_404


@login_required
def create_vote_view(request):
    if request.method == 'POST':
        form = VoteForm(request.POST)
        if form.is_valid():
            vote = form.save(commit=False)
            vote.clan         = request.user.clan
            vote.initiated_by = request.user
            vote.status       = VoteStatus.OPEN
            vote.save()
            messages.success(
                request, f"Vote '{vote.topic}' created."
            )
            return redirect('dashboard')
    else:
        form = VoteForm()
    return render(request, 'forms/vote_form.html', {'form': form})


@login_required
def cast_vote_view(request, vote_pk):
    vote   = Vote.objects.get(
        pk=vote_pk, clan=request.user.clan
    )
    choice = request.POST.get('choice')

    if vote.initiated_by == request.user:
        messages.error(
            request, "You cannot vote on a vote you initiated."
        )
        return redirect('dashboard')

    already = VoteCast.objects.filter(
        vote=vote, member=request.user
    ).exists()

    if already:
        messages.error(request, "You have already voted.")
        return redirect('dashboard')

    if choice in [VoteChoice.YES, VoteChoice.NO, VoteChoice.ABSTAIN]:
        weight = 2.0 if request.user.is_elder else 1.0
        VoteCast.objects.create(
            vote=vote,
            member=request.user,
            choice=choice,
            weight=weight
        )
        messages.success(request, f"Vote cast: {choice.upper()}")
    return redirect('dashboard')


@login_required
def assign_role_view(request, pk):       # ← changed from member_pk to pk
    from apps.identity.models import Member
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    if request.method == 'POST':
        form = AssignRoleForm(request.POST, clan=request.user.clan)
        if form.is_valid():
            MemberRole.objects.update_or_create(
                member=member,
                role=form.cleaned_data['role'],
                defaults={
                    'assigned_by': request.user,
                    'is_active':   True
                }
            )
            messages.success(
                request,
                f"Role assigned to {member.person.full_name}."
            )
            return redirect('members')
    else:
        form = AssignRoleForm(
            initial={'member_id': pk},
            clan=request.user.clan
        )
    return render(request, 'forms/role_form.html', {
        'form': form, 'member': member
    })
@login_required
def approval_list_view(request):
    """Elder council: view and vote on pending approvals."""
    from .models import ApprovalRequest, ApprovalVote
    clan = request.user.clan
    approvals = ApprovalRequest.objects.filter(clan=clan, status='pending').select_related('initiated_by__person').prefetch_related('votes').order_by('-created_at')
    
    if request.method == 'POST':
        approval_id = request.POST.get('approval_id')
        vote = request.POST.get('vote')  # 'approve' or 'reject'
        approval = get_object_or_404(ApprovalRequest, id=approval_id, clan=clan)
        
        # Record the vote
        ApprovalVote.objects.update_or_create(
            request=approval,
            voter=request.user,
            defaults={'vote': vote}
        )
        
        # Check if threshold met
        if approval.approval_count >= approval.minimum_approvals:
            approval.status = 'approved'
            approval.resolved_at = timezone.now()
            approval.save()
            messages.success(request, f"'{approval.action_type}' has been approved!")
        elif approval.rejection_count >= approval.minimum_approvals:
            approval.status = 'rejected'
            approval.resolved_at = timezone.now()
            approval.save()
            messages.warning(request, f"'{approval.action_type}' has been rejected.")
        
        return redirect('approval-list')
    
    return render(request, 'governance/approvals.html', {'approvals': approvals})
