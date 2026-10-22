
/home/void0312/l4d2_server/bin/engine_srv.so:     file format elf32-i386


Disassembly of section .text:

001ede70 <CGameServer::SpawnServer(char*, char*)>:
  1ede70:	55                   	push   ebp
  1ede71:	89 e5                	mov    ebp,esp
  1ede73:	57                   	push   edi
  1ede74:	56                   	push   esi
  1ede75:	53                   	push   ebx
  1ede76:	81 ec bc 02 00 00    	sub    esp,0x2bc
  1ede7c:	8b 45 0c             	mov    eax,DWORD PTR [ebp+0xc]
  1ede7f:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1ede82:	8b 75 10             	mov    esi,DWORD PTR [ebp+0x10]
  1ede85:	89 85 64 fd ff ff    	mov    DWORD PTR [ebp-0x29c],eax
  1ede8b:	65 a1 14 00 00 00    	mov    eax,gs:0x14
  1ede91:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
  1ede94:	31 c0                	xor    eax,eax
  1ede96:	e8 fc ff ff ff       	call   1ede97 <CGameServer::SpawnServer(char*, char*)+0x27>
  1ede9b:	8b 10                	mov    edx,DWORD PTR [eax]
  1ede9d:	c7 44 24 04 48 30 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3048
  1edea5:	89 04 24             	mov    DWORD PTR [esp],eax
  1edea8:	ff 52 28             	call   DWORD PTR [edx+0x28]
  1edeab:	85 c0                	test   eax,eax
  1edead:	74 0d                	je     1edebc <CGameServer::SpawnServer(char*, char*)+0x4c>
  1edeaf:	80 bb 60 02 00 00 00 	cmp    BYTE PTR [ebx+0x260],0x0
  1edeb6:	0f 84 b4 0a 00 00    	je     1ee970 <CGameServer::SpawnServer(char*, char*)+0xb00>
  1edebc:	8b 03                	mov    eax,DWORD PTR [ebx]
  1edebe:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1edec1:	ff 50 60             	call   DWORD PTR [eax+0x60]
  1edec4:	84 c0                	test   al,al
  1edec6:	0f 85 84 0a 00 00    	jne    1ee950 <CGameServer::SpawnServer(char*, char*)+0xae0>
  1edecc:	8b bd 64 fd ff ff    	mov    edi,DWORD PTR [ebp-0x29c]
  1eded2:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1eded5:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1eded9:	e8 72 f7 ff ff       	call   1ed650 <CGameServer::ReloadWhitelist(char const*)>
  1edede:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1edee2:	c7 04 24 b6 31 2b 00 	mov    DWORD PTR [esp],0x2b31b6
  1edee9:	e8 fc ff ff ff       	call   1edeea <CGameServer::SpawnServer(char*, char*)+0x7a>
  1edeee:	89 3c 24             	mov    DWORD PTR [esp],edi
  1edef1:	e8 2a 8f f2 ff       	call   116e20 <COM_SetupLogDir(char const*)>
  1edef6:	c7 04 24 e0 6b 3a 00 	mov    DWORD PTR [esp],0x3a6be0
  1edefd:	e8 de c8 ff ff       	call   1ea7e0 <CLog::Open()>
  1edf02:	89 7c 24 08          	mov    DWORD PTR [esp+0x8],edi
  1edf06:	c7 44 24 04 c9 31 2b 00 	mov    DWORD PTR [esp+0x4],0x2b31c9
  1edf0e:	c7 04 24 e0 6b 3a 00 	mov    DWORD PTR [esp],0x3a6be0
  1edf15:	e8 a6 c2 ff ff       	call   1ea1c0 <CLog::Printf(char const*, ...)>
  1edf1a:	c7 04 24 e0 6b 3a 00 	mov    DWORD PTR [esp],0x3a6be0
  1edf21:	e8 fa c2 ff ff       	call   1ea220 <CLog::PrintServerVars()>
  1edf26:	85 f6                	test   esi,esi
  1edf28:	0f 84 62 0a 00 00    	je     1ee990 <CGameServer::SpawnServer(char*, char*)+0xb20>
  1edf2e:	89 74 24 08          	mov    DWORD PTR [esp+0x8],esi
  1edf32:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1edf36:	c7 04 24 db 31 2b 00 	mov    DWORD PTR [esp],0x2b31db
  1edf3d:	e8 fc ff ff ff       	call   1edf3e <CGameServer::SpawnServer(char*, char*)+0xce>
  1edf42:	8b 83 08 01 00 00    	mov    eax,DWORD PTR [ebx+0x108]
  1edf48:	83 c0 01             	add    eax,0x1
  1edf4b:	a3 28 29 39 00       	mov    ds:0x392928,eax
  1edf50:	89 83 08 01 00 00    	mov    DWORD PTR [ebx+0x108],eax
  1edf56:	8b 03                	mov    eax,DWORD PTR [ebx]
  1edf58:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1edf5b:	ff 50 68             	call   DWORD PTR [eax+0x68]
  1edf5e:	c7 04 24 a0 10 39 00 	mov    DWORD PTR [esp],0x3910a0
  1edf65:	0f b6 c0             	movzx  eax,al
  1edf68:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
  1edf6c:	e8 4f 91 04 00       	call   2370c0 <ConVar::SetValue(int)>
  1edf71:	a1 5c 10 39 00       	mov    eax,ds:0x39105c
  1edf76:	8b 48 30             	mov    ecx,DWORD PTR [eax+0x30]
  1edf79:	85 c9                	test   ecx,ecx
  1edf7b:	0f 85 af 09 00 00    	jne    1ee930 <CGameServer::SpawnServer(char*, char*)+0xac0>
  1edf81:	8b 15 28 58 3d 00    	mov    edx,DWORD PTR ds:0x3d5828
  1edf87:	31 c0                	xor    eax,eax
  1edf89:	c7 04 24 e0 12 39 00 	mov    DWORD PTR [esp],0x3912e0
  1edf90:	85 d2                	test   edx,edx
  1edf92:	ba 03 00 00 00       	mov    edx,0x3
  1edf97:	0f 49 05 28 58 3d 00 	cmovns eax,DWORD PTR ds:0x3d5828
  1edf9e:	83 f8 03             	cmp    eax,0x3
  1edfa1:	0f 4f c2             	cmovg  eax,edx
  1edfa4:	f3 0f 2a c0          	cvtsi2ss xmm0,eax
  1edfa8:	a3 28 58 3d 00       	mov    ds:0x3d5828,eax
  1edfad:	f3 0f 11 44 24 04    	movss  DWORD PTR [esp+0x4],xmm0
  1edfb3:	e8 d8 90 04 00       	call   237090 <ConVar::SetValue(float)>
  1edfb8:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1edfbe:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1edfc1:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
  1edfc5:	e8 a6 f9 ff ff       	call   1ed970 <CGameServer::ExecGameTypeCfg(char const*)>
  1edfca:	c7 04 24 4c 23 2b 00 	mov    DWORD PTR [esp],0x2b234c
  1edfd1:	e8 fc ff ff ff       	call   1edfd2 <CGameServer::SpawnServer(char*, char*)+0x162>
  1edfd6:	e8 d5 7b fe ff       	call   1d5bb0 <StaticPropMgr()>
  1edfdb:	8b 10                	mov    edx,DWORD PTR [eax]
  1edfdd:	89 04 24             	mov    DWORD PTR [esp],eax
  1edfe0:	ff 52 14             	call   DWORD PTR [edx+0x14]
  1edfe3:	a1 a8 0a 39 00       	mov    eax,ds:0x390aa8
  1edfe8:	85 c0                	test   eax,eax
  1edfea:	74 10                	je     1edffc <CGameServer::SpawnServer(char*, char*)+0x18c>
  1edfec:	8b 10                	mov    edx,DWORD PTR [eax]
  1edfee:	89 04 24             	mov    DWORD PTR [esp],eax
  1edff1:	ff 52 54             	call   DWORD PTR [edx+0x54]
  1edff4:	84 c0                	test   al,al
  1edff6:	0f 84 b4 08 00 00    	je     1ee8b0 <CGameServer::SpawnServer(char*, char*)+0xa40>
  1edffc:	c7 04 24 05 32 2b 00 	mov    DWORD PTR [esp],0x2b3205
  1ee003:	e8 fc ff ff ff       	call   1ee004 <CGameServer::SpawnServer(char*, char*)+0x194>
  1ee008:	c7 04 24 01 00 00 00 	mov    DWORD PTR [esp],0x1
  1ee00f:	e8 cc b4 f7 ff       	call   1694e0 <Host_FreeStateAndWorld(bool)>
  1ee014:	c7 04 24 01 00 00 00 	mov    DWORD PTR [esp],0x1
  1ee01b:	e8 60 b5 f7 ff       	call   169580 <Host_FreeToLowMark(bool)>
  1ee020:	c7 04 24 18 32 2b 00 	mov    DWORD PTR [esp],0x2b3218
  1ee027:	c7 05 40 7f 3a 00 00 00 00 00 	mov    DWORD PTR ds:0x3a7f40,0x0
  1ee031:	e8 fc ff ff ff       	call   1ee032 <CGameServer::SpawnServer(char*, char*)+0x1c2>
  1ee036:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee038:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee03b:	ff 90 a8 00 00 00    	call   DWORD PTR [eax+0xa8]
  1ee041:	c7 04 24 70 23 2b 00 	mov    DWORD PTR [esp],0x2b2370
  1ee048:	e8 fc ff ff ff       	call   1ee049 <CGameServer::SpawnServer(char*, char*)+0x1d9>
  1ee04d:	a1 f4 17 33 00       	mov    eax,ds:0x3317f4
  1ee052:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee054:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee057:	ff 52 08             	call   DWORD PTR [edx+0x8]
  1ee05a:	8b 8d 64 fd ff ff    	mov    ecx,DWORD PTR [ebp-0x29c]
  1ee060:	8d 43 10             	lea    eax,[ebx+0x10]
  1ee063:	c7 44 24 08 40 00 00 00 	mov    DWORD PTR [esp+0x8],0x40
  1ee06b:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee06e:	89 85 5c fd ff ff    	mov    DWORD PTR [ebp-0x2a4],eax
  1ee074:	89 4c 24 04          	mov    DWORD PTR [esp+0x4],ecx
  1ee078:	e8 b3 f4 05 00       	call   24d530 <V_strncpy(char*, char const*, int)>
  1ee07d:	85 f6                	test   esi,esi
  1ee07f:	0f 84 5b 08 00 00    	je     1ee8e0 <CGameServer::SpawnServer(char*, char*)+0xa70>
  1ee085:	8d 83 c9 01 00 00    	lea    eax,[ebx+0x1c9]
  1ee08b:	c7 44 24 08 40 00 00 00 	mov    DWORD PTR [esp+0x8],0x40
  1ee093:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee097:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee09a:	e8 91 f4 05 00       	call   24d530 <V_strncpy(char*, char const*, int)>
  1ee09f:	e8 2c dd ff ff       	call   1ebdd0 <SV_FlushMemoryIfMarked()>
  1ee0a4:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1ee0a9:	bf 10 00 00 00       	mov    edi,0x10
  1ee0ae:	31 f6                	xor    esi,esi
  1ee0b0:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee0b2:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee0b5:	ff 92 24 01 00 00    	call   DWORD PTR [edx+0x124]
  1ee0bb:	a1 84 97 3f 00       	mov    eax,ds:0x3f9784
  1ee0c0:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee0c2:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee0c5:	c7 44 24 04 00 00 00 00 	mov    DWORD PTR [esp+0x4],0x0
  1ee0cd:	ff 92 94 00 00 00    	call   DWORD PTR [edx+0x94]
  1ee0d3:	c7 05 50 7f 3a 00 00 08 00 00 	mov    DWORD PTR ds:0x3a7f50,0x800
  1ee0dd:	c7 83 10 02 00 00 00 08 00 00 	mov    DWORD PTR [ebx+0x210],0x800
  1ee0e7:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee0e9:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee0ec:	ff 50 18             	call   DWORD PTR [eax+0x18]
  1ee0ef:	a3 14 7f 3a 00       	mov    ds:0x3a7f14,eax
  1ee0f4:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee0f6:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee0f9:	ff 50 18             	call   DWORD PTR [eax+0x18]
  1ee0fc:	83 c0 01             	add    eax,0x1
  1ee0ff:	89 83 0c 02 00 00    	mov    DWORD PTR [ebx+0x20c],eax
  1ee105:	c7 04 24 23 32 2b 00 	mov    DWORD PTR [esp],0x2b3223
  1ee10c:	e8 fc ff ff ff       	call   1ee10d <CGameServer::SpawnServer(char*, char*)+0x29d>
  1ee111:	a1 70 81 3a 00       	mov    eax,ds:0x3a8170
  1ee116:	c7 44 24 08 01 00 00 00 	mov    DWORD PTR [esp+0x8],0x1
  1ee11e:	c7 44 24 04 ae db 2a 00 	mov    DWORD PTR [esp+0x4],0x2adbae
  1ee126:	c1 e0 04             	shl    eax,0x4
  1ee129:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee12c:	e8 7f 23 04 00       	call   2304b0 <Hunk_AllocName(int, char const*, bool)>
  1ee131:	a3 74 81 3a 00       	mov    ds:0x3a8174,eax
  1ee136:	e8 e5 86 fd ff       	call   1c6820 <ED_ClearTimes()>
  1ee13b:	a1 70 81 3a 00       	mov    eax,ds:0x3a8170
  1ee140:	c7 44 24 08 01 00 00 00 	mov    DWORD PTR [esp+0x8],0x1
  1ee148:	c7 44 24 04 35 32 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3235
  1ee150:	c1 e0 02             	shl    eax,0x2
  1ee153:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee156:	e8 55 23 04 00       	call   2304b0 <Hunk_AllocName(int, char const*, bool)>
  1ee15b:	c6 83 24 02 00 00 01 	mov    BYTE PTR [ebx+0x224],0x1
  1ee162:	a3 78 81 3a 00       	mov    ds:0x3a8178,eax
  1ee167:	c7 83 f8 00 00 00 00 00 00 00 	mov    DWORD PTR [ebx+0xf8],0x0
  1ee171:	8b 83 14 02 00 00    	mov    eax,DWORD PTR [ebx+0x214]
  1ee177:	c7 83 fc 00 00 00 00 00 00 00 	mov    DWORD PTR [ebx+0xfc],0x0
  1ee181:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee184:	a3 58 7f 3a 00       	mov    ds:0x3a7f58,eax
  1ee189:	e8 12 7b 00 00       	call   1f5ca0 <CGameServer::AssignClassIds()>
  1ee18e:	c7 04 24 45 32 2b 00 	mov    DWORD PTR [esp],0x2b3245
  1ee195:	e8 fc ff ff ff       	call   1ee196 <CGameServer::SpawnServer(char*, char*)+0x326>
  1ee19a:	eb 29                	jmp    1ee1c5 <CGameServer::SpawnServer(char*, char*)+0x355>
  1ee19c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1ee1a0:	8b 83 14 01 00 00    	mov    eax,DWORD PTR [ebx+0x114]
  1ee1a6:	8b 14 b0             	mov    edx,DWORD PTR [eax+esi*4]
  1ee1a9:	83 c6 01             	add    esi,0x1
  1ee1ac:	8b 83 14 02 00 00    	mov    eax,DWORD PTR [ebx+0x214]
  1ee1b2:	01 f8                	add    eax,edi
  1ee1b4:	83 c7 10             	add    edi,0x10
  1ee1b7:	89 82 50 d7 01 00    	mov    DWORD PTR [edx+0x1d750],eax
  1ee1bd:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee1c0:	e8 8b 86 fd ff       	call   1c6850 <InitializeEntityDLLFields(edict_t*)>
  1ee1c5:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee1c7:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee1ca:	ff 50 20             	call   DWORD PTR [eax+0x20]
  1ee1cd:	39 c6                	cmp    esi,eax
  1ee1cf:	7c cf                	jl     1ee1a0 <CGameServer::SpawnServer(char*, char*)+0x330>
  1ee1d1:	c7 04 24 54 32 2b 00 	mov    DWORD PTR [esp],0x2b3254
  1ee1d8:	e8 fc ff ff ff       	call   1ee1d9 <CGameServer::SpawnServer(char*, char*)+0x369>
  1ee1dd:	c7 43 04 01 00 00 00 	mov    DWORD PTR [ebx+0x4],0x1
  1ee1e4:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1ee1eb:	e8 f0 a5 f0 ff       	call   f87e0 <CBaseServer::SendReservationStatus()>
  1ee1f0:	f3 0f 10 05 30 17 39 00 	movss  xmm0,DWORD PTR ds:0x391730
  1ee1f8:	f3 0f 11 83 0c 01 00 00 	movss  DWORD PTR [ebx+0x10c],xmm0
  1ee200:	0f 14 c0             	unpcklps xmm0,xmm0
  1ee203:	0f 5a c8             	cvtps2pd xmm1,xmm0
  1ee206:	f2 0f 10 05 90 28 29 00 	movsd  xmm0,QWORD PTR ds:0x292890
  1ee20e:	f2 0f 5e c1          	divsd  xmm0,xmm1
  1ee212:	f2 0f 2c c0          	cvttsd2si eax,xmm0
  1ee216:	83 c0 01             	add    eax,0x1
  1ee219:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
  1ee21c:	e8 fc ff ff ff       	call   1ee21d <CGameServer::SpawnServer(char*, char*)+0x3ad>
  1ee221:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee223:	c7 44 24 08 00 00 80 bf 	mov    DWORD PTR [esp+0x8],0xbf800000
  1ee22b:	c7 44 24 04 69 32 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3269
  1ee233:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee236:	ff 52 20             	call   DWORD PTR [edx+0x20]
  1ee239:	d9 9d 60 fd ff ff    	fstp   DWORD PTR [ebp-0x2a0]
  1ee23f:	f3 0f 10 85 60 fd ff ff 	movss  xmm0,DWORD PTR [ebp-0x2a0]
  1ee247:	0f 2f 05 7c 28 29 00 	comiss xmm0,DWORD PTR ds:0x29287c
  1ee24e:	0f 85 ac 05 00 00    	jne    1ee800 <CGameServer::SpawnServer(char*, char*)+0x990>
  1ee254:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
  1ee257:	a3 18 7f 3a 00       	mov    ds:0x3a7f18,eax
  1ee25c:	8d b5 dc fd ff ff    	lea    esi,[ebp-0x224]
  1ee262:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee264:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee267:	8d bd e0 fe ff ff    	lea    edi,[ebp-0x120]
  1ee26d:	ff 50 28             	call   DWORD PTR [eax+0x28]
  1ee270:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1ee276:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee279:	d9 9d 60 fd ff ff    	fstp   DWORD PTR [ebp-0x2a0]
  1ee27f:	f3 0f 10 85 60 fd ff ff 	movss  xmm0,DWORD PTR [ebp-0x2a0]
  1ee287:	c7 44 24 08 c0 6e 29 00 	mov    DWORD PTR [esp+0x8],0x296ec0
  1ee28f:	c7 44 24 04 04 01 00 00 	mov    DWORD PTR [esp+0x4],0x104
  1ee297:	89 44 24 0c          	mov    DWORD PTR [esp+0xc],eax
  1ee29b:	f3 0f 11 05 0c 7f 3a 00 	movss  DWORD PTR ds:0x3a7f0c,xmm0
  1ee2a3:	e8 c8 f3 05 00       	call   24d670 <V_snprintf(char*, int, char const*, ...)>
  1ee2a8:	c7 44 24 08 04 01 00 00 	mov    DWORD PTR [esp+0x8],0x104
  1ee2b0:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee2b4:	89 3c 24             	mov    DWORD PTR [esp],edi
  1ee2b7:	e8 a4 6e f9 ff       	call   185160 <GetMapPathNameOnDisk(char*, char const*, unsigned int)>
  1ee2bc:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1ee2c1:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee2c3:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee2c6:	c7 44 24 10 00 00 00 00 	mov    DWORD PTR [esp+0x10],0x0
  1ee2ce:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [esp+0xc],0x0
  1ee2d6:	c7 44 24 08 6d 07 29 00 	mov    DWORD PTR [esp+0x8],0x29076d
  1ee2de:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1ee2e2:	ff 52 1c             	call   DWORD PTR [edx+0x1c]
  1ee2e5:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1ee2ea:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee2ec:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee2ef:	ff 92 54 01 00 00    	call   DWORD PTR [edx+0x154]
  1ee2f5:	e8 fc ff ff ff       	call   1ee2f6 <CGameServer::SpawnServer(char*, char*)+0x486>
  1ee2fa:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee2fc:	c7 44 24 04 75 32 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3275
  1ee304:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee307:	ff 52 28             	call   DWORD PTR [edx+0x28]
  1ee30a:	85 c0                	test   eax,eax
  1ee30c:	0f 84 de 05 00 00    	je     1ee8f0 <CGameServer::SpawnServer(char*, char*)+0xa80>
  1ee312:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee316:	c7 04 24 f4 23 2b 00 	mov    DWORD PTR [esp],0x2b23f4
  1ee31d:	e8 fc ff ff ff       	call   1ee31e <CGameServer::SpawnServer(char*, char*)+0x4ae>
  1ee322:	a1 a4 15 33 00       	mov    eax,ds:0x3315a4
  1ee327:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee329:	c7 44 24 08 02 00 00 00 	mov    DWORD PTR [esp+0x8],0x2
  1ee331:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee335:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee338:	ff 52 1c             	call   DWORD PTR [edx+0x1c]
  1ee33b:	c7 04 24 28 17 39 00 	mov    DWORD PTR [esp],0x391728
  1ee342:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
  1ee346:	e8 d5 78 f7 ff       	call   165c20 <CCommonHostState::SetWorldModel(model_t*)>
  1ee34b:	a1 28 17 39 00       	mov    eax,ds:0x391728
  1ee350:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee354:	85 c0                	test   eax,eax
  1ee356:	0f 84 ad 06 00 00    	je     1eea09 <CGameServer::SpawnServer(char*, char*)+0xb99>
  1ee35c:	c7 04 24 20 24 2b 00 	mov    DWORD PTR [esp],0x2b2420
  1ee363:	e8 fc ff ff ff       	call   1ee364 <CGameServer::SpawnServer(char*, char*)+0x4f4>
  1ee368:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee36a:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee36d:	ff 50 68             	call   DWORD PTR [eax+0x68]
  1ee370:	84 c0                	test   al,al
  1ee372:	0f 85 b0 04 00 00    	jne    1ee828 <CGameServer::SpawnServer(char*, char*)+0x9b8>
  1ee378:	c7 83 b0 00 00 00 00 00 00 00 	mov    DWORD PTR [ebx+0xb0],0x0
  1ee382:	c7 83 b4 00 00 00 00 00 00 00 	mov    DWORD PTR [ebx+0xb4],0x0
  1ee38c:	a1 f8 15 33 00       	mov    eax,ds:0x3315f8
  1ee391:	bf 01 00 00 00       	mov    edi,0x1
  1ee396:	89 83 bc 00 00 00    	mov    DWORD PTR [ebx+0xbc],eax
  1ee39c:	c7 04 24 d4 32 2b 00 	mov    DWORD PTR [esp],0x2b32d4
  1ee3a3:	e8 fc ff ff ff       	call   1ee3a4 <CGameServer::SpawnServer(char*, char*)+0x534>
  1ee3a8:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1ee3ae:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee3b1:	e8 fa eb fa ff       	call   19cfb0 <SV_CreateNetworkStringTables(char const*)>
  1ee3b6:	a1 e0 15 33 00       	mov    eax,ds:0x3315e0
  1ee3bb:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee3bd:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee3c0:	ff 52 08             	call   DWORD PTR [edx+0x8]
  1ee3c3:	89 83 b8 00 00 00    	mov    DWORD PTR [ebx+0xb8],eax
  1ee3c9:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [esp+0xc],0x0
  1ee3d1:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee3d9:	c7 44 24 04 d4 79 2b 00 	mov    DWORD PTR [esp+0x4],0x2b79d4
  1ee3e1:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee3e4:	e8 97 bc 00 00       	call   1fa080 <CGameServer::PrecacheModel(char const*, int, model_t*)>
  1ee3e9:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee3f1:	c7 44 24 04 d4 79 2b 00 	mov    DWORD PTR [esp+0x4],0x2b79d4
  1ee3f9:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee3fc:	e8 7f c2 00 00       	call   1fa680 <CGameServer::PrecacheGeneric(char const*, int)>
  1ee401:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee409:	c7 44 24 04 d4 79 2b 00 	mov    DWORD PTR [esp+0x4],0x2b79d4
  1ee411:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee414:	e8 c7 bf 00 00       	call   1fa3e0 <CGameServer::PrecacheSound(char const*, int)>
  1ee419:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee41d:	c7 04 24 f1 32 2b 00 	mov    DWORD PTR [esp],0x2b32f1
  1ee424:	e8 fc ff ff ff       	call   1ee425 <CGameServer::SpawnServer(char*, char*)+0x5b5>
  1ee429:	a1 28 17 39 00       	mov    eax,ds:0x391728
  1ee42e:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee432:	c7 44 24 08 03 00 00 00 	mov    DWORD PTR [esp+0x8],0x3
  1ee43a:	8d b5 77 fd ff ff    	lea    esi,[ebp-0x289]
  1ee440:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee443:	89 44 24 0c          	mov    DWORD PTR [esp+0xc],eax
  1ee447:	e8 34 bc 00 00       	call   1fa080 <CGameServer::PrecacheModel(char const*, int, model_t*)>
  1ee44c:	c7 04 24 0b 33 2b 00 	mov    DWORD PTR [esp],0x2b330b
  1ee453:	e8 fc ff ff ff       	call   1ee454 <CGameServer::SpawnServer(char*, char*)+0x5e4>
  1ee458:	a1 2c 17 39 00       	mov    eax,ds:0x39172c
  1ee45d:	83 38 01             	cmp    DWORD PTR [eax],0x1
  1ee460:	7e 5f                	jle    1ee4c1 <CGameServer::SpawnServer(char*, char*)+0x651>
  1ee462:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1ee468:	89 7c 24 0c          	mov    DWORD PTR [esp+0xc],edi
  1ee46c:	83 c7 01             	add    edi,0x1
  1ee46f:	c7 44 24 08 49 33 2b 00 	mov    DWORD PTR [esp+0x8],0x2b3349
  1ee477:	c7 44 24 04 05 00 00 00 	mov    DWORD PTR [esp+0x4],0x5
  1ee47f:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee482:	e8 e9 f1 05 00       	call   24d670 <V_snprintf(char*, int, char const*, ...)>
  1ee487:	a1 a4 15 33 00       	mov    eax,ds:0x3315a4
  1ee48c:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee48e:	c7 44 24 08 02 00 00 00 	mov    DWORD PTR [esp+0x8],0x2
  1ee496:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee49a:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee49d:	ff 52 1c             	call   DWORD PTR [edx+0x1c]
  1ee4a0:	c7 44 24 08 03 00 00 00 	mov    DWORD PTR [esp+0x8],0x3
  1ee4a8:	89 44 24 0c          	mov    DWORD PTR [esp+0xc],eax
  1ee4ac:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee4b0:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee4b3:	e8 c8 bb 00 00       	call   1fa080 <CGameServer::PrecacheModel(char const*, int, model_t*)>
  1ee4b8:	a1 2c 17 39 00       	mov    eax,ds:0x39172c
  1ee4bd:	39 38                	cmp    DWORD PTR [eax],edi
  1ee4bf:	7f a7                	jg     1ee468 <CGameServer::SpawnServer(char*, char*)+0x5f8>
  1ee4c1:	c7 04 24 21 33 2b 00 	mov    DWORD PTR [esp],0x2b3321
  1ee4c8:	e8 fc ff ff ff       	call   1ee4c9 <CGameServer::SpawnServer(char*, char*)+0x659>
  1ee4cd:	e8 6e 08 04 00       	call   22ed40 <SV_ClearWorld()>
  1ee4d2:	c7 04 24 2f 33 2b 00 	mov    DWORD PTR [esp],0x2b332f
  1ee4d9:	e8 fc ff ff ff       	call   1ee4da <CGameServer::SpawnServer(char*, char*)+0x66a>
  1ee4de:	8b 83 14 02 00 00    	mov    eax,DWORD PTR [ebx+0x214]
  1ee4e4:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee4e7:	e8 64 83 fd ff       	call   1c6850 <InitializeEntityDLLFields(edict_t*)>
  1ee4ec:	8b 83 14 02 00 00    	mov    eax,DWORD PTR [ebx+0x214]
  1ee4f2:	0f 57 c0             	xorps  xmm0,xmm0
  1ee4f5:	83 20 fd             	and    DWORD PTR [eax],0xfffffffd
  1ee4f8:	a1 5c 10 39 00       	mov    eax,ds:0x39105c
  1ee4fd:	0f 2f 40 2c          	comiss xmm0,DWORD PTR [eax+0x2c]
  1ee501:	0f 84 c1 03 00 00    	je     1ee8c8 <CGameServer::SpawnServer(char*, char*)+0xa58>
  1ee507:	8b 48 30             	mov    ecx,DWORD PTR [eax+0x30]
  1ee50a:	85 c9                	test   ecx,ecx
  1ee50c:	0f 95 05 4e 7f 3a 00 	setne  BYTE PTR ds:0x3a7f4e
  1ee513:	8d 93 c9 01 00 00    	lea    edx,[ebx+0x1c9]
  1ee519:	31 c0                	xor    eax,eax
  1ee51b:	80 7b 10 00          	cmp    BYTE PTR [ebx+0x10],0x0
  1ee51f:	0f 45 85 5c fd ff ff 	cmovne eax,DWORD PTR [ebp-0x2a4]
  1ee526:	a3 3c 7f 3a 00       	mov    ds:0x3a7f3c,eax
  1ee52b:	31 c0                	xor    eax,eax
  1ee52d:	80 bb c9 01 00 00 00 	cmp    BYTE PTR [ebx+0x1c9],0x0
  1ee534:	c7 44 24 04 4d 33 2b 00 	mov    DWORD PTR [esp+0x4],0x2b334d
  1ee53c:	c7 04 24 e0 e0 3d 00 	mov    DWORD PTR [esp],0x3de0e0
  1ee543:	0f 45 c2             	cmovne eax,edx
  1ee546:	a3 44 7f 3a 00       	mov    ds:0x3a7f44,eax
  1ee54b:	e8 30 c3 01 00       	call   20a880 <CTestScriptMgr::CheckPoint(char const*)>
  1ee550:	a1 bc 96 3f 00       	mov    eax,ds:0x3f96bc
  1ee555:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee557:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee55a:	ff 52 28             	call   DWORD PTR [edx+0x28]
  1ee55d:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee55f:	c7 44 24 04 00 00 00 00 	mov    DWORD PTR [esp+0x4],0x0
  1ee567:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee56a:	ff 52 04             	call   DWORD PTR [edx+0x4]
  1ee56d:	85 c0                	test   eax,eax
  1ee56f:	89 c7                	mov    edi,eax
  1ee571:	89 85 64 fd ff ff    	mov    DWORD PTR [ebp-0x29c],eax
  1ee577:	0f 84 33 04 00 00    	je     1ee9b0 <CGameServer::SpawnServer(char*, char*)+0xb40>
  1ee57d:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee585:	c7 44 24 04 dc 80 29 00 	mov    DWORD PTR [esp+0x4],0x2980dc
  1ee58d:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee590:	e8 4b f9 04 00       	call   23dee0 <KeyValues::GetInt(char const*, int)>
  1ee595:	85 c0                	test   eax,eax
  1ee597:	c7 44 24 08 d4 79 2b 00 	mov    DWORD PTR [esp+0x8],0x2b79d4
  1ee59f:	0f 95 85 60 fd ff ff 	setne  BYTE PTR [ebp-0x2a0]
  1ee5a6:	c7 44 24 04 e9 80 29 00 	mov    DWORD PTR [esp+0x4],0x2980e9
  1ee5ae:	89 3c 24             	mov    DWORD PTR [esp],edi
  1ee5b1:	e8 3a ff 04 00       	call   23e4f0 <KeyValues::GetString(char const*, char const*)>
  1ee5b6:	c7 44 24 08 d4 79 2b 00 	mov    DWORD PTR [esp+0x8],0x2b79d4
  1ee5be:	c7 44 24 04 f7 80 29 00 	mov    DWORD PTR [esp+0x4],0x2980f7
  1ee5c6:	89 3c 24             	mov    DWORD PTR [esp],edi
  1ee5c9:	89 85 5c fd ff ff    	mov    DWORD PTR [ebp-0x2a4],eax
  1ee5cf:	e8 1c ff 04 00       	call   23e4f0 <KeyValues::GetString(char const*, char const*)>
  1ee5d4:	89 85 58 fd ff ff    	mov    DWORD PTR [ebp-0x2a8],eax
  1ee5da:	a1 70 00 2a 00       	mov    eax,ds:0x2a0070
  1ee5df:	8b 0d 70 00 2a 00    	mov    ecx,DWORD PTR ds:0x2a0070
  1ee5e5:	8b 00                	mov    eax,DWORD PTR [eax]
  1ee5e7:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [esp+0xc],0x0
  1ee5ef:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee5f7:	c7 44 24 04 99 6e 29 00 	mov    DWORD PTR [esp+0x4],0x296e99
  1ee5ff:	89 0c 24             	mov    DWORD PTR [esp],ecx
  1ee602:	ff 50 1c             	call   DWORD PTR [eax+0x1c]
  1ee605:	85 c0                	test   eax,eax
  1ee607:	89 c6                	mov    esi,eax
  1ee609:	0f 84 91 01 00 00    	je     1ee7a0 <CGameServer::SpawnServer(char*, char*)+0x930>
  1ee60f:	8b 00                	mov    eax,DWORD PTR [eax]
  1ee611:	f6 05 75 2a 39 00 10 	test   BYTE PTR ds:0x392a75,0x10
  1ee618:	8b 50 3c             	mov    edx,DWORD PTR [eax+0x3c]
  1ee61b:	b8 ea 5c 29 00       	mov    eax,0x295cea
  1ee620:	75 12                	jne    1ee634 <CGameServer::SpawnServer(char*, char*)+0x7c4>
  1ee622:	a1 7c 2a 39 00       	mov    eax,ds:0x392a7c
  1ee627:	8b 48 24             	mov    ecx,DWORD PTR [eax+0x24]
  1ee62a:	b8 d4 79 2b 00       	mov    eax,0x2b79d4
  1ee62f:	85 c9                	test   ecx,ecx
  1ee631:	0f 45 c1             	cmovne eax,ecx
  1ee634:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee638:	c7 44 24 04 a6 6e 29 00 	mov    DWORD PTR [esp+0x4],0x296ea6
  1ee640:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee643:	ff d2                	call   edx
  1ee645:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee647:	8b 78 3c             	mov    edi,DWORD PTR [eax+0x3c]
  1ee64a:	c7 44 24 04 00 00 00 00 	mov    DWORD PTR [esp+0x4],0x0
  1ee652:	c7 04 24 48 c1 39 00 	mov    DWORD PTR [esp],0x39c148
  1ee659:	e8 e2 6a 05 00       	call   245140 <netadr_s::ToString(bool) const>
  1ee65e:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee662:	c7 44 24 04 0c 51 2b 00 	mov    DWORD PTR [esp+0x4],0x2b510c
  1ee66a:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee66d:	ff d7                	call   edi
  1ee66f:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee671:	8b 78 30             	mov    edi,DWORD PTR [eax+0x30]
  1ee674:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee676:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee679:	ff 50 24             	call   DWORD PTR [eax+0x24]
  1ee67c:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee680:	c7 44 24 04 da c0 2a 00 	mov    DWORD PTR [esp+0x4],0x2ac0da
  1ee688:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee68b:	ff d7                	call   edi
  1ee68d:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee68f:	c7 44 24 08 e0 67 38 00 	mov    DWORD PTR [esp+0x8],0x3867e0
  1ee697:	c7 44 24 04 30 b7 2b 00 	mov    DWORD PTR [esp+0x4],0x2bb730
  1ee69f:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee6a2:	ff 50 3c             	call   DWORD PTR [eax+0x3c]
  1ee6a5:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee6a7:	8b 78 3c             	mov    edi,DWORD PTR [eax+0x3c]
  1ee6aa:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee6ac:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee6af:	ff 50 3c             	call   DWORD PTR [eax+0x3c]
  1ee6b2:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee6b6:	c7 44 24 04 82 31 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3182
  1ee6be:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee6c1:	ff d7                	call   edi
  1ee6c3:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee6c5:	8b 78 30             	mov    edi,DWORD PTR [eax+0x30]
  1ee6c8:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee6ca:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee6cd:	ff 50 18             	call   DWORD PTR [eax+0x18]
  1ee6d0:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee6d4:	c7 44 24 04 10 30 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3010
  1ee6dc:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee6df:	ff d7                	call   edi
  1ee6e1:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee6e3:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee6eb:	c7 44 24 04 70 08 2a 00 	mov    DWORD PTR [esp+0x4],0x2a0870
  1ee6f3:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee6f6:	ff 50 30             	call   DWORD PTR [eax+0x30]
  1ee6f9:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee6fb:	c7 44 24 08 71 33 2b 00 	mov    DWORD PTR [esp+0x8],0x2b3371
  1ee703:	c7 44 24 04 03 d2 2b 00 	mov    DWORD PTR [esp+0x4],0x2bd203
  1ee70b:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee70e:	ff 50 3c             	call   DWORD PTR [eax+0x3c]
  1ee711:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee713:	8b 78 30             	mov    edi,DWORD PTR [eax+0x30]
  1ee716:	8b 03                	mov    eax,DWORD PTR [ebx]
  1ee718:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1ee71b:	ff 50 60             	call   DWORD PTR [eax+0x60]
  1ee71e:	0f b6 c0             	movzx  eax,al
  1ee721:	c7 44 24 04 10 64 2b 00 	mov    DWORD PTR [esp+0x4],0x2b6410
  1ee729:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
  1ee72d:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee730:	ff d7                	call   edi
  1ee732:	0f b6 95 60 fd ff ff 	movzx  edx,BYTE PTR [ebp-0x2a0]
  1ee739:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee73b:	c7 44 24 04 e1 80 29 00 	mov    DWORD PTR [esp+0x4],0x2980e1
  1ee743:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee746:	89 54 24 08          	mov    DWORD PTR [esp+0x8],edx
  1ee74a:	ff 50 2c             	call   DWORD PTR [eax+0x2c]
  1ee74d:	8b 8d 5c fd ff ff    	mov    ecx,DWORD PTR [ebp-0x2a4]
  1ee753:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee755:	c7 44 24 04 af 6e 29 00 	mov    DWORD PTR [esp+0x4],0x296eaf
  1ee75d:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee760:	89 4c 24 08          	mov    DWORD PTR [esp+0x8],ecx
  1ee764:	ff 50 3c             	call   DWORD PTR [eax+0x3c]
  1ee767:	8b 8d 58 fd ff ff    	mov    ecx,DWORD PTR [ebp-0x2a8]
  1ee76d:	8b 06                	mov    eax,DWORD PTR [esi]
  1ee76f:	c7 44 24 04 b7 6e 29 00 	mov    DWORD PTR [esp+0x4],0x296eb7
  1ee777:	89 34 24             	mov    DWORD PTR [esp],esi
  1ee77a:	89 4c 24 08          	mov    DWORD PTR [esp+0x8],ecx
  1ee77e:	ff 50 3c             	call   DWORD PTR [eax+0x3c]
  1ee781:	a1 70 00 2a 00       	mov    eax,ds:0x2a0070
  1ee786:	8b 0d 70 00 2a 00    	mov    ecx,DWORD PTR ds:0x2a0070
  1ee78c:	8b 00                	mov    eax,DWORD PTR [eax]
  1ee78e:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
  1ee796:	89 74 24 04          	mov    DWORD PTR [esp+0x4],esi
  1ee79a:	89 0c 24             	mov    DWORD PTR [esp],ecx
  1ee79d:	ff 50 20             	call   DWORD PTR [eax+0x20]
  1ee7a0:	c7 04 24 56 33 2b 00 	mov    DWORD PTR [esp],0x2b3356
  1ee7a7:	e8 fc ff ff ff       	call   1ee7a8 <CGameServer::SpawnServer(char*, char*)+0x938>
  1ee7ac:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1ee7b1:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee7b3:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee7b6:	ff 92 58 01 00 00    	call   DWORD PTR [edx+0x158]
  1ee7bc:	8b 8d 64 fd ff ff    	mov    ecx,DWORD PTR [ebp-0x29c]
  1ee7c2:	b8 01 00 00 00       	mov    eax,0x1
  1ee7c7:	85 c9                	test   ecx,ecx
  1ee7c9:	74 14                	je     1ee7df <CGameServer::SpawnServer(char*, char*)+0x96f>
  1ee7cb:	89 0c 24             	mov    DWORD PTR [esp],ecx
  1ee7ce:	89 85 64 fd ff ff    	mov    DWORD PTR [ebp-0x29c],eax
  1ee7d4:	e8 67 0b 05 00       	call   23f340 <KeyValues::deleteThis()>
  1ee7d9:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1ee7df:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
  1ee7e2:	65 33 0d 14 00 00 00 	xor    ecx,DWORD PTR gs:0x14
  1ee7e9:	0f 85 44 02 00 00    	jne    1eea33 <CGameServer::SpawnServer(char*, char*)+0xbc3>
  1ee7ef:	81 c4 bc 02 00 00    	add    esp,0x2bc
  1ee7f5:	5b                   	pop    ebx
  1ee7f6:	5e                   	pop    esi
  1ee7f7:	5f                   	pop    edi
  1ee7f8:	5d                   	pop    ebp
  1ee7f9:	c3                   	ret
  1ee7fa:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1ee800:	f3 0f 5e 05 30 17 39 00 	divss  xmm0,DWORD PTR ds:0x391730
  1ee808:	f3 0f 2c d0          	cvttss2si edx,xmm0
  1ee80c:	b8 01 00 00 00       	mov    eax,0x1
  1ee811:	8d 4a 01             	lea    ecx,[edx+0x1]
  1ee814:	85 d2                	test   edx,edx
  1ee816:	0f 4f c1             	cmovg  eax,ecx
  1ee819:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
  1ee81c:	e9 36 fa ff ff       	jmp    1ee257 <CGameServer::SpawnServer(char*, char*)+0x3e7>
  1ee821:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
  1ee828:	8d 83 b0 00 00 00    	lea    eax,[ebx+0xb0]
  1ee82e:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee831:	89 85 60 fd ff ff    	mov    DWORD PTR [ebp-0x2a0],eax
  1ee837:	e8 34 6a 04 00       	call   235270 <CRC32_Init(unsigned long*)>
  1ee83c:	8b 85 60 fd ff ff    	mov    eax,DWORD PTR [ebp-0x2a0]
  1ee842:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1ee846:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee849:	e8 32 67 f1 ff       	call   104f80 <CRC_MapFile(unsigned long*, char const*)>
  1ee84e:	84 c0                	test   al,al
  1ee850:	0f 84 7a 01 00 00    	je     1ee9d0 <CGameServer::SpawnServer(char*, char*)+0xb60>
  1ee856:	8d bd 7c fd ff ff    	lea    edi,[ebp-0x284]
  1ee85c:	c7 44 24 08 c5 32 2b 00 	mov    DWORD PTR [esp+0x8],0x2b32c5
  1ee864:	c7 44 24 04 60 00 00 00 	mov    DWORD PTR [esp+0x4],0x60
  1ee86c:	89 3c 24             	mov    DWORD PTR [esp],edi
  1ee86f:	e8 fc ed 05 00       	call   24d670 <V_snprintf(char*, int, char const*, ...)>
  1ee874:	c7 44 24 04 2f 00 00 00 	mov    DWORD PTR [esp+0x4],0x2f
  1ee87c:	89 3c 24             	mov    DWORD PTR [esp],edi
  1ee87f:	e8 4c fe 05 00       	call   24e6d0 <V_FixSlashes(char*, char)>
  1ee884:	8d 83 b4 00 00 00    	lea    eax,[ebx+0xb4]
  1ee88a:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1ee88e:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee891:	e8 2a 65 f1 ff       	call   104dc0 <CRC_File(unsigned long*, char const*)>
  1ee896:	84 c0                	test   al,al
  1ee898:	0f 85 ee fa ff ff    	jne    1ee38c <CGameServer::SpawnServer(char*, char*)+0x51c>
  1ee89e:	c7 83 b4 00 00 00 ff ff ff ff 	mov    DWORD PTR [ebx+0xb4],0xffffffff
  1ee8a8:	e9 df fa ff ff       	jmp    1ee38c <CGameServer::SpawnServer(char*, char*)+0x51c>
  1ee8ad:	8d 76 00             	lea    esi,[esi+0x0]
  1ee8b0:	a1 a8 0a 39 00       	mov    eax,ds:0x390aa8
  1ee8b5:	8b 10                	mov    edx,DWORD PTR [eax]
  1ee8b7:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee8ba:	ff 52 14             	call   DWORD PTR [edx+0x14]
  1ee8bd:	e9 3a f7 ff ff       	jmp    1edffc <CGameServer::SpawnServer(char*, char*)+0x18c>
  1ee8c2:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1ee8c8:	a1 bc 10 39 00       	mov    eax,ds:0x3910bc
  1ee8cd:	8b 50 30             	mov    edx,DWORD PTR [eax+0x30]
  1ee8d0:	85 d2                	test   edx,edx
  1ee8d2:	0f 95 05 4d 7f 3a 00 	setne  BYTE PTR ds:0x3a7f4d
  1ee8d9:	e9 35 fc ff ff       	jmp    1ee513 <CGameServer::SpawnServer(char*, char*)+0x6a3>
  1ee8de:	66 90                	xchg   ax,ax
  1ee8e0:	c6 83 c9 01 00 00 00 	mov    BYTE PTR [ebx+0x1c9],0x0
  1ee8e7:	e9 b3 f7 ff ff       	jmp    1ee09f <CGameServer::SpawnServer(char*, char*)+0x22f>
  1ee8ec:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1ee8f0:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1ee8f5:	8d 50 04             	lea    edx,[eax+0x4]
  1ee8f8:	8b 40 04             	mov    eax,DWORD PTR [eax+0x4]
  1ee8fb:	c7 44 24 08 6d 07 29 00 	mov    DWORD PTR [esp+0x8],0x29076d
  1ee903:	c7 44 24 04 84 32 2b 00 	mov    DWORD PTR [esp+0x4],0x2b3284
  1ee90b:	89 14 24             	mov    DWORD PTR [esp],edx
  1ee90e:	ff 50 28             	call   DWORD PTR [eax+0x28]
  1ee911:	84 c0                	test   al,al
  1ee913:	0f 84 f9 f9 ff ff    	je     1ee312 <CGameServer::SpawnServer(char*, char*)+0x4a2>
  1ee919:	c7 04 24 98 23 2b 00 	mov    DWORD PTR [esp],0x2b2398
  1ee920:	e8 fc ff ff ff       	call   1ee921 <CGameServer::SpawnServer(char*, char*)+0xab1>
  1ee925:	e9 e8 f9 ff ff       	jmp    1ee312 <CGameServer::SpawnServer(char*, char*)+0x4a2>
  1ee92a:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1ee930:	c7 44 24 04 00 00 00 00 	mov    DWORD PTR [esp+0x4],0x0
  1ee938:	c7 04 24 a0 10 39 00 	mov    DWORD PTR [esp],0x3910a0
  1ee93f:	e8 7c 87 04 00       	call   2370c0 <ConVar::SetValue(int)>
  1ee944:	e9 38 f6 ff ff       	jmp    1edf81 <CGameServer::SpawnServer(char*, char*)+0x111>
  1ee949:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
  1ee950:	c7 44 24 04 1e 00 00 00 	mov    DWORD PTR [esp+0x4],0x1e
  1ee958:	c7 04 24 60 de 3d 00 	mov    DWORD PTR [esp],0x3dde60
  1ee95f:	e8 5c 87 04 00       	call   2370c0 <ConVar::SetValue(int)>
  1ee964:	e9 63 f5 ff ff       	jmp    1edecc <CGameServer::SpawnServer(char*, char*)+0x5c>
  1ee969:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
  1ee970:	a1 1c 18 33 00       	mov    eax,ds:0x33181c
  1ee975:	c6 83 60 02 00 00 01 	mov    BYTE PTR [ebx+0x260],0x1
  1ee97c:	89 04 24             	mov    DWORD PTR [esp],eax
  1ee97f:	e8 6c af 00 00       	call   1f98f0 <CServerPlugin::LoadPlugins()>
  1ee984:	e9 33 f5 ff ff       	jmp    1edebc <CGameServer::SpawnServer(char*, char*)+0x4c>
  1ee989:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
  1ee990:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1ee996:	c7 04 24 f3 31 2b 00 	mov    DWORD PTR [esp],0x2b31f3
  1ee99d:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
  1ee9a1:	e8 fc ff ff ff       	call   1ee9a2 <CGameServer::SpawnServer(char*, char*)+0xb32>
  1ee9a6:	e9 97 f5 ff ff       	jmp    1edf42 <CGameServer::SpawnServer(char*, char*)+0xd2>
  1ee9ab:	90                   	nop
  1ee9ac:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1ee9b0:	c7 85 58 fd ff ff d4 79 2b 00 	mov    DWORD PTR [ebp-0x2a8],0x2b79d4
  1ee9ba:	c7 85 5c fd ff ff d4 79 2b 00 	mov    DWORD PTR [ebp-0x2a4],0x2b79d4
  1ee9c4:	c6 85 60 fd ff ff 00 	mov    BYTE PTR [ebp-0x2a0],0x0
  1ee9cb:	e9 0a fc ff ff       	jmp    1ee5da <CGameServer::SpawnServer(char*, char*)+0x76a>
  1ee9d0:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1ee9d4:	c7 04 24 a8 32 2b 00 	mov    DWORD PTR [esp],0x2b32a8
  1ee9db:	89 85 64 fd ff ff    	mov    DWORD PTR [ebp-0x29c],eax
  1ee9e1:	e8 fc ff ff ff       	call   1ee9e2 <CGameServer::SpawnServer(char*, char*)+0xb72>
  1ee9e6:	8b 15 a0 f9 38 00    	mov    edx,DWORD PTR ds:0x38f9a0
  1ee9ec:	c7 43 04 00 00 00 00 	mov    DWORD PTR [ebx+0x4],0x0
  1ee9f3:	8b 0a                	mov    ecx,DWORD PTR [edx]
  1ee9f5:	89 14 24             	mov    DWORD PTR [esp],edx
  1ee9f8:	ff 91 58 01 00 00    	call   DWORD PTR [ecx+0x158]
  1ee9fe:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1eea04:	e9 d6 fd ff ff       	jmp    1ee7df <CGameServer::SpawnServer(char*, char*)+0x96f>
  1eea09:	c7 04 24 8e 32 2b 00 	mov    DWORD PTR [esp],0x2b328e
  1eea10:	e8 fc ff ff ff       	call   1eea11 <CGameServer::SpawnServer(char*, char*)+0xba1>
  1eea15:	a1 a0 f9 38 00       	mov    eax,ds:0x38f9a0
  1eea1a:	c7 43 04 00 00 00 00 	mov    DWORD PTR [ebx+0x4],0x0
  1eea21:	8b 10                	mov    edx,DWORD PTR [eax]
  1eea23:	89 04 24             	mov    DWORD PTR [esp],eax
  1eea26:	ff 92 58 01 00 00    	call   DWORD PTR [edx+0x158]
  1eea2c:	31 c0                	xor    eax,eax
  1eea2e:	e9 ac fd ff ff       	jmp    1ee7df <CGameServer::SpawnServer(char*, char*)+0x96f>
  1eea33:	e8 fc ff ff ff       	call   1eea34 <CGameServer::SpawnServer(char*, char*)+0xbc4>
  1eea38:	89 c3                	mov    ebx,eax
  1eea3a:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1eea40:	89 04 24             	mov    DWORD PTR [esp],eax
  1eea43:	e8 f8 08 05 00       	call   23f340 <KeyValues::deleteThis()>
  1eea48:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1eea4b:	e8 50 f2 09 00       	call   28dca0 <_Unwind_Resume>
  1eea50:	89 c3                	mov    ebx,eax
  1eea52:	8b 85 64 fd ff ff    	mov    eax,DWORD PTR [ebp-0x29c]
  1eea58:	85 c0                	test   eax,eax
  1eea5a:	75 de                	jne    1eea3a <CGameServer::SpawnServer(char*, char*)+0xbca>
  1eea5c:	eb ea                	jmp    1eea48 <CGameServer::SpawnServer(char*, char*)+0xbd8>
  1eea5e:	66 90                	xchg   ax,ax

