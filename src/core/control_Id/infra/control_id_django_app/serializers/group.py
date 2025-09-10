from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup
from src.core.user.infra.user_django_app.models import User

class CustomGroupSerializer(serializers.ModelSerializer):
    users = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroup
        fields = ['id', 'name', 'users']
        read_only_fields = ['id']

    def get_users(self, obj):
        return [{'id': user.id, 'name': user.name} for user in User.objects.filter(usergroup__group=obj)]