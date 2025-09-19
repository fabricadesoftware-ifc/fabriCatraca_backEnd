from src.core.user.infra.user_django_app.models import User
from src.core.user.infra.user_django_app.serializers import UserSerializer
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup as Group
from src.core.control_Id.infra.control_id_django_app.models import UserGroup
from src.core.control_Id.infra.control_id_django_app.models.device import Device
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import serializers
from src.core.__seedwork__.infra import ControlIDSyncMixin
from django.db import transaction
import pandas as pd
import re
import tempfile
from django.core.files.uploadedfile import InMemoryUploadedFile
import os


class FileUploadSerializer(serializers.Serializer):
    """Serializer para upload de arquivo Excel"""
    file = serializers.FileField(
        help_text="Arquivo Excel (.xlsx) com usuários para importar. Formato: abas como '1INFO1(2025)', '1AGRO1(2025)', ou '1QUIMI (2025)' com colunas ORDEM, MATRICULA, NOME_COMPLETO"
    )


class ImportUsersView(ControlIDSyncMixin, APIView):
    """
    View to import users (students) from an Excel file with multiple sheets (grupos).
    Each sheet represents a grupo (e.g., '1INFO1(2025)', '1AGRO1(2025)', '1QUIMI (2025)'), and creates/updates users
    associated with the parsed grupo via M2M relation (UserGroup).
    Also creates users in all active catracas automatically.
    """
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = FileUploadSerializer
    
    def get(self, request, *args, **kwargs):
        """
        Retorna informações sobre como usar a API de importação.
        """
        return Response({
            "message": "Upload de arquivo Excel para importação de usuários",
            "instructions": {
                "method": "POST",
                "content_type": "multipart/form-data",
                "field_name": "file",
                "file_format": ".xlsx",
                "sheet_format": "1INFO1(2025), 1AGRO1(2025), 1QUIMI (2025), etc.",
                "required_columns": ["ORDEM", "MATRICULA", "NOME_COMPLETO"]
            },
            "example": {
                "curl": "curl -X POST -F 'file=@usuarios.xlsx' http://localhost:8000/api/control_id/import-users/"
            }
        })
    
    def create_user_in_catraca(self, user):
        """
        Cria o usuário em todas as catracas ativas usando a mesma lógica do UserViewSet.
        """
        try:
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"
            
            for device in devices:
                self.set_device(device)
                
                response = self.create_objects("users", [{
                    "id": user.id,
                    "name": user.name,
                    "registration": user.registration,
                }])
                
                if response.status_code != status.HTTP_201_CREATED:
                    return False, f"Erro ao criar usuário na catraca {device.name}: {response.data}"
                
                device.users.add(user)
            
            return True, "Usuário criado com sucesso em todas as catracas"
            
        except Exception as e:
            return False, f"Erro ao criar usuário na catraca: {str(e)}"
    
    def create_group_in_catraca(self, group):
        """
        Cria o grupo em todas as catracas ativas.
        """
        try:
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"
            
            for device in devices:
                self.set_device(device)
                
                response = self.create_objects("groups", [{
                    "id": group.id,
                    "name": group.name
                }])
                
                if response.status_code != status.HTTP_201_CREATED:
                    return False, f"Erro ao criar grupo na catraca {device.name}: {response.data}"
            
            return True, "Grupo criado com sucesso em todas as catracas"
            
        except Exception as e:
            return False, f"Erro ao criar grupo na catraca: {str(e)}"
    
    def create_user_group_relation_in_catraca(self, user, group):
        """
        Cria a relação usuário-grupo em todas as catracas ativas.
        """
        try:
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return False, "Nenhuma catraca ativa encontrada"
            
            for device in devices:
                self.set_device(device)
                
                response = self.create_objects("user_groups", [{
                    "user_id": user.id,
                    "group_id": group.id
                }])
                
                if response.status_code != status.HTTP_201_CREATED:
                    return False, f"Erro ao criar relação usuário-grupo na catraca {device.name}: {response.data}"
            
            return True, "Relação usuário-grupo criada com sucesso em todas as catracas"
            
        except Exception as e:
            return False, f"Erro ao criar relação usuário-grupo na catraca: {str(e)}"
    
    def post(self, request, *args, **kwargs):
        try:
            file: InMemoryUploadedFile = request.FILES.get('file')
            if not file:
                return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Verifica se o arquivo é um Excel válido
            if not re.match(r'.*\.xlsx$', file.name):
                return Response({"error": "Invalid file format. Please upload an .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Salva o arquivo temporariamente
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                for chunk in file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
                tmp.flush()
            
            # Lê o arquivo Excel e obtém nomes das abas
            excel_file = pd.ExcelFile(tmp_path)
            sheet_names = excel_file.sheet_names
            excel_file.close()
            
            if not sheet_names:
                try:
                    os.unlink(tmp_path)
                except:
                    pass
                return Response({"error": "No sheets found in the Excel file."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Estatísticas gerais
            created_users = 0
            updated_users = 0
            created_groups = 0
            updated_groups = 0
            created_relations = 0
            catraca_errors = []
            errors = []
            
            for sheet_name in sheet_names:
                # Carrega os dados da aba
                df = pd.read_excel(tmp_path, sheet_name=sheet_name)
                
                # Padroniza colunas
                if len(df.columns) != 3:
                    errors.append(f"Sheet '{sheet_name}': Expected exactly 3 columns (ORDEM, MATRICULA, NOME_COMPLETO)")
                    continue
                df.columns = ['ORDEM', 'MATRICULA', 'NOME_COMPLETO']
                
                # Verifica colunas requeridas
                required_columns = {'MATRICULA', 'NOME_COMPLETO'}
                if not required_columns.issubset(df.columns):
                    errors.append(f"Sheet '{sheet_name}': Missing required columns: {required_columns - set(df.columns)}")
                    continue
                
                # Verifica se a aba tem dados
                if df.empty:
                    errors.append(f"Sheet '{sheet_name}': No data found in the sheet")
                    continue
                
                # Parseia o nome da aba
                nome_grupo = None
                match_full = re.match(r'(\d+)([A-Z]+)(\d+)\s*\((\d+)\)', sheet_name.strip())  # Ex.: 1INFO1(2025), 1AGRO2(2025)
                match_quimi = re.match(r'(\d+)(QUIMI)(\s*\((\d+)\))?', sheet_name.strip())  # Ex.: 1QUIMI or 1QUIMI (2025)
                
                if match_full:
                    nivel = int(match_full.group(1))  # Ex.: 1
                    curso = match_full.group(2)       # Ex.: INFO, AGRO
                    secao = int(match_full.group(3))  # Ex.: 1
                    nome_grupo = f"{nivel}{curso}{secao}"  # Ex.: 1INFO1
                elif match_quimi:
                    nivel = int(match_quimi.group(1))  # Ex.: 1
                    curso = match_quimi.group(2)       # QUIMI
                    nome_grupo = f"{nivel}{curso}"     # Ex.: 1QUIMI
                else:
                    errors.append(f"Sheet '{sheet_name}': Invalid sheet name format. Expected: '1INFO1(2025)', '1AGRO1(2025)', or '1QUIMI (2025)'")
                    continue
                
                # Cria ou atualiza o Grupo
                with transaction.atomic():
                    grupo, grupo_created = Group.objects.update_or_create(
                        name=nome_grupo
                    )
                    if grupo_created:
                        created_groups += 1
                        success, message = self.create_group_in_catraca(grupo)
                        if not success:
                            catraca_errors.append(f"Grupo {grupo.name}: {message}")
                    else:
                        updated_groups += 1
                
                    # Para cada aluno, cria/atualiza User e cria a relação UserGroup
                    for idx, row in df.iterrows():
                        if pd.isna(row['MATRICULA']) or pd.isna(row['NOME_COMPLETO']):
                            errors.append(f"Sheet '{sheet_name}', row {idx+2}: Missing MATRICULA or NOME_COMPLETO")
                            continue
                        
                        email = f"{row['MATRICULA']}@escola.edu"
                        
                        user, user_created = User.objects.update_or_create(
                            email=email,
                            defaults={
                                'name': str(row['NOME_COMPLETO']).strip(),
                                'registration': str(row['MATRICULA']).strip(),
                                'is_active': True
                            }
                        )
                        
                        if user_created:
                            created_users += 1
                            success, message = self.create_user_in_catraca(user)
                            if not success:
                                catraca_errors.append(f"Usuário {user.name} ({user.registration}): {message}")
                        else:
                            updated_users += 1
                        
                        relacao_existente, created = UserGroup.objects.get_or_create(
                            user=user,
                            group=grupo
                        )
                        if created:
                            created_relations += 1
                            success, message = self.create_user_group_relation_in_catraca(user, grupo)
                            if not success:
                                catraca_errors.append(f"Relação {user.name}-{grupo.name}: {message}")
            
            # Limpa o arquivo temp
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            response_data = {
                "success": True,
                "message": f"Import completed. Groups: Created {created_groups}, Updated {updated_groups}. Users: Created {created_users}, Updated {updated_users}. Relations: Created {created_relations}",
                "sheets_processed": len(sheet_names),
                "errors": errors if errors else None,
                "catraca_errors": catraca_errors if catraca_errors else None
            }
            
            status_code = status.HTTP_200_OK if not (errors or catraca_errors) else status.HTTP_207_MULTI_STATUS
            return Response(response_data, status=status_code)
        
        except Exception as e:
            if 'tmp_path' in locals():
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            return Response({"error": f"Erro ao processar arquivo: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)