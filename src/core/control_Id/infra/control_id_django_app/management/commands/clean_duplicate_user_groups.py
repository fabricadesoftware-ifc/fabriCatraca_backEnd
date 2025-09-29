from django.core.management.base import BaseCommand
from django.db import transaction
from src.core.control_Id.infra.control_id_django_app.models import UserGroup
from collections import defaultdict


class Command(BaseCommand):
    help = 'Remove relações duplicadas de UserGroup mantendo apenas uma instância de cada combinação user-group'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas mostra o que seria removido sem executar a remoção',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostra detalhes de cada relação sendo processada',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('Iniciando analise de duplicatas de UserGroup...')
        )
        
        # Encontra todas as relações
        all_relations = UserGroup.objects.all().select_related('user', 'group')
        total_relations = all_relations.count()
        
        self.stdout.write(f"Total de relacoes encontradas: {total_relations}")
        
        if total_relations == 0:
            self.stdout.write(self.style.WARNING('Nenhuma relacao encontrada.'))
            return
        
        # Agrupa por (user, group) para encontrar duplicatas
        relations_by_key = defaultdict(list)
        for relation in all_relations:
            key = (relation.user_id, relation.group_id)
            relations_by_key[key].append(relation)
        
        # Identifica duplicatas
        duplicates = {}
        unique_relations = 0
        
        for key, relations in relations_by_key.items():
            if len(relations) > 1:
                duplicates[key] = relations
            else:
                unique_relations += 1
        
        duplicate_count = sum(len(relations) - 1 for relations in duplicates.values())
        
        self.stdout.write(f"Relacoes unicas: {unique_relations}")
        self.stdout.write(f"Relacoes duplicadas: {duplicate_count}")
        self.stdout.write(f"Grupos com duplicatas: {len(duplicates)}")
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('Nenhuma duplicata encontrada!'))
            return
        
        # Mostra detalhes das duplicatas
        if verbose:
            self.stdout.write("\nDetalhes das duplicatas:")
            for (user_id, group_id), relations in duplicates.items():
                user = relations[0].user
                group = relations[0].group
                self.stdout.write(f"  Usuario: {user.name} (ID: {user_id}) -> Grupo: {group.name} (ID: {group_id})")
                self.stdout.write(f"     {len(relations)} instancias encontradas")
                for i, relation in enumerate(relations):
                    self.stdout.write(f"       - ID: {relation.id} {'(MANTER)' if i == 0 else '(REMOVER)'}")
                self.stdout.write("")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: {duplicate_count} relacoes seriam removidas')
            )
            self.stdout.write("Execute sem --dry-run para remover as duplicatas.")
            return
        
        # Confirma a remoção
        self.stdout.write(f"\nATENCAO: {duplicate_count} relacoes duplicadas serao removidas!")
        confirm = input("Deseja continuar? (sim/nao): ").lower().strip()
        
        if confirm not in ['sim', 's', 'yes', 'y']:
            self.stdout.write(self.style.WARNING('Operacao cancelada.'))
            return
        
        # Remove duplicatas mantendo apenas a primeira de cada grupo
        removed_count = 0
        
        with transaction.atomic():
            for (user_id, group_id), relations in duplicates.items():
                # Mantém a primeira relação (menor ID)
                relations.sort(key=lambda x: x.id)
                to_keep = relations[0]
                to_remove = relations[1:]
                
                if verbose:
                    user = to_keep.user
                    group = to_keep.group
                    self.stdout.write(f"Removendo {len(to_remove)} duplicatas de {user.name} -> {group.name}")
                
                # Remove as duplicatas
                for relation in to_remove:
                    relation.delete()
                    removed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Limpeza concluida! {removed_count} relacoes duplicadas removidas.')
        )
        
        # Verifica resultado final
        final_count = UserGroup.objects.count()
        self.stdout.write(f"Relacoes restantes: {final_count}")
        self.stdout.write(f"Relacoes removidas: {total_relations - final_count}")
