from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer
import requests
from django.conf import settings

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = None
        self.catraka_url = settings.CATRAKA_URL
        self.catraka_user = settings.CATRAKA_USER
        self.catraka_pass = settings.CATRAKA_PASS

    def login(self):
        if self.session:
            return self.session
        response = requests.post(f"{self.catraka_url}/login.fcgi", json={
            "login": self.catraka_user,
            "password": self.catraka_pass
        })
        response.raise_for_status()
        self.session = response.json().get("session")
        return self.session

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Criar no banco local
        user = serializer.save()

        # Criar na catraca
        try:
            sess = self.login()
            response = requests.post(f"{self.catraka_url}/create_objects.fcgi?session={sess}", json={
                "object": "users",
                "values": [{
                    "id": user.id,
                    "name": user.name,
                    "registration": user.registration
                }]
            })
            response.raise_for_status()
        except requests.RequestException as e:
            user.delete()  # Reverte se falhar na catraca
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Atualizar no banco local
        serializer.save()

        # Atualizar na catraca
        try:
            sess = self.login()
            response = requests.post(f"{self.catraka_url}/update_objects.fcgi?session={sess}", json={
                "object": "users",
                "values": [{
                    "id": instance.id,
                    "name": serializer.validated_data.get("name", instance.name),
                    "registration": serializer.validated_data.get("registration", instance.registration)
                }],
                "where": {"users": {"id": instance.id}}
            })
            response.raise_for_status()
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Deletar na catraca
        try:
            sess = self.login()
            response = requests.post(f"{self.catraka_url}/destroy_objects.fcgi?session={sess}", json={
                "object": "users",
                "where": {"users": {"id": instance.id}}
            })
            response.raise_for_status()
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Deletar no banco local
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def sync(self, request):
        try:
            sess = self.login()
            # Carregar usuários da catraca
            response = requests.post(f"{self.catraka_url}/load_objects.fcgi?session={sess}", json={
                "object": "users",
                "fields": ["id", "name", "registration"],
                "order_by": ["id"]
            })
            response.raise_for_status()
            catraca_users = response.json().get("users", [])

            # Apagar todos os usuários do banco local
            User.objects.all().delete()

            # Cadastrar usuários da catraca no banco local
            for user_data in catraca_users:
                User.objects.create(
                    id=user_data["id"],
                    name=user_data["name"],
                    registration=user_data.get("registration", "")
                )

            return Response({"success": True, "message": f"Sincronizados {len(catraca_users)} usuários"})
        except requests.RequestException as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)