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
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(assertions, indent=2))
    return int(any(r['status'] == 'FAIL' for r in assertions.values()))


if __name__ == '__main__':
    raise SystemExit(main())
