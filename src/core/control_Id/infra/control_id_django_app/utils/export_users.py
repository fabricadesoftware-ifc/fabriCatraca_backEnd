from core.user.infra.user_django_app.models import User
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
import re

class ExportUsersView(GenericAPIView):
    """
    View to export users to an Excel file.
    """
    def get(self, request, *args, **kwargs):
        try:
            users = User.objects.all().values('id', 'name', 'email', 'is_active', 'created_at', 'updated_at')
            df = pd.DataFrame(users)
            
            # Formatar colunas de data
            df['created_at'] = df['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df['updated_at'] = df['updated_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Nome do arquivo com timestamp
            filename = f"users_export_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Salvar em um arquivo Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Users')
                
                # Ajustar largura das colunas
                for column in df:
                    column_width = max(df[column].astype(str).map(len).max(), len(column))
                    col_idx = df.columns.get_loc(column) + 1
                    writer.sheets['Users'].column_dimensions[chr(64 + col_idx)].width = column_width + 2
            
            # Ler o arquivo e retornar como resposta
            with open(filename, 'rb') as f:
                response = Response(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)