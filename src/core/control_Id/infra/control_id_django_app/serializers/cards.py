from src.core.user.infra.user_django_app.models import User
from rest_framework import serializers
from src.core.control_Id.infra.control_id_django_app.models import Card, Device


class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'registration']


class CardSerializer(serializers.ModelSerializer):
    # ✅ Saída: mostra os dados básicos do usuário
    user = UserBasicSerializer(read_only=True)

    # ✅ Entrada: permite enviar apenas o id do usuário
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=User.objects.all(),
        source="user",  # preenche o campo user do model
        required=True
    )

    enrollment_device_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=True,
        queryset=Device.objects.all(),
        help_text="Catraca que será usada para cadastro do cartão"
    )

    class Meta:
        model = Card
        fields = ['id', 'value', 'user', 'user_id', 'enrollment_device_id']
        read_only_fields = ['id', 'value']

    def create(self, validated_data):
        validated_data.pop('enrollment_device_id', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('enrollment_device_id', None)
        return super().update(instance, validated_data)
