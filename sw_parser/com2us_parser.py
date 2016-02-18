import dpkt
import json
from dateutil.parser import *
import pytz

from bestiary.models import Monster
from herders.models import MonsterPiece, MonsterInstance, RuneInstance

from .com2us_mapping import *
from .smon_decryptor import decrypt_response


def parse_pcap_new(pcap_file):
    pcap = dpkt.pcap.Reader(pcap_file)
    req_src = None
    req_dst = None
    req_sport = None
    req_dport = None
    #gateway_request = None

    for ts, buf in pcap:
        eth = dpkt.ethernet.Ethernet(buf)
        ip = eth.data
        tcp = ip.data

        if len(tcp.data) > 0:
            if tcp.dport == 80:
                try:
                    req = dpkt.http.Request(tcp.data)
                except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
                    continue
                else:
                    if req.method == 'POST' and req.uri == '/api/gateway.php':
                        # Found the data request
                        #gateway_request = (ip.src, ip.dst, tcp.sport, tcp.dport)
                        req_src = ip.src
                        req_dst = ip.dst
                        req_sport = tcp.sport
                        req_dport = tcp.dport

            #if ip.dst == req_src:
                #print 'found IP match'
            if tcp.dport == req_sport:
                print 'found port match'
                try:
                    resp = dpkt.http.Response(tcp.data)
                    print decrypt_response(resp.body)
                except:
                    continue

            #if  == (ip.dst, ip.src, tcp.dport, tcp.sport):
                # Found the response
            #    try:
            #        resp = dpkt.http.Response(tcp.data)
            #    except (dpkt.dpkt.NeedData, dpkt.dpkt.UnpackError):
            #        continue
            #    else:
            #        print decrypt_response(resp.body)


def parse_pcap(pcap_file):
    streams = dict()  # Connections with current buffer
    pcap = dpkt.pcap.Reader(pcap_file)

    for ts, buf in pcap:
        eth = dpkt.ethernet.Ethernet(buf)
        if eth.type != dpkt.ethernet.ETH_TYPE_IP:
            continue
        ip = eth.data
        if not isinstance(ip, dpkt.ip.IP):
            try:
                ip = dpkt.ip.IP(ip)
            except:
                continue
        if ip.p != dpkt.ip.IP_PROTO_TCP:
            continue
        tcp = ip.data

        if not isinstance(tcp, dpkt.tcp.TCP):
            try:
                tcp = dpkt.tcp.TCP(tcp)
            except:
                continue

        tupl = (ip.src, ip.dst, tcp.sport, tcp.dport)
        if tupl in streams:
            streams[tupl] = streams[tupl] + tcp.data
        else:
            streams[tupl] = tcp.data

        if (tcp.flags & dpkt.tcp.TH_FIN) != 0 and \
                (tcp.dport == 80 or tcp.sport == 80) and \
                        len(streams[tupl]) > 0:
            other_tupl = (ip.dst, ip.src, tcp.dport, tcp.sport)
            stream1 = streams[tupl]
            del streams[tupl]
            try:
                stream2 = streams[other_tupl]
                del streams[other_tupl]
            except:
                stream2 = ""
            if tcp.dport == 80:
                requests = stream1
                responses = stream2
            else:
                requests = stream2
                responses = stream1

            while len(requests):
                try:
                    request = dpkt.http.Request(requests)
                except:
                    request = ''
                    requests = ''
                try:
                    response = dpkt.http.Response(responses)
                except:
                    response = ''
                    responses = ''
                requests = requests[len(request):]
                responses = requests[len(responses):]

                if len(request) > 0 and len(response) > 0 and request.method == 'POST' and request.uri == '/api/gateway.php' and response.status == '200':
                    resp_plain = decrypt_response(response.body)
                    resp_json = json.loads(resp_plain)

                    if resp_json.get('command') == 'HubUserLogin' and 'unit_list' in resp_json:
                        return resp_json

        elif (tcp.flags & dpkt.tcp.TH_FIN) != 0:
            del streams[tupl]


