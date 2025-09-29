from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers
from django.db import transaction
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from src.core.control_Id.infra.control_id_django_app.models import UserGroup, CustomGroup
from src.core.user.infra.user_django_app.models import User
from src.core.control_Id.infra.control_id_django_app.serializers import UserGroupSerializer

import pandas as pd
import io


class UserGroupImportSerializer(serializers.Serializer):
    """Serializer para importação de usuários em grupo"""
    file = serializers.FileField(
        help_text="Arquivo Excel (.xlsx) com usuários para importar. Deve conter colunas 'MATRICULA' e 'NOME_COMPLETO'."
    )
    group_id = serializers.IntegerField(
        help_text="ID do grupo para adicionar os usuários"
    )

    def validate(self, data):
        """Validação personalizada para o arquivo e grupo"""
        # Verifica se o grupo existe
        try:
            group = CustomGroup.objects.get(id=data['group_id'])
        except CustomGroup.DoesNotExist:
            raise serializers.ValidationError({"group_id": "Grupo não encontrado"})

        # Verifica se o arquivo é um Excel
        file = data.get('file')
        if not file:
            raise serializers.ValidationError({"file": "Arquivo é obrigatório"})
        
        if not file.name.lower().endswith(('.xls', '.xlsx')):
            raise serializers.ValidationError({"file": "Formato de arquivo inválido. Use .xlsx"})

        return data


class UserGroupViewSet(viewsets.ModelViewSet):
    """ViewSet para gerenciamento de grupos de usuários"""
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    filterset_fields = ['user', 'group']
    search_fields = ['user__name', 'group__name']
    ordering_fields = ['user__name', 'group__name']

    @extend_schema(
        summary="Importar usuários para um grupo",
        description="""
        Importa usuários de um arquivo Excel para um grupo específico.
        
        Formato do arquivo Excel:
        - Colunas obrigatórias: 
          * MATRICULA: Matrícula do usuário
          * NOME_COMPLETO: Nome completo do usuário
        
        Comportamento:
        - Usuários são buscados pela matrícula
        - Usuários já existentes no grupo são ignorados
        - Usuários não encontrados são listados nos erros
        
        Exemplo de uso via cURL:
        ```
        curl -X POST -F "file=@usuarios.xlsx" -F "group_id=123" /api/user-groups/import-users/
        ```
        
        Resposta de exemplo:
        ```json
        {
            "message": "Importação de usuários concluída",
            "estatisticas": {
                "total_usuarios": 10,
                "usuarios_adicionados": 7,
                "usuarios_ja_existentes": 2,
                "usuarios_nao_encontrados": 1,
                "erros": ["Usuário não encontrado: 12345 - João Silva"]
            }
        }
        ```
        """,
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'group_id': {'type': 'integer'}
                }
            }
        },
        responses={
            200: {
                'description': 'Importação bem-sucedida',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'Importação de usuários concluída',
                            'estatisticas': {
                                'total_usuarios': 10,
                                'usuarios_adicionados': 7,
                                'usuarios_ja_existentes': 2,
                                'usuarios_nao_encontrados': 1,
                                'erros': []
                            }
                        }
                    }
                }
            },
            400: {'description': 'Erro de validação do arquivo'},
            404: {'description': 'Nenhum usuário encontrado'},
            207: {'description': 'Importação parcial com erros'}
        }
    )
    @action(
        detail=False, 
        methods=['POST'], 
        parser_classes=[MultiPartParser, FormParser],
        serializer_class=UserGroupImportSerializer
    )
    def import_users(self, request):
        """
        Importa usuários de um arquivo Excel para um grupo específico
        
        Formato do arquivo Excel:
        - Colunas obrigatórias: MATRICULA, NOME_COMPLETO
        - Exemplo de uso:
          curl -X POST -F "file=@usuarios.xlsx" -F "group_id=123" /api/user-groups/import-users/
        """
        # Adiciona diagnóstico detalhado de upload
        print("[DEBUG] Arquivos recebidos:", request.FILES)
        print("[DEBUG] Dados do POST:", request.POST)
        
        # Verifica se há arquivos
        if not request.FILES:
            return Response(
                {"error": "Nenhum arquivo enviado", "details": "request.FILES está vazio"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            # Adiciona mais detalhes sobre o erro de validação
            return Response(
                {
                    "error": "Erro de validação", 
                    "details": str(e),
                    "validation_errors": e.detail
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Dados validados
        file = serializer.validated_data['file']
        group_id = serializer.validated_data['group_id']
        
        # Diagnóstico adicional do arquivo
        print(f"[DEBUG] Arquivo recebido: nome={file.name}, tamanho={file.size}, tipo={file.content_type}")
        
        group = CustomGroup.objects.get(id=group_id)
        
        # Lê o arquivo Excel
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return Response(
                {
                    "error": f"Erro ao ler arquivo Excel: {str(e)}",
                    "details": {
                        "filename": file.name,
                        "file_size": file.size,
                        "file_type": file.content_type
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Valida colunas
        required_columns = {'Matrícula', 'Nome'}
        if not required_columns.issubset(df.columns):
            return Response(
                {"error": f"Colunas obrigatórias ausentes. Esperado: {required_columns}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Estatísticas de importação
        stats = {
            'total_usuarios': len(df),
            'usuarios_adicionados': 0,
            'usuarios_ja_existentes': 0,
            'usuarios_nao_encontrados': 0,
            'erros': []
        }
        
        # Processamento em transação
        with transaction.atomic():
            for _, row in df.iterrows():
                try:
                    # Busca usuário pela matrícula
                    registration = str(row['Matrícula']).strip()
                    name = str(row['Nome']).strip()
                    
                    # Tenta encontrar usuário pela matrícula
                    user = User.objects.filter(registration=registration).first()
                    
                    if not user:
                        # Se não encontrar, pula
                        stats['usuarios_nao_encontrados'] += 1
                        stats['erros'].append(f"Usuário não encontrado: {registration} - {name}")
                        continue
                    
                    # Verifica se já está no grupo
                    existing_group = UserGroup.objects.filter(user=user, group=group).exists()
                    if existing_group:
                        stats['usuarios_ja_existentes'] += 1
                        continue
                    
                    # Adiciona ao grupo
                    UserGroup.objects.create(user=user, group=group)
                    stats['usuarios_adicionados'] += 1
                
                except Exception as e:
                    # Registra erro para este usuário
                    stats['erros'].append(f"Erro ao processar {registration} - {name}: {str(e)}")
        
        # Prepara resposta
        response_data = {
            "message": "Importação de usuários concluída",
            "estatisticas": stats
        }
        
        # Determina status de resposta
        if stats['usuarios_nao_encontrados'] == stats['total_usuarios']:
            # Nenhum usuário encontrado
            return Response(response_data, status=status.HTTP_404_NOT_FOUND)
        elif stats['erros']:
            # Alguns erros ocorreram
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        else:
            # Importação bem-sucedida
            return Response(response_data, status=status.HTTP_200_OK)