001eea60 <SV_IsSimulating()>:
  1eea60:	83 3d 64 7f 3a 00 03 	cmp    DWORD PTR ds:0x3a7f64,0x3
  1eea67:	55                   	push   ebp
  1eea68:	89 e5                	mov    ebp,esp
  1eea6a:	5d                   	pop    ebp
  1eea6b:	0f 95 c0             	setne  al
  1eea6e:	c3                   	ret
  1eea6f:	90                   	nop

001eea70 <SV_Think(bool)>:
  1eea70:	55                   	push   ebp
  1eea71:	89 e5                	mov    ebp,esp
  1eea73:	56                   	push   esi
  1eea74:	53                   	push   ebx
  1eea75:	83 ec 70             	sub    esp,0x70
  1eea78:	c7 45 d0 00 00 00 00 	mov    DWORD PTR [ebp-0x30],0x0
  1eea7f:	a1 0c 00 00 00       	mov    eax,ds:0xc
  1eea84:	c7 45 d4 00 00 00 00 	mov    DWORD PTR [ebp-0x2c],0x0
  1eea8b:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1eea8e:	85 c0                	test   eax,eax
  1eea90:	0f 84 ba 02 00 00    	je     1eed50 <SV_Think(bool)+0x2e0>
  1eea96:	8d 55 d0             	lea    edx,[ebp-0x30]
  1eea99:	89 04 24             	mov    DWORD PTR [esp],eax
  1eea9c:	89 54 24 04          	mov    DWORD PTR [esp+0x4],edx
