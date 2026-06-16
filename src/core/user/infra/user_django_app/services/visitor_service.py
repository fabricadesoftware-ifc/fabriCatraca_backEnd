from __future__ import annotations

from django.utils import timezone

from src.core.user.infra.user_django_app.models import User, Visitas


class VisitorService:
    def is_visitor(self, user: User) -> bool:
        return user.user_type_id == User.UserType.VISITOR

    def is_visitor_payload(self, validated_data: dict) -> bool:
        return validated_data.get("user_type_id") == User.UserType.VISITOR

    def find_existing_visitor(self, validated_data: dict) -> User | None:
        visitors = User.objects.filter(
            deleted_at__isnull=True,
            user_type_id=User.UserType.VISITOR,
        )

        cpf = validated_data.get("cpf")
        if cpf:
            existing = visitors.filter(cpf=cpf).first()
            if existing:
                return existing

        registration = validated_data.get("registration")
        if registration:
            existing = visitors.filter(registration=registration).first()
            if existing:
                return existing

        phone = validated_data.get("phone")
        if phone:
            phone_matches = visitors.filter(phone=phone)
            if phone_matches.count() == 1:
                return phone_matches.first()

            name = validated_data.get("name")
            if name:
                name_matches = phone_matches.filter(name__iexact=name)
                if name_matches.count() == 1:
                    return name_matches.first()

        email = validated_data.get("email")
        if email:
            email_matches = visitors.filter(email=email)
            if email_matches.count() == 1:
                return email_matches.first()

        return None

    def create_visit_record(
        self,
        user: User,
        request_user: User,
        card=None,
    ) -> Visitas:
        visit_date = user.start_date or timezone.now()
        visit = Visitas.objects.create(
            user=user,
            created_by=request_user,
            visit_date=visit_date,
            end_date=user.end_date,
            card=card,
        )
        if visit.end_date and visit.end_date > timezone.now():
            from src.core.user.infra.user_django_app.tasks import expire_visit

            expire_visit.apply_async(kwargs={"visit_id": visit.id}, eta=visit.end_date)
        return visit
