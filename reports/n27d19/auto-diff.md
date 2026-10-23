# N27-D19 differential report

Runs: 4; images: frameonly, pristine

## frameonly

| run | ok | connect | events | engine_base | client_base |
|---|---|---|---|---|---|
| frameonly-2 | True | True | 844 | 0x79e00000 | 0x74630000 |
| frameonly-3 | True | True | 714 | 0x79e00000 | 0x74630000 |

### finalCall target histogram

| target | hits |
|---|---|
| `engine.dll+0x4E510` | 715 |
| `engine.dll+0x53FE0` | 715 |

## pristine

| run | ok | connect | events | engine_base | client_base |
|---|---|---|---|---|---|
| pristine-2 | True | True | 1003 | 0x79e00000 | 0x74630000 |
| pristine-3 | True | True | 731 | 0x79e00000 | 0x74630000 |

### finalCall target histogram

| target | hits |
|---|---|
| `engine.dll+0x4E510` | 628 |
| `engine.dll+0x53FE0` | 628 |
| `engine.dll+0x53EF0` | 136 |
| `engine.dll+0x4EE80` | 57 |
| `engine.dll+0x56E60` | 50 |
| `engine.dll+0x53E40` | 28 |
| `engine.dll+0x26E0` | 9 |
| `engine.dll+0x4E440` | 6 |
| `engine.dll+0x53890` | 3 |
| `engine.dll+0x53900` | 3 |
| `engine.dll+0x53970` | 2 |
| `engine.dll+0x4FFA0` | 2 |
| `engine.dll+0x53B20` | 2 |

## Target set comparison

- `engine.dll+0x26E0`: frameonly=0, pristine=9
- `engine.dll+0x4E440`: frameonly=0, pristine=6
- `engine.dll+0x4E510`: frameonly=715, pristine=628
- `engine.dll+0x4EE80`: frameonly=0, pristine=57
- `engine.dll+0x4FFA0`: frameonly=0, pristine=2
- `engine.dll+0x53890`: frameonly=0, pristine=3
- `engine.dll+0x53900`: frameonly=0, pristine=3
- `engine.dll+0x53970`: frameonly=0, pristine=2
- `engine.dll+0x53B20`: frameonly=0, pristine=2
- `engine.dll+0x53E40`: frameonly=0, pristine=28
- `engine.dll+0x53EF0`: frameonly=0, pristine=136
- `engine.dll+0x53FE0`: frameonly=715, pristine=628
- `engine.dll+0x56E60`: frameonly=0, pristine=50

## E56 target objects (target, vtable, object)

- pristine: target=engine.dll+0x56E60 edx=engine.dll+0x358EEC esi=37800528 hits=50
