from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models.cards import Card


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ['id', 'value', 'user']
        read_only_fields = ['id', 'value']