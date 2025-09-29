from src.core.user.infra.user_django_app.models import User
from src.core.control_Id.infra.control_id_django_app.models import CustomGroup, UserGroup
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from drf_spectacular.utils import extend_schema, OpenApiParameter
import pandas as pd
import tempfile
import os
import io

class ExportUsersView(APIView):
    """
    View to export users to a file (xlsx, csv, txt), filtered by group.
    """
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='group_id',
                description='ID do grupo para exportar usuários. Se não fornecido, exporta todos os grupos.',
                required=False,
                type=int
            ),
            OpenApiParameter(
                name='file_type',
                description='Formato do arquivo de exportação (xlsx, csv, txt). Padrão: xlsx',
                required=False,
                type=str,
                enum=['xlsx', 'csv', 'txt']
            )
        ]
    )
    def get(self, request, *args, **kwargs):
        try:
            group_id = request.query_params.get('group_id')
            file_type = request.query_params.get('file_type', 'xlsx').lower()
            
            # Valida o tipo de arquivo
            if file_type not in ['xlsx', 'csv', 'txt']:
                return Response(
                    {"error": "Formato de arquivo inválido. Use xlsx, csv ou txt."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Se fornecido group_id, filtra por grupo específico
            if group_id:
                try:
                    group = CustomGroup.objects.get(id=group_id)
                    groups = [group]
                except CustomGroup.DoesNotExist:
                    return Response(
                        {"error": f"Grupo com ID {group_id} não encontrado"},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Se não fornecido, pega todos os grupos
                groups = CustomGroup.objects.all()

            # Cria um buffer em memória
            output = io.BytesIO()
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            
            # Define nome do arquivo e content type baseado no formato
            if file_type == 'xlsx':
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                file_extension = 'xlsx'
            elif file_type == 'csv':
                content_type = 'text/csv; charset=utf-8'
                file_extension = 'csv'
            else:  # txt
                content_type = 'text/plain; charset=utf-8'
                file_extension = 'txt'

            # Flag para verificar se há dados
            has_data = False
            all_users_data = []  # Para CSV e TXT

            # Processa os dados
            if file_type == 'xlsx':
                # Cria Excel com múltiplas abas
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    for group in groups:
                        users = User.objects.filter(
                            id__in=UserGroup.objects.filter(group=group).values('user')
                        ).distinct()
                        
                        users_data = [{
                            'ID': user.id,
                            'Nome': user.name,
                            'Matrícula': user.registration or ''
                        } for user in users]
                        
                        if users_data:
                            has_data = True
                            df = pd.DataFrame(users_data)
                            sheet_name = str(group.name)[:31]
                            df.to_excel(writer, index=False, sheet_name=sheet_name)
                            
                            # Ajusta largura das colunas
                            worksheet = writer.sheets[sheet_name]
                            for idx, col in enumerate(df.columns):
                                max_length = max(
                                    df[col].astype(str).apply(lambda x: len(str(x))).max(),
                                    len(str(col))
                                )
                                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
            else:
                # Para CSV e TXT, junta todos os usuários em um único DataFrame
                for group in groups:
                    users = User.objects.filter(
                        id__in=UserGroup.objects.filter(group=group).values('user')
                    ).distinct()
                    
                    for user in users:
                        all_users_data.append({
                            'ID': user.id,
                            'Nome': user.name,
                            'Matrícula': user.registration or '',
                            'Grupo': group.name  # Adiciona coluna de grupo para CSV/TXT
                        })
                
                if all_users_data:
                    has_data = True
                    df = pd.DataFrame(all_users_data)
                    if file_type == 'csv':
                        df.to_csv(output, index=False, encoding='utf-8-sig')  # utf-8-sig para Excel abrir corretamente
                    else:  # txt
                        # Cria o conteúdo do texto formatado
                        text_lines = ["Exportação de Usuários por Grupo", "=" * 50, ""]
                        
                        # Formata o cabeçalho das colunas
                        headers = list(df.columns)
                        col_widths = {col: max(df[col].astype(str).str.len().max(), len(col)) for col in headers}
                        header_line = "  ".join(col.ljust(col_widths[col]) for col in headers)
                        text_lines.append(header_line)
                        text_lines.append("-" * len(header_line))
                        
                        # Formata os dados
                        for _, row in df.iterrows():
                            line = "  ".join(str(row[col]).ljust(col_widths[col]) for col in headers)
                            text_lines.append(line)
                        
                        # Junta tudo com quebras de linha
                        return HttpResponse(
                            "\n".join(text_lines),
                            content_type='text/plain; charset=utf-8'
                        )

            # Se nenhum dado foi encontrado
            if not has_data:
                return Response(
                    {"message": "Nenhum usuário encontrado no(s) grupo(s) especificado(s)"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Prepara o nome do arquivo
            if group_id:
                filename = f"usuarios_{groups[0].name}_{timestamp}.{file_extension}"
            else:
                filename = f"usuarios_por_grupo_{timestamp}.{file_extension}"

            # Para Excel e CSV, prepara o arquivo para download
            if file_type in ['xlsx', 'csv']:
                output.seek(0)
                response = HttpResponse(
                    output.getvalue(),
                    content_type=content_type
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response

        except Exception as e:
            return Response(
                {"error": f"Erro ao exportar usuários: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )