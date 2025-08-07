from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.db.utils import OperationalError
from time import sleep

from src.core.control_Id.infra.control_id_django_app.models import Device, Template, Card, TimeZone, TimeSpan, Portal, AccessRule, PortalAccessRule, UserAccessRule, AccessRuleTimeZone, Area, UserGroup, CustomGroup, GroupAccessRule
from src.core.user.infra.user_django_app.models import User

from src.core.__seedwork__.infra import ControlIDSyncMixin

class GlobalSyncMixin(ControlIDSyncMixin):
    """Mixin para sincronização global com as catracas"""
    
    def sync_users(self, device):
        """Sincroniza usuários"""
        users = self.load_objects(
            "users",
            fields=["id", "name", "registration", "user_type_id"],
            order_by=["id"]
        )
        return users

    def sync_time_zones(self, device):
        """Sincroniza zonas de tempo"""
        time_zones = self.load_objects(
            "time_zones",
            fields=["id", "name"],
            order_by=["id"]
        )
        return time_zones

    def sync_time_spans(self, device):
        """Sincroniza intervalos de tempo"""
        time_spans = self.load_objects(
            "time_spans",
            fields=["id", "time_zone_id", "start", "end", "sun", "mon", "tue", "wed", "thu", "fri", "sat", "hol1", "hol2", "hol3"],
            order_by=["id"]
        )
        return time_spans

    def sync_access_rules(self, device):
        """Sincroniza regras de acesso"""
        access_rules = self.load_objects(
            "access_rules",
            fields=["id", "name", "type", "priority"],
            order_by=["id"]
        )
        return access_rules

    def sync_portals(self, device):
        """Sincroniza portais"""
        portals = self.load_objects(
            "portals",
            fields=["id", "name", "area_from_id", "area_to_id"],
            order_by=["id"]
        )
        return portals

    def sync_areas(self, device):
        """Sincroniza áreas"""
        areas = self.load_objects(
            "areas",
            fields=["id", "name"],
            order_by=["id"]
        )
        return areas

    def sync_templates(self, device):
        """Sincroniza templates"""
        templates = self.load_objects(
            "templates",
            fields=["user_id", "template", "finger_type", "finger_position"],
            order_by=["user_id"]
        )
        return templates

    def sync_cards(self, device):
        """Sincroniza cartões"""
        cards = self.load_objects(
            "cards",
            fields=["user_id", "value"],
            order_by=["user_id"]
        )
        return cards

    def sync_user_access_rules(self, device):
        """Sincroniza regras de acesso de usuários"""
        rules = self.load_objects(
            "user_access_rules",
            fields=["user_id", "access_rule_id"],
            order_by=["user_id", "access_rule_id"]
        )
        return rules

    def sync_portal_access_rules(self, device):
        """Sincroniza regras de acesso de portais"""
        rules = self.load_objects(
            "portal_access_rules",
            fields=["portal_id", "access_rule_id"],
            order_by=["portal_id", "access_rule_id"]
        )
        return rules

    def sync_access_rule_time_zones(self, device):
        """Sincroniza zonas de tempo das regras de acesso"""
        rules = self.load_objects(
            "access_rule_time_zones",
            fields=["access_rule_id", "time_zone_id"],
            order_by=["access_rule_id", "time_zone_id"]
        )
        return rules

    def sync_user_groups(self, device):
        """Sincroniza usuários em grupos"""
        user_groups = self.load_objects(
            "user_groups",
            fields=["user_id", "group_id"],
            order_by=["user_id", "group_id"]
        )
        return user_groups
    def sync_groups(self, device):
        """Sincroniza grupos"""
        groups = self.load_objects(
            "groups",
            fields=["id", "name"],
            order_by=["id"]
        )
        return groups
    
    def sync_group_access_rules(self, device):
        """Sincroniza grupos de acesso"""
        group_access_rules = self.load_objects(
            "group_access_rules",
            fields=["group_id", "access_rule_id"],
            order_by=["group_id", "access_rule_id"]
        )
        return group_access_rules

