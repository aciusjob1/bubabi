from rest_framework import serializers
from apps.identity.models import Person, Clan, Member, MemberStatusHistory


class PersonSerializer(serializers.ModelSerializer):
    age        = serializers.ReadOnlyField()
    is_deceased = serializers.ReadOnlyField()

    class Meta:
        model  = Person
        fields = [
            'id', 'full_name', 'gender',
            'birth_date', 'death_date',
            'biography', 'age', 'is_deceased',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClanSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Clan
        fields = [
            'id', 'name', 'description',
            
            
        ]
        read_only_fields = ['id']


class MemberSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(
        source='person.full_name', read_only=True
    )
    clan_name   = serializers.CharField(
        source='clan.name', read_only=True
    )
    is_elder    = serializers.ReadOnlyField()

    class Meta:
        model  = Member
        fields = [
            'id', 'email', 'phone',
            'person', 'person_name',
            'clan', 'clan_name',
            'status', 'is_elder',
            'joined_at', 'invited_at'
        ]
        read_only_fields = [
            'id', 'invited_at', 'joined_at', 'status'
        ]


class MemberStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(
        source='changed_by.person.full_name',
        read_only=True
    )

    class Meta:
        model  = MemberStatusHistory
        fields = [
            'id', 'from_status', 'to_status',
            'changed_by', 'changed_by_name',
            'reason', 'timestamp'
        ]
        read_only_fields = fields


class InviteMemberSerializer(serializers.Serializer):
    person_id = serializers.UUIDField()
    email     = serializers.EmailField()
    phone     = serializers.CharField(required=False, default='')


class TransitionStatusSerializer(serializers.Serializer):
    new_status = serializers.CharField()
    reason     = serializers.CharField(required=False, default='')