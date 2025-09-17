from core.user.infra.user_django_app.models import User
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import re
import tempfile
from django.core.files.uploadedfile import InMemoryUploadedFile


class ImportUsersView(GenericAPIView):
    """
    View to import users from an Excel file.
    """
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
            
            # Lê o arquivo Excel
            df = pd.read_excel(tmp_path, engine='openpyxl')
            
            required_columns = {'name', 'email', 'is_active'}
            if not required_columns.issubset(df.columns):
                return Response({"error": f"Missing required columns: {required_columns - set(df.columns)}"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Valida e cria/atualiza usuários
            created_count = 0
            updated_count = 0
            for _, row in df.iterrows():
                if pd.isna(row['email']) or pd.isna(row['name']):
                    continue
                
                user, created = User.objects.update_or_create(
                    email=row['email'],
                    defaults={
                        'name': row['name'],
                        'is_active': bool(row['is_active'])
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            
            return Response({
                "success": True,
                "message": f"Import completed. Created: {created_count}, Updated: {updated_count}"
            })
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)