@api_view(['GET'])
def sync_all(request):
    """Sincroniza todos os dados de todas as catracas ativas"""
    sync = GlobalSyncMixin()
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Pega todas as catracas ativas
            devices = Device.objects.filter(is_active=True)
            if not devices:
                return Response({
                    "error": "Nenhuma catraca ativa encontrada"
                }, status=status.HTTP_404_NOT_FOUND)

            # Dicionários para armazenar dados de todas as catracas
            all_users = {}  # Dicionário para usuários
            all_time_zones = {}
            all_time_spans = {}
            all_access_rules = {}
            all_portals = {}
            all_areas = {}
            all_templates = []
            all_cards = []
            all_user_access_rules = []
            all_portal_access_rules = []
            all_access_rule_time_zones = []
            all_user_groups = []
            all_groups = []
            all_group_access_rules = []
            # Coleta dados de todas as catracas
            for device in devices:
                sync.set_device(device)
                
                # Primeiro sincroniza usuários pois outras entidades dependem deles
                for user in sync.sync_users(device):
                    if user['id'] not in all_users:
                        all_users[user['id']] = user
                        all_users[user['id']]['devices'] = []
                    all_users[user['id']]['devices'].append(device)
                
                # Coleta dados de cada tipo
                for tz in sync.sync_time_zones(device):
                    all_time_zones[tz['id']] = tz
                
                for ts in sync.sync_time_spans(device):
                    all_time_spans[ts['id']] = ts
                
                for ar in sync.sync_access_rules(device):
                    all_access_rules[ar['id']] = ar
                
                for a in sync.sync_areas(device):
                    all_areas[a['id']] = a
                
                for p in sync.sync_portals(device):
                    all_portals[p['id']] = p
                
                # Templates e Cards não têm ID na API, usamos user_id + dados como chave
                for t in sync.sync_templates(device):
                    t['devices'] = [device]
                    # Procura se já existe um template igual
                    found = False
                    for existing in all_templates:
                        if (existing['user_id'] == t['user_id'] and 
                            existing['template'] == t['template']):
                            existing['devices'].append(device)
                            found = True
                            break
                    if not found:
                        all_templates.append(t)
                
                for c in sync.sync_cards(device):
                    c['devices'] = [device]
                    # Procura se já existe um cartão igual
                    found = False
                    for existing in all_cards:
                        if (existing['user_id'] == c['user_id'] and 
                            existing['value'] == c['value']):
                            existing['devices'].append(device)
                            found = True
                            break
                    if not found:
                        all_cards.append(c)

                # Regras de acesso não têm ID próprio, são compostas
                all_user_access_rules.extend(sync.sync_user_access_rules(device))
                all_portal_access_rules.extend(sync.sync_portal_access_rules(device))
                all_access_rule_time_zones.extend(sync.sync_access_rule_time_zones(device))
                all_user_groups.extend(sync.sync_user_groups(device))
                all_groups.extend(sync.sync_groups(device))
                all_group_access_rules.extend(sync.sync_group_access_rules(device))
            # Atualiza o banco em uma única transação
            with transaction.atomic():
                # Limpa dados antigos
                TimeZone.objects.all().delete()
                TimeSpan.objects.all().delete()
                AccessRule.objects.all().delete()
                Portal.objects.all().delete()
                Area.objects.all().delete()
                Template.objects.all().delete()
                Card.objects.all().delete()
                UserAccessRule.objects.all().delete()
                PortalAccessRule.objects.all().delete()
                AccessRuleTimeZone.objects.all().delete()
                UserGroup.objects.all().delete()
                CustomGroup.objects.all().delete()
                GroupAccessRule.objects.all().delete()
                # Primeiro cria/atualiza os usuários
                for user_data in all_users.values():
                    devices = user_data.pop('devices')
                    user, created = User.objects.update_or_create(
                        id=user_data['id'],
                        defaults={
                            'name': user_data['name'],
                            'registration': user_data.get('registration'),
                            'user_type_id': user_data.get('user_type_id')
                        }
                    )
                    # Associa o usuário com suas catracas
                    user.devices.set(devices)
                
                # Cria os grupos primeiro
                for group_data in all_groups:
                    CustomGroup.objects.update_or_create(
                        id=group_data['id'],
                        defaults={'name': group_data['name']}
                    )

                # Depois cria as associações de usuários com grupos
                for user_group in all_user_groups:
                    try:
                        user = User.objects.get(id=user_group['user_id'])
                        group = CustomGroup.objects.get(id=user_group['group_id'])
                        UserGroup.objects.create(
                            user=user,
                            group=group
                        )
                    except (User.DoesNotExist, CustomGroup.DoesNotExist):
                        continue  # Pula se o usuário ou grupo não existir
                
                # Cria novos registros
                TimeZone.objects.bulk_create([
                    TimeZone(id=tz['id'], name=tz['name'])
                    for tz in all_time_zones.values()
                ])
                
                TimeSpan.objects.bulk_create([
                    TimeSpan(
                        id=ts['id'],
                        time_zone_id=ts['time_zone_id'],
                        start=ts['start'],
                        end=ts['end'],
                        sun=ts['sun'],
                        mon=ts['mon'],
                        tue=ts['tue'],
                        wed=ts['wed'],
                        thu=ts['thu'],
                        fri=ts['fri'],
                        sat=ts['sat'],
                        hol1=ts['hol1'],
                        hol2=ts['hol2'],
                        hol3=ts['hol3']
                    )
                    for ts in all_time_spans.values()
                ])
                
                AccessRule.objects.bulk_create([
                    AccessRule(
                        id=ar['id'],
                        name=ar['name'],
                        type=ar['type'],
                        priority=ar['priority']
                    )
                    for ar in all_access_rules.values()
                ])
                
                GroupAccessRule.objects.bulk_create([
                    GroupAccessRule(
                        group_id=gar['group_id'],
                        access_rule_id=gar['access_rule_id']
                    )
                    for gar in all_group_access_rules
                ])
                
                Area.objects.bulk_create([
                    Area(id=a['id'], name=a['name'])
                    for a in all_areas.values()
                ])
                
                Portal.objects.bulk_create([
                    Portal(id=p['id'], name=p['name'], area_from_id=Area.objects.get(id=p['area_from_id']), area_to_id=Area.objects.get(id=p['area_to_id']))
                    for p in all_portals.values()
                ])
                
                # Para templates e cards, criamos com auto ID   
                templates = Template.objects.bulk_create([
                    Template(
                        user_id=t['user_id'],  # Aqui usamos _id pois é o nome do campo na tabela
                        template=t['template'],
                        finger_type=t.get('finger_type', 0),
                        finger_position=t.get('finger_position', 0)
                    )
                    for t in all_templates
                    if User.objects.filter(id=t['user_id']).exists()  # Só cria se o usuário existir
                ])
                
                # Associa templates com devices
                for t, t_data in zip(templates, all_templates):
                    if User.objects.filter(id=t_data['user_id']).exists():  # Verifica novamente por segurança
                        t.devices.set(t_data['devices'])
                
                cards = Card.objects.bulk_create([
                    Card(
                        user_id=c['user_id'],  # Aqui usamos _id pois é o nome do campo na tabela
                        value=c['value']
                    )
                    for c in all_cards
                    if User.objects.filter(id=c['user_id']).exists()  # Só cria se o usuário existir
                ])
                
                # Associa cards com devices
                for c, c_data in zip(cards, all_cards):
                    if User.objects.filter(id=c_data['user_id']).exists():  # Verifica novamente por segurança
                        c.devices.set(c_data['devices'])
                
                # Cria regras de acesso compostas
                for rule in all_user_access_rules:
                    try:
                        user = User.objects.get(id=rule['user_id'])
                        access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                        UserAccessRule.objects.create(
                            user_id=user,  # Usa a instância do usuário
                            access_rule_id=access_rule  # Usa a instância da regra
                        )
                    except (User.DoesNotExist, AccessRule.DoesNotExist):
                        continue  # Pula se o usuário ou regra não existir
                
                # Cria regras de acesso de portal
                for rule in all_portal_access_rules:
                    try:
                        portal = Portal.objects.get(id=rule['portal_id'])
                        access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                        PortalAccessRule.objects.create(
                            portal_id=portal,  # Usa a instância do portal
                            access_rule_id=access_rule  # Usa a instância da regra
                        )
                    except (Portal.DoesNotExist, AccessRule.DoesNotExist):
                        continue  # Pula se o portal ou regra não existir
                
                # Cria regras de acesso de timezone
                for rule in all_access_rule_time_zones:
                    try:
                        access_rule = AccessRule.objects.get(id=rule['access_rule_id'])
                        time_zone = TimeZone.objects.get(id=rule['time_zone_id'])
                        AccessRuleTimeZone.objects.create(
                            access_rule_id=access_rule,  # Usa a instância da regra
                            time_zone_id=time_zone  # Usa a instância da timezone
                        )
                    except (AccessRule.DoesNotExist, TimeZone.DoesNotExist):
                        continue  # Pula se a regra ou timezone não existir

            return Response({
                "success": True,
                "message": f"Sincronização global concluída com sucesso",
                "stats": {
                    "users": len(all_users),
                    "time_zones": len(all_time_zones),
                    "time_spans": len(all_time_spans),
                    "access_rules": len(all_access_rules),
                    "areas": len(all_areas),
                    "portals": len(all_portals),
                    "templates": len(all_templates),
                    "cards": len(all_cards),
                    "user_access_rules": len(all_user_access_rules),
                    "portal_access_rules": len(all_portal_access_rules),
                    "access_rule_time_zones": len(all_access_rule_time_zones),
                    "groups": len(all_groups),
                    "user_groups": len(all_user_groups),
                    "group_access_rules": len(all_group_access_rules),
                    "devices": len(devices)
                }
            })
            
        except OperationalError as e:
            if "database is locked" in str(e) and retry_count < max_retries - 1:
                retry_count += 1
                sleep(1)
                continue
            return Response({
                "error": f"Erro de banco de dados: {str(e)}. Tente novamente mais tarde."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                "error": f"Erro ao sincronizar: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        break 