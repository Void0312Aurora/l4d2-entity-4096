#!/usr/bin/env python3
"""Summarize the bounded D62 E/F experiments from recorded memory and traces.

This checks observations, not script exit status. Missing evidence is an error.
E's later malformed capacity experiment is deliberately outside the interval.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--native', action='store_true', help='also verify completed G and cold-start repeats')
    ap.add_argument('--d63-root', type=Path,
                    help='also evaluate additive D63 evidence without changing D62 assertions')
    a = ap.parse_args()
    sources = {}

    def read(name):
        raw = (a.root/name).read_bytes()
        sources[name] = hashlib.sha256(raw).hexdigest()
        return raw.decode().replace('\r\n', '\n')

    def load(name):
        return json.loads(read(name))

    indices = [2048, 2049, 2095, 2096, 4095]
    clients = {name: load(f'client-fixed/E-{name}.json') for name in
               ['low', 'created4095', 'updated', 'disconnected', 'reconnected',
                'reconnect-updated', 'deleted']}
    cutoff = clients['deleted']['time']
    trace = [json.loads(line) for line in read('server-E/entity-trace.jsonl').splitlines()]
    trace = [row for row in trace if row['time'] <= cutoff]
    snapshots = {}
    for p in sorted((a.root/'server-E').glob('*.json')):
        if p.name == 'session.json':
            continue
        d = load(f'server-E/{p.name}')
        if d['time'] <= cutoff:
            snapshots[f'server-E/{p.name}'] = d
    native = {name: load(f'server-F/{name}.json') for name in ['created', 'deleted', 'reused']}
    snapshots.update({f'server-F/{n}.json': d for n, d in native.items()})
    adds = [r for r in trace if r['event'] == 'add_enter']
    added = [r for r in trace if r['event'] == 'add_done']
    removed = [r for r in trace if r['event'] == 'remove_done']
    sky_returns = [r for r in trace if r['event'] == 'sky_return']
    assertions = {}

    def check(name, checks, evidence):
        checks = list(checks)
        assertions[name] = dict(status='PASS' if checks and all(checks) else 'FAIL',
                                observations=len(checks), evidence=evidence)

    for key in ['NETWORK_SLOT_IN_RANGE', 'NON_NETWORK_SLOT_IN_RANGE',
                'HANDLE_ROUNDTRIP_OK', 'FREELIST_INTEGRITY_OK', 'SKYCAMERA_HANDLE_VALID']:
        check(key, [d['assertions'][key] for d in snapshots.values()], 'server memory snapshots')
    check('NO_SLOT_OVERWRITE', [r['NO_SLOT_OVERWRITE'] for r in adds], 'AddEntityAtSlot entry')
    check('ADD_HANDLE_ROUNDTRIP_OK', [r['HANDLE_ROUNDTRIP_OK'] for r in added], 'AddEntityAtSlot completion')
    check('SERIAL_CONSISTENT', [r['SERIAL_CONSISTENT'] for r in removed], 'RemoveEntityAtSlot completion')
    check('REMOVE_CONFIRMED', [r['REMOVE_CONFIRMED'] for r in removed], 'RemoveEntityAtSlot completion')
    check('OLD_HANDLE_INVALID', [r['OLD_HANDLE_INVALID'] for r in removed], 'removed slot pointer and serial')
    check('RELOCATIONS_OK', [d['relocations']['passed'] for d in snapshots.values() if 'relocations' in d],
          'all 587 relocated live words per external snapshot')
    check('ADD_POOLS_IN_RANGE', [r['pool'] in ('network', 'nonnetwork') and
          (0 <= r['index'] <= 4095 if r['pool'] == 'network' else 4097 <= r['index'] <= 8191)
          for r in adds], 'actual AddNetworkableEntity/AddNonNetworkableEntity return PCs')

    frames = {n: {r['index']: r for r in d['slots']} for n, d in clients.items()}
    low = frames['low']
    check('LOW_INDEX_REGRESSION_OK', [int(low[i]['pointer'], 16) != 0 and klass in low[i]['rtti']
          for i, klass in [(0, 'C_World'), (1, 'C_TerrorPlayer')]], 'client E-low actual RTTI')
    lifecycle = []
    for i in indices:
        c, u, r, v, d = [frames[n][i] for n in
                        ['created4095', 'updated', 'reconnected', 'reconnect-updated', 'deleted']]
        server = next(x for x in added if x['index'] == i)
        lifecycle += [all(int(x['pointer'], 16) and 'C_DynamicProp' in x['rtti'] for x in [c, u, r, v]),
                      c['serial'] == u['serial'] == r['serial'] == v['serial'] == (server['serial'] & 1023),
                      [b-a for a, b in zip(c['origin'], u['origin'])] == [0, 96, 32],
                      r['origin'] == u['origin'],
                      [b-a for a, b in zip(r['origin'], v['origin'])] == [0, 96, 32],
                      int(d['pointer'], 16) == 0 and d['serial'] == ((c['serial']+1) & 32767),
                      any(x['index'] == i and x['REMOVE_CONFIRMED'] for x in removed)]
    check('HIGH_INDEX_LIFECYCLE_OK', lifecycle, 'E client create/update/reconnect/update/delete plus server Remove')
    reused = []
    for i in indices:
        before, empty, after = [native[n]['slots'][i] for n in ['created', 'deleted', 'reused']]
        reused += [before['pointer'] != 0, empty['pointer'] == 0,
                   empty['serial'] == ((before['serial']+1) & 32767),
                   after['pointer'] != 0, after['serial'] == empty['serial'],
                   before['serial'] != after['serial']]
    native_log = read('server-F/pty.log')
    reused += [len(re.findall(r'^D62_REUSED_OLD_VALID=false$', native_log, re.M)) == len(indices)]
    check('NETWORK_REUSE_OK', reused, 'native F created/deleted/reused memory plus old VScript validity')
    nonnet_adds = [r for r in added if r['index'] == 4416]
    nonnet_removes = [r for r in removed if r['index'] == 4416]
    check('NONNETWORK_REUSE_OK', [len(nonnet_adds) == 2, len(nonnet_removes) == 2,
          [r['serial'] for r in nonnet_adds] == [24258, 24259],
          all(r['REMOVE_CONFIRMED'] and r['SERIAL_CONSISTENT'] for r in nonnet_removes)],
          'actual logic_relay slot 4416: add/remove/add/remove')
    initial = snapshots['server-E/initial.json']
    disconnected = snapshots['server-E/after-disconnect.json']
    sky = initial['sky'][0]
    same_sky = all((d['sky'][0]['pointer'], d['sky'][0]['serial'], d['sky'][0]['handle']) ==
                   (sky['pointer'], sky['serial'], sky['handle'])
                   for name, d in snapshots.items() if name.startswith('server-E/'))
    server_log = read('server-E/pty.log')
    disconnect_checks = [same_sky, all(r['pointer'] == sky['pointer'] and r['handle'] == sky['handle']
                                    for r in sky_returns),
                         any(r['time'] > clients['disconnected']['time'] for r in sky_returns),
                         'Dropped Void0312 from server (Disconnect by user.)' in server_log]
    for i in indices:
        old = next(r for r in added if r['index'] == i)
        disconnect_checks += [int(frames['disconnected'][i]['pointer'], 16) == 0,
                              disconnected['slots'][i]['pointer'] == old['pointer'],
                              disconnected['slots'][i]['serial'] == old['serial']]
    check('DISCONNECT_SAFE', disconnect_checks, 'E client emptied/server retained targets; actual sky getter returns')
    check('RECONNECT_ACTIVE', [bool(re.search(r'#\s+7\s+1 "Void0312".* active ', server_log)),
                              assertions['HIGH_INDEX_LIFECYCLE_OK']['status'] == 'PASS'],
          'server userid 7 active plus existing target resync and subsequent update/delete')
    for key in ['SERIAL_WRAP_32767_TO_0', 'INVALID_SENTINEL_CONSUMERS',
                'ALL_8184_HANDLE_SITES', 'MULTICLIENT_CONCURRENT', 'LONG_SOAK']:
        assertions[key] = dict(status='NOT_TESTED', observations=0)
    native_result = None
    if a.native:
        gserver = {n: load(f'server-G/{n}.json') for n in
                   ['low-initial', 'high', 'before-disconnect', 'after-disconnect', 'after-delete']}
        gclient = {n: load(f'client-native-final/{n}.json') for n in
                   ['low', 'created-4095', 'updated', 'disconnected', 'reconnected',
                    'reconnect-updated', 'deleted']}
        gframes = {n: {r['index']: r for r in d['slots']} for n, d in gclient.items()}
        gchecks, disconnect_checks = [], []
        for i in indices:
            c, u, r, v, d = [gframes[n][i] for n in
                            ['created-4095', 'updated', 'reconnected', 'reconnect-updated', 'deleted']]
            gchecks += [all(int(x['pointer'], 16) and 'C_DynamicProp' in x['rtti'] for x in [c, u, r, v]),
                        c['serial'] == u['serial'] == r['serial'] == v['serial'],
                        c['serial'] == (gserver['high']['slots'][i]['serial'] & 1023),
                        [b-a for a, b in zip(c['origin'], u['origin'])] == [0, 96, 32],
                        r['origin'] == u['origin'],
                        [b-a for a, b in zip(r['origin'], v['origin'])] == [0, 96, 32],
                        int(d['pointer'], 16) == 0 and d['serial'] == ((c['serial']+1) & 32767),
                        gserver['after-delete']['slots'][i]['pointer'] == 0,
                        gserver['after-delete']['slots'][i]['serial'] ==
                        ((gserver['high']['slots'][i]['serial']+1) & 32767)]
            disconnect_checks += [int(gframes['disconnected'][i]['pointer'], 16) == 0,
                                  gserver['after-disconnect']['slots'][i]['pointer'] ==
                                  gserver['high']['slots'][i]['pointer']]
        sky_keys = ['pointer', 'serial', 'handle']
        disconnect_checks += [all(d['assertions'].values()) and
                              all(d['sky'][0][k] == gserver['high']['sky'][0][k] for k in sky_keys)
                              for d in gserver.values()]
        check('NATIVE_HIGH_INDEX_LIFECYCLE_OK', gchecks, 'G full client frames and server memory; normal watchdog')
        check('NATIVE_DISCONNECT_SAFE', disconnect_checks, 'G client clear/server targets and sky retained')
        check('NATIVE_RELOCATIONS_OK', [d['relocations']['passed'] for d in gserver.values()],
              'G: all 587 relocated words per snapshot')
        glog = read('server-G/pty.log')
        check('NATIVE_RECONNECT_ACTIVE',
              [bool(re.search(r'D62_FREE_BATCH requested=\d+ remaining=0.*?Dropped Void0312'
                              r'.*?"Void0312"[^\n]* active ', glog, re.S)),
               assertions['NATIVE_HIGH_INDEX_LIFECYCLE_OK']['status'] == 'PASS'],
              'G status after reconnect plus resync/update/delete')
        repeat = [load(f'{n}/run.json') for n in ['client-cache-control', 'client-native-final']]
        first_low = load('client-cache-control/low-stable-final.json')
        check('CLIENT_COLD_START_REPEAT', [d['launcher_final_returncode'] == 0 and
              d['ended']-d['started'] >= 120 and
              {x['event'] for x in d['events']} >= {'game_created', 'game_exited', 'module_loaded'}
              and {x.get('module') for x in d['events'] if x['event'] == 'module_loaded'} >=
              {'bin/engine.dll', 'left4dead2/bin/client.dll'}
              for d in repeat] + [all(int(r['pointer'], 16) for r in gframes['low'].values()),
              {r.get('rtti') for r in first_low['slots']} == {'.?AVC_World@@', '.?AVC_TerrorPlayer@@'},
              all(int(r['pointer'], 16) for r in first_low['slots']),
              bool(re.search(r'"Void0312".* active ', read('client-cache-control/server-status.txt')))],
              'two fresh game PIDs, actual loaded modules, low objects, active, >=120s, deliberate quit rc=0')
        infected = load('server-G/infected-event-reporter.json')
        check('INFECTED_KILLED_LOOKUP_OK',
              [len(infected) == 2, infected[0]['index'] >= 2048,
               'PlayerReporter::FireGameEvent' in infected[0]['stack'],
               'Infected::Event_Killed' in infected[0]['stack'], infected[1]['pointer'] != 0,
               'D62_INFECTED_DAMAGE_RETURNED' in glog], 'G index 4031 death-event lookup entry/actual return')
        native_result = dict(server_session=load('server-G/session.json'), client_runs=repeat,
                             client_frames=gclient, first_low=first_low, infected_event=infected,
                             cache_recovery=load('workshop-cache-recovery.json'),
                             ugc_failure=dict(run=load('client-oom-trace/run.json'),
                                 fault_excerpt=read('client-oom-trace/oom-stack.log').split('process 509509')[0]),
                             listener_control=load('listener-guard.json'),
                             wrong_source_control=load('wrong-source-rejected.json'))
        snapshots.update({f'server-G/{n}.json': d for n, d in gserver.items()})

    d63_result = None
    if a.d63_root:
        droot = a.d63_root
        d63_sources = {}

        def d63_read(name):
            raw = (droot/name).read_bytes()
            d63_sources[name] = hashlib.sha256(raw).hexdigest()
            return raw.decode(errors='replace').replace('\r\n', '\n')

        def d63_load(name):
            return json.loads(d63_read(name))

        def d63_assert(name, checks, evidence, note=None, check_names=None):
            checks = list(checks)
            d63_status[name] = dict(status='PASS' if checks and all(checks) else 'FAIL',
                                     observations=len(checks), evidence=evidence)
            if note:
                d63_status[name]['note'] = note
            if check_names:
                d63_status[name]['checks'] = dict(zip(check_names, checks))

        d63_assertions = [
            'MULTICLIENT_CONCURRENT', 'MULTICLIENT_HIGH_INDEX_SYNC', 'MULTICLIENT_RECONNECT',
            'REAL_GAMEPLAY_HIGH_INDEX', 'CONCURRENT_ENTITY_STRESS', 'WIRE_SERIAL_WRAP',
            'INTERNAL_SERIAL_WRAP', 'INVALID_HANDLE_BOUNDARIES', 'HIGH_RISK_HANDLE_AUDIT',
            'MAP_TRANSITION', 'LONG_SOAK']
        d63_status = {}
        # A two-client attempt was deferred by the user. Keep every C1 result
        # explicitly untested; never count bots or a single client as C1.
        for key in ['MULTICLIENT_CONCURRENT', 'MULTICLIENT_HIGH_INDEX_SYNC',
                    'MULTICLIENT_RECONNECT', 'WIRE_SERIAL_WRAP', 'INTERNAL_SERIAL_WRAP',
                    'MAP_TRANSITION', 'LONG_SOAK']:
            d63_status[key] = dict(status='NOT_TESTED', observations=0,
                                   evidence='deferred or no qualifying dynamic evidence')

        # Keep the ordinary-infected control separate from the Hunter run.
        # The Hunter session also spawned an ordinary infected first, but that
        # same-session marker alone is not an independent control.
        failure = d63_load('server-crash.json')
        hunter_stack = d63_read('c2-hunter-gdb/crash.gdb.txt')
        hunter_log = d63_read('c2-hunter-gdb/pty.log')
        infected_log = d63_read('infected-only-isolated/pty.log')
        infected_status = d63_read('infected-only-isolated/status-after-spawn.txt')
        infected_session = d63_load('infected-only-isolated/session.json')
        infected_observation = d63_load('infected-only-isolated/observation.json')
        hunter_checks = [failure.get('first_error') == 'NUM_FOR_EDICT: bad pointer',
                         'CVEngineServer::SetFakeClientConVarValue' in hunter_stack,
                         'BossZombiePlayerBot::Spawn' in hunter_stack,
                         'D63_HUNTER_ONLY_FILLERS=' in hunter_log,
                         'D63_HUNTER_ONLY_CREATED' not in hunter_log]
        infected_checks = [
            'D63_INFECTED_ONLY_CREATED idx=2048 valid=true' in infected_log,
            'NUM_FOR_EDICT: bad pointer' not in infected_log,
            infected_session.get('port') == 27072 and infected_session.get('mode') == 'low-index-control',
            'hostname: L4D2-4096-lab' in infected_status and 'map     : c1m1_hotel' in infected_status,
            'players : 0 humans, 0 bots' in infected_status,
            infected_observation.get('spawn_marker') is True,
            infected_observation.get('status_response_has_lab_hostname') is True,
            infected_observation.get('process_alive_after_controlled_stop') is False]
        real_gameplay_checks = hunter_checks + infected_checks
        d63_status['REAL_GAMEPLAY_HIGH_INDEX'] = dict(
            status='FAIL' if real_gameplay_checks and all(real_gameplay_checks) else 'NOT_TESTED',
            observations=len(real_gameplay_checks),
            evidence='c2-hunter-gdb logs plus infected-only-isolated control logs and status response',
            checks=dict(zip(['hunter_first_error', 'hunter_engine_stack', 'hunter_bot_spawn_stack',
                             'hunter_fillers_reached', 'hunter_not_created', 'infected_control_created_at_2048',
                             'infected_control_no_bad_pointer', 'control_isolated_session',
                             'control_server_status_after_spawn', 'control_status_empty_players',
                             'control_observation_spawn_marker', 'control_observation_status',
                             'control_server_stopped_intentionally'], real_gameplay_checks)),
            note='Separate ordinary-infected control created index 2048 and answered status after spawn. In the Hunter run, an ordinary-infected marker also preceded the Hunter attempt in the same session; Hunter then failed at NUM_FOR_EDICT/SetFakeClientConVarValue. This bounds the failure to the observed Hunter path and does not establish a general edict-mapping root cause.')

        # The invalid-index API exercise is based on EntIndexToHScript, with
        # D62 client evidence retained for a real index-4095 live object.
        boundary_logs = [d63_read('stress-connected-1793017646/pty.log'),
                         d63_read('server-public/pty.log')]
        boundary_rows = {}
        for log in boundary_logs:
            for row in re.findall(r'^D63_BOUNDARY idx=(-?\d+) valid=(true|false) class=([^\r\n]+)$',
                                  log, re.M):
                boundary_rows.setdefault(int(row[0]), []).append((row[1] == 'true', row[2]))
        boundary_checks = [
            any(ok and cls == 'player' for ok, cls in boundary_rows.get(1, [])),
            any(ok and cls == 'prop_dynamic' for ok, cls in boundary_rows.get(2048, [])),
            all(any(not ok and cls == 'NULL' for ok, cls in boundary_rows.get(i, []))
                for i in [0, 4096, 4097, 8191, -1]),
            all('D63_BOUNDARY_DONE' in log for log in boundary_logs)]
        d63_assert('INVALID_HANDLE_BOUNDARIES', boundary_checks,
                   'VScript EntIndexToHScript calls at 0, 1, 2048, 4096, 4097, 8191, -1; D62 index-4095 client lifecycle',
                   'Tests index lookup behavior; it does not synthesize arbitrary stale CBaseHandle values.',
                   ['valid_player', 'valid_high_entity', 'invalid_empty_and_out_of_range', 'all_scripts_completed'])

        # Static coverage only. No candidate is credited with execution solely
        # because its containing function name suggests a runtime path.
        audit = d63_load('handle-audit.json')
        audit_assertions = audit.get('assertions', {})
        review_names = sorted(p.name for p in (droot/'handle-review').glob('*.c'))
        audit_checks = [audit.get('candidate_count') == 8184,
                        audit.get('reviewed_instruction_count') == 8184,
                        audit.get('dynamic_execution_count') == 0,
                        audit.get('boundary_tested_count') == 0,
                        all(audit_assertions.get(k) is True for k in
                            ['ALL_8184_HANDLE_SITES_CLASSIFIED', 'STATIC_BYTES_AND_CANDIDATE_TAGS_PRESENT',
                             'UNKNOWN_RETAINED', 'NO_UNVERIFIED_DYNAMIC_CLAIMS']),
                        len(review_names) >= 5]
        d63_assert('HIGH_RISK_HANDLE_AUDIT', audit_checks,
                   'handle-audit.json plus six reviewed pseudocode extracts',
                   'PASS means complete static classification and selected function review; dynamic execution remains 0/8184.')

        stress_dir = 'stress-connected-1793017646/'
        stress_log = d63_read(stress_dir+'pty.log')
        sbefore = d63_load(stress_dir+'server-before.json')
        safter = d63_load(stress_dir+'server-after.json')
        cbefore = d63_load(stress_dir+'client-before.json')
        cafter = d63_load(stress_dir+'client-after.json')
        move_before = d63_load('client-move-before.json')
        move_after = d63_load('client-move-after.json')
        update_times = d63_load(stress_dir+'update-times.json')
        metrics = d63_load(stress_dir+'metrics.json')
        pcap = d63_load(stress_dir+'pcap-summary.json')
        stress_session = d63_load(stress_dir+'session.json')
        movement_run = d63_load('client-stress-movement/run.json')
        movement_modules = movement_run.get('modules', {})
        build_identity_ok = (
            stress_session.get('engine_sha256') == '79b3966bd9752394beb2f29f0cf0244acedddde15112b4c037535994ecaf8014'
            and movement_modules.get('left4dead2.exe') == 'c1007187e05ed681173b1c44c043980edf72dfcb2183ad90ec8e6d874d1b14e3'
            and movement_modules.get('bin/engine.dll') == '48329969eaaedee94d011957d81cf53b5a06d8c8098a5e548a7e741309994bd9'
            and movement_modules.get('left4dead2/bin/client.dll') == '3e5c3f2ee98c2bfa3f3672c654f7ae8b3ae401cc437a08ae1abbe57a6d363943')
        targets = [(int(i), int(idx)) for i, idx in
                   re.findall(r'^D63_STRESS_TARGET i=(\d+) idx=(\d+)$', stress_log, re.M)]
        expected_indices = list(range(2048, 2064))
        sb = {x['index']: x for x in sbefore['occupied']}
        sa = {x['index']: x for x in safter['occupied']}
        cb = {x['index']: x for x in cbefore['slots']}
        ca = {x['index']: x for x in cafter['slots']}
        player_active = bool(re.search(r'^#\s+\d+\s+1 "Void0312".* active ', stress_log, re.M))
        move_before_slots = {x['index']: x for x in move_before['slots']}
        move_after_slots = {x['index']: x for x in move_after['slots']}
        move_status = stress_log.rsplit('status\n', 1)[-1].split('script ::d63_stress_step()', 1)[0]
        move_active = bool(re.search(r'^#\s+\d+\s+1 "Void0312".* active ', move_status, re.M))
        movement_visible = all(
            i in move_before_slots and i in move_after_slots
            and int(move_before_slots[i]['pointer'], 16) != 0
            and int(move_after_slots[i]['pointer'], 16) != 0
            and move_before_slots[i]['serial'] == move_after_slots[i]['serial']
            and move_before_slots[i].get('rtti') == move_after_slots[i].get('rtti')
            and move_before_slots[i]['rtti'].endswith('C_DynamicProp@@')
            and abs(move_after_slots[i]['origin'][0] - move_before_slots[i]['origin'][0]) < 0.01
            and abs(move_after_slots[i]['origin'][1] - move_before_slots[i]['origin'][1]) < 0.01
            and abs(move_after_slots[i]['origin'][2] - move_before_slots[i]['origin'][2] - 32) < 0.01
            for i in expected_indices)
        stress_checks = [targets == list(enumerate(expected_indices)),
                         'D63_STRESS_BEGIN count=16 rate=1' in stress_log,
                         len(re.findall(r'^D63_STRESS_HEARTBEAT count=16 rate=1 updates=', stress_log, re.M)) >= 3,
                         player_active,
                         build_identity_ok,
                         all(i in sb and i in sa and i in cb and i in ca for i in expected_indices),
                         all('DynamicProp' in sb[i]['rtti'] and 'DynamicProp' in sa[i]['rtti']
                             and int(cb[i]['pointer'],16) != 0 and int(ca[i]['pointer'],16) != 0
                             and 'C_DynamicProp' in cb[i]['rtti'] and 'C_DynamicProp' in ca[i]['rtti']
                             for i in expected_indices),
                         all((sb[i]['serial'] & 1023) == cb[i]['serial'] == ca[i]['serial']
                             and sa[i]['serial'] == sb[i]['serial'] for i in expected_indices),
                         all(d['assertions'].get(k) is True for d in [sbefore, safter]
                             for k in ['FREELIST_INTEGRITY_OK', 'HANDLE_ROUNDTRIP_OK',
                                       'SKYCAMERA_HANDLE_VALID', 'NETWORK_SLOT_IN_RANGE',
                                       'NON_NETWORK_SLOT_IN_RANGE']),
                         update_times.get('updates') == 30
                         and 28.0 <= update_times.get('elapsed_seconds',0) <= 31.0
                         and all(0.95 <= y-x <= 1.05 for x,y in zip(update_times['timestamps'],
                                                                   update_times['timestamps'][1:])),
                         len(metrics.get('samples',[])) >= 30,
                         pcap.get('server_out',{}).get('packets',0) > 0
                         and pcap.get('server_in',{}).get('packets',0) > 0,
                         move_before.get('pid') == move_after.get('pid')
                         and move_before.get('client_sha256') == move_after.get('client_sha256')
                         and list(move_before_slots) == expected_indices
                         and list(move_after_slots) == expected_indices
                         and move_active and movement_visible]
        d63_assert('CONCURRENT_ENTITY_STRESS', stress_checks,
                   '16 live high-index C_DynamicProp slots on server/client, 30 1Hz updates, one additional server movement observed at all 16 client slots, pcap and process metrics',
                   'One real client; demonstrated 16 only. The additional movement observation was one 32-unit update, not a multiplayer or capacity limit test.',
                   ['target_indices', 'script_begin', 'heartbeat_count', 'client_active', 'build_identities',
                    'slot_presence', 'rtti_and_nonnull', 'serial_consistency', 'server_invariants', 'update_schedule',
                    'metrics_samples', 'bidirectional_udp', 'client_movement_visible'])

        for key in d63_assertions:
            d63_status.setdefault(key, dict(status='NOT_TESTED', observations=0))
        d63_result = dict(evidence_root=str(droot.resolve()), assertions={k: d63_status[k]
                          for k in d63_assertions},
                          stress=dict(target_indices=expected_indices,
                                      updates=update_times['updates'],
                                      elapsed_seconds=update_times['elapsed_seconds'],
                                      server_rss_kib=[metrics['samples'][0]['rss_kib'],
                                                      metrics['samples'][-1]['rss_kib']],
                                      client_movement=dict(
                                          indices=expected_indices,
                                          delta_origin=[0, 0, 32],
                                          client_pid=move_before['pid'],
                                          before_time=move_before['time'],
                                          after_time=move_after['time']),
                                      pcap=pcap),
                          handle_audit=dict(candidate_count=audit['candidate_count'],
                                            categories=audit['categories'],
                                            dynamic_execution_count=audit['dynamic_execution_count'],
                                            reviewed_functions=review_names),
                          boundary=dict(observed_indices=sorted(boundary_rows)),
                          failure=dict(phase=failure.get('phase'), first_error=failure.get('first_error'),
                                       stack_functions=['CVEngineServer::SetFakeClientConVarValue',
                                                        'BossZombiePlayerBot::Spawn']),
                          source_sha256=d63_sources)
    compact = {}
    for name, d in snapshots.items():
        compact[name] = {k: d[k] for k in ['time', 'entity_list', 'sky', 'assertions']}
        compact[name].update(occupied=len(d['occupied']), free_nonnetwork=len(d['nonnetwork_free']['indices']),
                             active_head_tail=[d['active'][k] for k in ['head', 'tail']],
                             free_nonnetwork_head_tail=[d['nonnetwork_free'][k] for k in ['head', 'tail']],
                             reserved=d['slots'][4096],
                             selected_slots=[d['slots'][i] for i in indices+[4416]])
        if 'relocations' in d:
            compact[name]['relocations'] = d['relocations']
    result = dict(raw_root=str(a.root.resolve()), E_interval_end=cutoff,
                  interval_reason='ends at E-deleted.json, before the malformed reuse driver',
                  identities=load('binary-identities.json'),
                  sessions={n: load(f'{n}/session.json') for n in ['server-E', 'server-F']},
                  assertions=assertions, trace_counts=dict(Counter(r['event'] for r in trace)),
                  target_events=[r for r in trace if r['event'] in ('add_done', 'remove_done')
                                 and r['index'] in indices+[4416]],
                  snapshots=compact, client_frames=clients, native=native_result, source_sha256=sources)
    if d63_result is not None:
        result['d63'] = d63_result
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(assertions, indent=2))
    failed = any(r['status'] == 'FAIL' for r in assertions.values())
    if d63_result is not None:
        failed = failed or any(r['status'] == 'FAIL'
                               for r in d63_result['assertions'].values())
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
