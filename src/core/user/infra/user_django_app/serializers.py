from rest_framework import serializers
from .models import User
from django.contrib.auth.models import Group


class UserSerializer(serializers.ModelSerializer):
    user_groups = serializers.SerializerMethodField()
    device_admin = serializers.BooleanField(source="is_staff", required=False)
    effective_app_role = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "registration",
            "app_role",
            "effective_app_role",
            "panel_access_only",
            "user_type_id",
            "pin",
            "password",
            "device_admin",
            "user_groups",
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True, "allow_null": True},
        }

    def get_user_groups(self, obj):
        return [
            {"id": group.pk, "name": group.name}
            for group in Group.objects.filter(usergroup__user=obj)
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        app_role = attrs.get("app_role")
        email = attrs.get("email")
        password = attrs.get("password")
        panel_access_only = attrs.get("panel_access_only")

        current_role = instance.app_role if instance else User.AppRole.NONE
        current_email = instance.email if instance else None
        effective_role = app_role if app_role is not None else current_role
        effective_email = email if email is not None else current_email

        if (
            effective_role
            in (
                User.AppRole.ADMIN,
                User.AppRole.GUARITA,
                User.AppRole.SISAE,
            )
            and not effective_email
        ):
            raise serializers.ValidationError(
                {"email": ["Perfis de painel exigem um e-mail para login."]}
            )

        if (
            instance is None
            and effective_role
            in (
                User.AppRole.ADMIN,
                User.AppRole.GUARITA,
                User.AppRole.SISAE,
            )
            and not password
        ):
            raise serializers.ValidationError(
                {"password": ["Perfis de painel exigem uma senha ao criar a conta."]}
            )

        if panel_access_only is True and not effective_role:
            raise serializers.ValidationError(
                {
                    "panel_access_only": [
                        "Contas somente do painel precisam ter um perfil de aplicação."
                    ]
                }
            )

        return attrs

    def validate_email(self, value):
        if value in ("", None):
            return None
        return value.strip().lower()

    def validate_registration(self, value):
        if value in ("", None):
            return None
        return value.strip()

    def validate_user_type_id(self, value):
        """Normaliza valores inválidos para None.

        A catraca rejeita chaves estrangeiras inválidas. Quando recebemos 0 (ou strings vazias),
        tratamos como None para representar "sem tipo" e evitar violar constraints no device.
        """
        if value in (0, "0", "", None):
            return None
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RoleAwareUserReadSerializer(UserSerializer):
    ROLE_FIELDS = {
        User.AppRole.ADMIN: None,  # None = todos os campos
        "sisae": {
            "id",
            "name",
            "registration",
            "pin",
            "user_groups",
        },
        "guarita": {"id", "name", "registration"},
    }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        role = getattr(user, "effective_app_role", User.AppRole.NONE)
        allowed = self.ROLE_FIELDS.get(role)

        if allowed is None:
            return data
        return {k: v for k, v in data.items() if k in allowed}
