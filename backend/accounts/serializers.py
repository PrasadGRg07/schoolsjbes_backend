from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminProfileSerializer(serializers.ModelSerializer):
    # The dashboard reads this to decide which sign-in area a person belongs to.
    role = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'display_name']
        read_only_fields = ['id', 'username', 'role', 'display_name']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