def parse_sw_json(data, owner, options):
    errors = []
    parsed_runes = []
    parsed_mons = []
    parsed_inventory = {}
    parsed_monster_pieces = []

    building_list = data['building_list']
    inventory_info = data['inventory_info']
    unit_list = data['unit_list']
    runes_info = data['runes']
    locked_mons = data.get('unit_lock_list')

    # Buildings
    storage_building_id = None
    for building in building_list:
        if building:
            # Find which one is the storage building
            if building.get('building_master_id') == 25:
                storage_building_id = building.get('building_id')
                break

    # Inventory - essences and summoning pieces
    for item in inventory_info:
        # Essence Inventory
        if item['item_master_type'] == inventory_type_map['inventory']:
            essence = inventory_essence_map.get(item['item_master_id'])
            quantity = item.get('item_quantity')

            if essence and quantity:
                parsed_inventory[essence] = quantity
        elif item['item_master_type'] == inventory_type_map['monster_piece']:
            quantity = item.get('item_quantity')
            if quantity > 0:
                try:
                    mon = get_monster_from_id(item['item_master_id'])
                except ValueError as e:
                    errors.append(e.message)
                else:
                    if mon:
                        parsed_monster_pieces.append(MonsterPiece(
                            monster=mon,
                            pieces=quantity,
                            owner=owner,
                            uncommitted=True,
                        ))

    # Extract Rune Inventory (unequpped runes)
    for rune_data in runes_info:
        rune = parse_rune_data(rune_data, owner)
        if rune:
            rune.owner = owner
            rune.assigned_to = None
            parsed_runes.append(rune)
        else:
            errors.append('Unable to parse rune in inventory with this data: ' + str(rune_data))

    # Extract monsters
    for unit_info in unit_list:
        mon, is_new = parse_monster_data(unit_info, owner)

        if mon:
            mon.owner = owner
            mon.in_storage = unit_info.get('building_id') == storage_building_id

            # Set priority levels
            if options['default_priority'] and is_new:
                mon.priority = options['default_priority']

            if mon.monster.archetype == Monster.TYPE_MATERIAL:
                mon.fodder = True
                mon.priority = MonsterInstance.PRIORITY_DONE

            # Set ignore for fusion if requested
            if options['ignore_fusion'] and mon.monster.fusion_food and (locked_mons and mon.com2us_id in locked_mons):
                mon.ignore_for_fusion = True

            # Equipped runes
            equipped_runes = unit_info.get('runes')

            # Check import options to determine if monster should be saved
            level_ignored = mon.stars < options['minimum_stars']
            silver_ignored = options['ignore_silver'] and not mon.monster.can_awaken
            material_ignored = options['ignore_material'] and mon.monster.archetype == Monster.TYPE_MATERIAL
            allow_due_to_runes = options['except_with_runes'] and len(equipped_runes) > 0
            allow_due_to_ld = options['except_light_and_dark'] and mon.monster.element in [Monster.ELEMENT_DARK, Monster.ELEMENT_LIGHT] and mon.monster.archetype != Monster.TYPE_MATERIAL

            if (level_ignored or silver_ignored or material_ignored) and not (allow_due_to_runes or allow_due_to_ld):
                continue

            parsed_mons.append(mon)

            # Sometimes the runes are a dict or a list in the json. Convert to list.
            if isinstance(equipped_runes, dict):
                equipped_runes = equipped_runes.values()

            for rune_data in equipped_runes:
                rune = parse_rune_data(rune_data, owner)
                if rune:
                    rune.owner = owner
                    rune.assigned_to = mon
                    parsed_runes.append(rune)
                else:
                    errors.append('Unable to parse rune assigned to ' + str(mon))
        else:
            errors.append('Unable to parse monster data. Monster type: ' + str(unit_info.get('unit_master_id')) + '. Monster ID: ' + str(unit_info.get('unit_id')))

    import_results = {
        'errors': errors,
        'monsters': parsed_mons,
        'monster_pieces': parsed_monster_pieces,
        'runes': parsed_runes,
        'inventory': parsed_inventory,
    }

    return import_results


