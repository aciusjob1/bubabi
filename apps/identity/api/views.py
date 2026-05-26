from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.identity.models import Person, Member
from apps.identity.services.membership_service import MembershipService
from .serializers import (
    PersonSerializer, MemberSerializer,
    MemberStatusHistorySerializer,
    InviteMemberSerializer,
    TransitionStatusSerializer
)

service = MembershipService()


class PersonListCreateView(generics.ListCreateAPIView):
    serializer_class   = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Person.objects.filter(
            memberships__clan=self.request.user.clan
        ).distinct()


class PersonDetailView(generics.RetrieveUpdateAPIView):
    serializer_class   = PersonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Person.objects.filter(
            memberships__clan=self.request.user.clan
        ).distinct()


class MemberListView(generics.ListAPIView):
    serializer_class   = MemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Member.objects.filter(
            clan=self.request.user.clan
        ).select_related('person', 'clan')


class MemberDetailView(generics.RetrieveAPIView):
    serializer_class   = MemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Member.objects.filter(
            clan=self.request.user.clan
        )


class MemberHistoryView(generics.ListAPIView):
    serializer_class   = MemberStatusHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        member = Member.objects.get(
            pk=self.kwargs['pk'],
            clan=self.request.user.clan
        )
        return member.status_history.all()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    serializer = MemberSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_member(request):
    serializer = InviteMemberSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from apps.identity.models import Person
        person = Person.objects.get(
            pk=serializer.validated_data['person_id']
        )
        member = service.invite_member(
            person=person,
            clan=request.user.clan,
            email=serializer.validated_data['email'],
            phone=serializer.validated_data.get('phone', ''),
            invited_by=request.user,
            request=request
        )
        return Response(
            MemberSerializer(member).data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def transition_member_status(request, pk):
    serializer = TransitionStatusSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        member = Member.objects.get(
            pk=pk,
            clan=request.user.clan
        )
        updated = service.transition_status(
            member=member,
            new_status=serializer.validated_data['new_status'],
            changed_by=request.user,
            reason=serializer.validated_data.get('reason', ''),
            request=request
        )
        return Response(MemberSerializer(updated).data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )