import logging

from django.contrib.auth.models import Group
from rest_framework import serializers

from src.core.control_Id.infra.control_id_django_app.models import Device
from src.core.control_Id.infra.control_id_django_app.models import UserGroup
from src.core.uploader.models import Archive

from .models import User
from .validate import normalize_cpf, normalize_phone, validate_user_dates

logger = logging.getLogger(__name__)


class DeviceBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ["id", "name", "ip", "is_active", "is_default"]


class UserSerializer(serializers.ModelSerializer):
    user_groups = serializers.SerializerMethodField()
    device_admin = serializers.BooleanField(source="is_staff", required=False)
    picture_url = serializers.SerializerMethodField()
    effective_app_role = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    selected_devices = DeviceBasicSerializer(read_only=True, many=True)
    selected_device_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        required=False,
        queryset=Device.objects.all(),
        source="selected_devices",
    )
    picture_id = serializers.PrimaryKeyRelatedField(
        queryset=Archive.objects.all(),
        source="picture",
        write_only=True,
        required=False,
        allow_null=True,
    )
    remove_picture = serializers.BooleanField(
        write_only=True, required=False, default=False
    )

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "cpf",
            "phone",
            "registration",
            "app_role",
            "effective_app_role",
            "panel_access_only",
            "device_scope",
            "selected_devices",
            "selected_device_ids",
            "user_type_id",
            "pin",
            "password",
            "device_admin",
            "user_groups",
            "birth_date",
            "picture_url",
            "picture_id",
            "remove_picture",
            "start_date",
            "end_date",
            "last_passage_at",
        ]
        extra_kwargs = {
            "email": {"required": False, "allow_blank": True, "allow_null": True},
            "cpf": {"required": False, "allow_blank": True, "allow_null": True},
            "phone": {"required": False, "allow_blank": True, "allow_null": True},
            "registration": {
                "required": False,
                "allow_blank": True,
                "allow_null": True,
            },
        }

    def get_user_groups(self, obj):
        group_ids = UserGroup.objects.filter(user=obj).values_list(
            "group_id", flat=True
        )
        return [
            {"id": group.pk, "name": group.name}
            for group in Group.objects.filter(id__in=group_ids)
        ]

    def get_picture_url(self, obj):
        picture = getattr(obj, "picture", None)
        if picture is None:
            picture_id = getattr(obj, "picture_id", None)
            if picture_id is not None:
                try:
                    from src.core.uploader.models import Archive

                    picture = Archive.objects.get(pk=picture_id)
                except Archive.DoesNotExist:
                    picture = None
        if picture is None or not picture.arquivo:
            return None
        try:
            return picture.arquivo.url
        except (OSError, ValueError):
            logger.warning(
                "Failed to resolve picture URL for user %s (archive %s)",
                obj.id,
                getattr(obj, "picture_id", None),
            )
            return None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        app_role = attrs.get("app_role")
        email = attrs.get("email")
        password = attrs.get("password")
        panel_access_only = attrs.get(
            "panel_access_only",
            instance.panel_access_only if instance else False,
        )
        device_scope = attrs.get(
            "device_scope",
            instance.device_scope if instance else User.DeviceScope.ALL_ACTIVE,
        )
        selected_devices = attrs.get(
            "selected_devices",
            instance.selected_devices.all() if instance else [],
        )

        current_role = instance.app_role if instance else User.AppRole.NONE
        current_email = instance.email if instance else None
        effective_role = app_role if app_role is not None else current_role
        effective_email = email if email is not None else current_email

        if (
            effective_role
            in (User.AppRole.ADMIN, User.AppRole.GUARITA, User.AppRole.SISAE)
            and not effective_email
        ):
            raise serializers.ValidationError(
                {"email": ["Perfis de painel exigem um e-mail para login."]}
            )

        if (
            instance is None
            and effective_role
            in (User.AppRole.ADMIN, User.AppRole.GUARITA, User.AppRole.SISAE)
            and not password
        ):
            raise serializers.ValidationError(
                {"password": ["Perfis de painel exigem uma senha ao criar a conta."]}
            )

        if panel_access_only is True and not effective_role:
            raise serializers.ValidationError(
                {
                    "panel_access_only": [
                        "Contas somente do painel precisam ter um perfil de aplicacao."
                    ]
                }
            )

        if panel_access_only and device_scope != User.DeviceScope.NONE:
            raise serializers.ValidationError(
                {
                    "device_scope": [
                        "Contas somente do painel devem usar o escopo 'none'."
                    ]
                }
            )

        if device_scope == User.DeviceScope.SELECTED and len(selected_devices) == 0:
            raise serializers.ValidationError(
                {
                    "selected_device_ids": [
                        "Selecione ao menos uma catraca quando o escopo for 'selected'."
                    ]
                }
            )

        user_type_id = attrs.get(
            "user_type_id",
            instance.user_type_id if instance else None,
        )
        phone = attrs.get("phone", instance.phone if instance else None)

        if user_type_id == User.UserType.VISITOR and not phone:
            raise serializers.ValidationError(
                {"phone": ["Telefone e obrigatorio para visitantes."]}
            )

        try:
            validate_user_dates(
                {
                    "start_date": attrs.get(
                        "start_date",
                        instance.start_date if instance else None,
                    ),
                    "end_date": attrs.get(
                        "end_date",
                        instance.end_date if instance else None,
                    ),
                }
            )
        except ValueError as exc:
            raise serializers.ValidationError({"end_date": [str(exc)]}) from exc

        return attrs

    def validate_email(self, value):
        if value in ("", None):
            return None
        return value.strip().lower()

    def validate_registration(self, value):
        if value in ("", None):
            return None
        return value.strip()

    def validate_cpf(self, value):
        try:
            return normalize_cpf(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_phone(self, value):
        try:
            return normalize_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_user_type_id(self, value):
        if value in (0, "0", "", None):
            return None
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        selected_devices = validated_data.pop("selected_devices", [])
        validated_data.pop("remove_picture", False)
        logger.info(
            "create(): picture=%s, picture_id_raw=%s, fields=%s",
            validated_data.get("picture"),
            validated_data.get("picture_id"),
            list(validated_data.keys()),
        )
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        if selected_devices:
            user.selected_devices.set(selected_devices)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        selected_devices = validated_data.pop("selected_devices", None)
        remove_picture = validated_data.pop("remove_picture", False)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if remove_picture:
            instance.picture = None
        instance.save()
        if selected_devices is not None:
            instance.selected_devices.set(selected_devices)
        return instance


class RoleAwareUserReadSerializer(UserSerializer):
    ROLE_FIELDS = {
        User.AppRole.ADMIN: None,
        "sisae": {
            "id",
            "name",
            "registration",
            "pin",
            "cpf",
            "phone",
            "email",
            "user_groups",
            "device_scope",
            "selected_devices",
            "birth_date",
            "picture_url",
            "start_date",
            "end_date",
            "last_passage_at",
        },
        "guarita": {
            "id",
            "name",
            "registration",
            "cpf",
            "phone",
            "email",
            "user_type_id",
            "device_scope",
            "selected_devices",
            "start_date",
            "end_date",
            "last_passage_at",
        },
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