def get_monster_from_id(com2us_id):
    try:
        com2us_id = str(com2us_id)
        monster_family = int(com2us_id[:3])
        awakened = com2us_id[3] == '1'
        element = element_map.get(int(com2us_id[-1:]))

        return Monster.objects.get(com2us_id=monster_family, is_awakened=awakened, element=element)
    except (TypeError, ValueError):
        raise ValueError('Unable to parse monster ID ' + str(com2us_id))
    except Monster.DoesNotExist:
        return None


def parse_monster_data(monster_data, owner):
    # Get base monster type
    com2us_id = monster_data.get('unit_id')
    monster_type_id = str(monster_data.get('unit_master_id'))

    mon = MonsterInstance.objects.filter(com2us_id=com2us_id, owner=owner).first()

    if not mon:
        mon = MonsterInstance()
        is_new = True
    else:
        is_new = False

    # Make sure it's saved as a new instance and marked as an import
    mon.pk = None
    mon.uncommitted = True

    mon.com2us_id = com2us_id

    # Base monster
    monster_family = int(monster_type_id[:3])
    awakened = monster_type_id[3] == '1'
    element = element_map.get(int(monster_type_id[-1:]))

    try:
        mon.monster = Monster.objects.get(com2us_id=monster_family, is_awakened=awakened, element=element)
    except Monster.DoesNotExist:
        return None, None

    mon.stars = monster_data.get('class')
    mon.level = monster_data.get('unit_level')

    skills = monster_data.get('skills', [])
    if len(skills) >= 1:
        mon.skill_1_level = skills[0][1]
    if len(skills) >= 2:
        mon.skill_2_level = skills[1][1]
    if len(skills) >= 3:
        mon.skill_3_level = skills[2][1]
    if len(skills) >= 4:
        mon.skill_4_level = skills[3][1]

    try:
        created_date = parse(monster_data.get('create_time') + ' PST', tzinfos={'PST': pytz.timezone('US/Pacific')})
        mon.created = created_date
    except (ValueError, TypeError):
        mon.created = None

    return mon, is_new


def parse_rune_data(rune_data, owner):
    com2us_id = rune_data.get('rune_id')

    rune = RuneInstance.objects.filter(com2us_id=com2us_id, owner=owner).first()

    if not rune:
        rune = RuneInstance()

    # Make sure it's saved as a new instance and marked as an import
    rune.pk = None
    rune.uncommitted = True

    # Basic rune info
    rune.type = rune_set_map.get(rune_data.get('set_id'))

    rune.com2us_id = com2us_id
    rune.value = rune_data.get('sell_value')
    rune.slot = rune_data.get('slot_no')
    rune.stars = rune_data.get('class')
    rune.level = rune_data.get('upgrade_curr')

    # Rune stats
    main_stat = rune_data.get('pri_eff')
    if main_stat:
        rune.main_stat = rune_stat_type_map.get(main_stat[0])
        rune.main_stat_value = main_stat[1]

    innate_stat = rune_data.get('prefix_eff')
    if innate_stat:
        rune.innate_stat = rune_stat_type_map.get(innate_stat[0])
        rune.innate_stat_value = innate_stat[1]

    substats = rune_data.get('sec_eff', [])
    if len(substats) >= 1:
        rune.substat_1 = rune_stat_type_map.get(substats[0][0])
        rune.substat_1_value = substats[0][1]

    if len(substats) >= 2:
        rune.substat_2 = rune_stat_type_map.get(substats[1][0])
        rune.substat_2_value = substats[1][1]

    if len(substats) >= 3:
        rune.substat_3 = rune_stat_type_map.get(substats[2][0])
        rune.substat_3_value = substats[2][1]

    if len(substats) >= 4:
        rune.substat_4 = rune_stat_type_map.get(substats[3][0])
        rune.substat_4_value = substats[3][1]

    return rune