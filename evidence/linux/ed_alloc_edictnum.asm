
/home/void0312/l4d2_server/bin/engine_srv.so:     file format elf32-i386


Disassembly of section .text:

001c6820 <ED_ClearTimes()>:
  1c6820:	55                   	push   ebp
  1c6821:	89 e5                	mov    ebp,esp
  1c6823:	83 ec 18             	sub    esp,0x18
  1c6826:	c7 44 24 08 00 20 00 00 	mov    DWORD PTR [esp+0x8],0x2000
  1c682e:	c7 44 24 04 00 00 00 00 	mov    DWORD PTR [esp+0x4],0x0
  1c6836:	c7 04 24 c0 e4 39 00 	mov    DWORD PTR [esp],0x39e4c0
  1c683d:	e8 6e 5f 08 00       	call   24c7b0 <_V_memset(void*, int, int)>
  1c6842:	c9                   	leave
  1c6843:	c3                   	ret
  1c6844:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1c684a:	8d bf 00 00 00 00    	lea    edi,[edi+0x0]

001c6850 <InitializeEntityDLLFields(edict_t*)>:
  1c6850:	55                   	push   ebp
  1c6851:	89 e5                	mov    ebp,esp
  1c6853:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  1c6856:	5d                   	pop    ebp
  1c6857:	2b 05 74 81 3a 00    	sub    eax,DWORD PTR ds:0x3a8174
  1c685d:	c1 f8 04             	sar    eax,0x4
  1c6860:	c7 04 85 c0 e4 39 00 00 00 00 00 	mov    DWORD PTR [eax*4+0x39e4c0],0x0
  1c686b:	c3                   	ret
  1c686c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]

001c6870 <EDICT_NUM(int)>:
  1c6870:	55                   	push   ebp
  1c6871:	89 e5                	mov    ebp,esp
  1c6873:	53                   	push   ebx
  1c6874:	83 ec 14             	sub    esp,0x14
  1c6877:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c687a:	85 db                	test   ebx,ebx
  1c687c:	78 08                	js     1c6886 <EDICT_NUM(int)+0x16>
  1c687e:	3b 1d 70 81 3a 00    	cmp    ebx,DWORD PTR ds:0x3a8170
  1c6884:	7c 10                	jl     1c6896 <EDICT_NUM(int)+0x26>
  1c6886:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c688a:	c7 04 24 3b db 2a 00 	mov    DWORD PTR [esp],0x2adb3b
  1c6891:	e8 1a e9 03 00       	call   2051b0 <Sys_Error(char const*, ...)>
  1c6896:	89 d8                	mov    eax,ebx
  1c6898:	c1 e0 04             	shl    eax,0x4
  1c689b:	03 05 74 81 3a 00    	add    eax,DWORD PTR ds:0x3a8174
  1c68a1:	83 c4 14             	add    esp,0x14
  1c68a4:	5b                   	pop    ebx
  1c68a5:	5d                   	pop    ebp
  1c68a6:	c3                   	ret
  1c68a7:	89 f6                	mov    esi,esi
  1c68a9:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]

001c68b0 <NUM_FOR_EDICT(edict_t const*)>:
  1c68b0:	55                   	push   ebp
  1c68b1:	89 e5                	mov    ebp,esp
  1c68b3:	53                   	push   ebx
  1c68b4:	83 ec 14             	sub    esp,0x14
  1c68b7:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c68ba:	2b 1d 74 81 3a 00    	sub    ebx,DWORD PTR ds:0x3a8174
  1c68c0:	c1 fb 04             	sar    ebx,0x4
  1c68c3:	85 db                	test   ebx,ebx
  1c68c5:	78 08                	js     1c68cf <NUM_FOR_EDICT(edict_t const*)+0x1f>
  1c68c7:	3b 1d 6c 81 3a 00    	cmp    ebx,DWORD PTR ds:0x3a816c
  1c68cd:	7c 0c                	jl     1c68db <NUM_FOR_EDICT(edict_t const*)+0x2b>
  1c68cf:	c7 04 24 54 db 2a 00 	mov    DWORD PTR [esp],0x2adb54
  1c68d6:	e8 d5 e8 03 00       	call   2051b0 <Sys_Error(char const*, ...)>
  1c68db:	83 c4 14             	add    esp,0x14
  1c68de:	89 d8                	mov    eax,ebx
  1c68e0:	5b                   	pop    ebx
  1c68e1:	5d                   	pop    ebp
  1c68e2:	c3                   	ret
  1c68e3:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1c68e9:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]

001c68f0 <NUM_FOR_EDICTINFO(edict_t const*)>:
  1c68f0:	55                   	push   ebp
  1c68f1:	89 e5                	mov    ebp,esp
  1c68f3:	53                   	push   ebx
  1c68f4:	83 ec 14             	sub    esp,0x14
  1c68f7:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c68fa:	2b 1d 74 81 3a 00    	sub    ebx,DWORD PTR ds:0x3a8174
  1c6900:	c1 fb 04             	sar    ebx,0x4
  1c6903:	85 db                	test   ebx,ebx
  1c6905:	78 08                	js     1c690f <NUM_FOR_EDICTINFO(edict_t const*)+0x1f>
  1c6907:	3b 1d 70 81 3a 00    	cmp    ebx,DWORD PTR ds:0x3a8170
  1c690d:	7c 0c                	jl     1c691b <NUM_FOR_EDICTINFO(edict_t const*)+0x2b>
  1c690f:	c7 04 24 b8 db 2a 00 	mov    DWORD PTR [esp],0x2adbb8
  1c6916:	e8 95 e8 03 00       	call   2051b0 <Sys_Error(char const*, ...)>
  1c691b:	83 c4 14             	add    esp,0x14
  1c691e:	89 d8                	mov    eax,ebx
  1c6920:	5b                   	pop    ebx
  1c6921:	5d                   	pop    ebp
  1c6922:	c3                   	ret
  1c6923:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1c6929:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]

001c6930 <ED_ClearEdict(edict_t*)>:
  1c6930:	55                   	push   ebp
  1c6931:	89 e5                	mov    ebp,esp
  1c6933:	53                   	push   ebx
  1c6934:	83 ec 14             	sub    esp,0x14
  1c6937:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c693a:	81 23 fc fe ff ff    	and    DWORD PTR [ebx],0xfffffefc
  1c6940:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1c6943:	e8 a8 ff ff ff       	call   1c68f0 <NUM_FOR_EDICTINFO(edict_t const*)>
  1c6948:	8b 15 78 81 3a 00    	mov    edx,DWORD PTR ds:0x3a8178
  1c694e:	31 c9                	xor    ecx,ecx
  1c6950:	66 89 4c 82 02       	mov    WORD PTR [edx+eax*4+0x2],cx
  1c6955:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1c6958:	e8 93 ff ff ff       	call   1c68f0 <NUM_FOR_EDICTINFO(edict_t const*)>
  1c695d:	8b 15 78 81 3a 00    	mov    edx,DWORD PTR ds:0x3a8178
  1c6963:	31 c9                	xor    ecx,ecx
  1c6965:	66 89 4c 82 02       	mov    WORD PTR [edx+eax*4+0x2],cx
  1c696a:	a1 78 c3 3d 00       	mov    eax,ds:0x3dc378
  1c696f:	8b 10                	mov    edx,DWORD PTR [eax]
  1c6971:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c6975:	89 04 24             	mov    DWORD PTR [esp],eax
  1c6978:	ff 52 0c             	call   DWORD PTR [edx+0xc]
  1c697b:	89 d8                	mov    eax,ebx
  1c697d:	2b 05 74 81 3a 00    	sub    eax,DWORD PTR ds:0x3a8174
  1c6983:	c1 f8 04             	sar    eax,0x4
  1c6986:	c7 04 85 c0 e4 39 00 00 00 00 00 	mov    DWORD PTR [eax*4+0x39e4c0],0x0
  1c6991:	c7 43 04 ff ff ff ff 	mov    DWORD PTR [ebx+0x4],0xffffffff
  1c6998:	83 c4 14             	add    esp,0x14
  1c699b:	5b                   	pop    ebx
  1c699c:	5d                   	pop    ebp
  1c699d:	c3                   	ret
  1c699e:	66 90                	xchg   ax,ax

001c69a0 <CBaseEdict::GetChangeAccessor()>:
  1c69a0:	55                   	push   ebp
  1c69a1:	89 e5                	mov    ebp,esp
  1c69a3:	83 ec 18             	sub    esp,0x18
  1c69a6:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  1c69a9:	89 04 24             	mov    DWORD PTR [esp],eax
  1c69ac:	e8 3f ff ff ff       	call   1c68f0 <NUM_FOR_EDICTINFO(edict_t const*)>
  1c69b1:	8b 15 78 81 3a 00    	mov    edx,DWORD PTR ds:0x3a8178
  1c69b7:	c9                   	leave
  1c69b8:	8d 04 82             	lea    eax,[edx+eax*4]
  1c69bb:	c3                   	ret
  1c69bc:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]

001c69c0 <CBaseEdict::GetChangeAccessor() const>:
  1c69c0:	55                   	push   ebp
  1c69c1:	89 e5                	mov    ebp,esp
  1c69c3:	83 ec 18             	sub    esp,0x18
  1c69c6:	8b 45 08             	mov    eax,DWORD PTR [ebp+0x8]
  1c69c9:	89 04 24             	mov    DWORD PTR [esp],eax
  1c69cc:	e8 1f ff ff ff       	call   1c68f0 <NUM_FOR_EDICTINFO(edict_t const*)>
  1c69d1:	8b 15 78 81 3a 00    	mov    edx,DWORD PTR ds:0x3a8178
  1c69d7:	c9                   	leave
  1c69d8:	8d 04 82             	lea    eax,[edx+eax*4]
  1c69db:	c3                   	ret
  1c69dc:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]

001c69e0 <ED_AllowImmediateReuse()>:
  1c69e0:	55                   	push   ebp
  1c69e1:	89 e5                	mov    ebp,esp
  1c69e3:	53                   	push   ebx
  1c69e4:	83 ec 14             	sub    esp,0x14
  1c69e7:	8b 1d 74 81 3a 00    	mov    ebx,DWORD PTR ds:0x3a8174
  1c69ed:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c69f4:	e8 27 05 f3 ff       	call   f6f20 <CBaseServer::GetMaxClients() const>
  1c69f9:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6a00:	83 c0 01             	add    eax,0x1
  1c6a03:	c1 e0 04             	shl    eax,0x4
  1c6a06:	01 c3                	add    ebx,eax
  1c6a08:	e8 13 05 f3 ff       	call   f6f20 <CBaseServer::GetMaxClients() const>
  1c6a0d:	8b 15 6c 81 3a 00    	mov    edx,DWORD PTR ds:0x3a816c
  1c6a13:	83 c0 01             	add    eax,0x1
  1c6a16:	39 d0                	cmp    eax,edx
  1c6a18:	7d 20                	jge    1c6a3a <ED_AllowImmediateReuse()+0x5a>
  1c6a1a:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
  1c6a20:	f6 03 02             	test   BYTE PTR [ebx],0x2
  1c6a23:	74 0b                	je     1c6a30 <ED_AllowImmediateReuse()+0x50>
  1c6a25:	c7 04 85 c0 e4 39 00 00 00 00 00 	mov    DWORD PTR [eax*4+0x39e4c0],0x0
  1c6a30:	83 c0 01             	add    eax,0x1
  1c6a33:	83 c3 10             	add    ebx,0x10
  1c6a36:	39 d0                	cmp    eax,edx
  1c6a38:	75 e6                	jne    1c6a20 <ED_AllowImmediateReuse()+0x40>
  1c6a3a:	83 c4 14             	add    esp,0x14
  1c6a3d:	5b                   	pop    ebx
  1c6a3e:	5d                   	pop    ebp
  1c6a3f:	c3                   	ret

001c6a40 <ED_Alloc(int)>:
  1c6a40:	55                   	push   ebp
  1c6a41:	89 e5                	mov    ebp,esp
  1c6a43:	57                   	push   edi
  1c6a44:	56                   	push   esi
  1c6a45:	53                   	push   ebx
  1c6a46:	83 ec 1c             	sub    esp,0x1c
  1c6a49:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c6a4c:	85 db                	test   ebx,ebx
  1c6a4e:	78 30                	js     1c6a80 <ED_Alloc(int)+0x40>
  1c6a50:	3b 1d 6c 81 3a 00    	cmp    ebx,DWORD PTR ds:0x3a816c
  1c6a56:	0f 8d 94 01 00 00    	jge    1c6bf0 <ED_Alloc(int)+0x1b0>
  1c6a5c:	c1 e3 04             	shl    ebx,0x4
  1c6a5f:	31 c0                	xor    eax,eax
  1c6a61:	03 1d 74 81 3a 00    	add    ebx,DWORD PTR ds:0x3a8174
  1c6a67:	f6 03 02             	test   BYTE PTR [ebx],0x2
  1c6a6a:	74 0a                	je     1c6a76 <ED_Alloc(int)+0x36>
  1c6a6c:	89 1c 24             	mov    DWORD PTR [esp],ebx
  1c6a6f:	e8 bc fe ff ff       	call   1c6930 <ED_ClearEdict(edict_t*)>
  1c6a74:	89 d8                	mov    eax,ebx
  1c6a76:	83 c4 1c             	add    esp,0x1c
  1c6a79:	5b                   	pop    ebx
  1c6a7a:	5e                   	pop    esi
  1c6a7b:	5f                   	pop    edi
  1c6a7c:	5d                   	pop    ebp
  1c6a7d:	c3                   	ret
  1c6a7e:	66 90                	xchg   ax,ax
  1c6a80:	8b 35 74 81 3a 00    	mov    esi,DWORD PTR ds:0x3a8174
  1c6a86:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6a8d:	e8 8e 04 f3 ff       	call   f6f20 <CBaseServer::GetMaxClients() const>
  1c6a92:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6a99:	83 c0 01             	add    eax,0x1
  1c6a9c:	c1 e0 04             	shl    eax,0x4
  1c6a9f:	01 c6                	add    esi,eax
  1c6aa1:	e8 7a 04 f3 ff       	call   f6f20 <CBaseServer::GetMaxClients() const>
  1c6aa6:	8d 58 01             	lea    ebx,[eax+0x1]
  1c6aa9:	a1 6c 81 3a 00       	mov    eax,ds:0x3a816c
  1c6aae:	39 c3                	cmp    ebx,eax
  1c6ab0:	89 c2                	mov    edx,eax
  1c6ab2:	0f 8d 00 01 00 00    	jge    1c6bb8 <ED_Alloc(int)+0x178>
  1c6ab8:	f3 0f 10 15 d8 80 29 00 	movss  xmm2,DWORD PTR ds:0x2980d8
  1c6ac0:	bf ff ff ff ff       	mov    edi,0xffffffff
  1c6ac5:	8d 76 00             	lea    esi,[esi+0x0]
  1c6ac8:	f6 06 02             	test   BYTE PTR [esi],0x2
  1c6acb:	0f 84 8f 00 00 00    	je     1c6b60 <ED_Alloc(int)+0x120>
  1c6ad1:	f3 0f 10 04 9d c0 e4 39 00 	movss  xmm0,DWORD PTR [ebx*4+0x39e4c0]
  1c6ada:	0f 2f d0             	comiss xmm2,xmm0
  1c6add:	76 41                	jbe    1c6b20 <ED_Alloc(int)+0xe0>
  1c6adf:	0f 2f 05 f8 27 29 00 	comiss xmm0,DWORD PTR ds:0x2927f8
  1c6ae6:	75 20                	jne    1c6b08 <ED_Alloc(int)+0xc8>
  1c6ae8:	a1 dc 04 3a 00       	mov    eax,ds:0x3a04dc
  1c6aed:	8b 50 30             	mov    edx,DWORD PTR [eax+0x30]
  1c6af0:	85 d2                	test   edx,edx
  1c6af2:	74 14                	je     1c6b08 <ED_Alloc(int)+0xc8>
  1c6af4:	a1 f4 17 33 00       	mov    eax,ds:0x3317f4
  1c6af9:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c6afd:	89 04 24             	mov    DWORD PTR [esp],eax
  1c6b00:	e8 8b b7 01 00       	call   1e2290 <CFrameSnapshotManager::AddExplicitDelete(int)>
  1c6b05:	8d 76 00             	lea    esi,[esi+0x0]
  1c6b08:	89 34 24             	mov    DWORD PTR [esp],esi
  1c6b0b:	e8 20 fe ff ff       	call   1c6930 <ED_ClearEdict(edict_t*)>
  1c6b10:	89 f0                	mov    eax,esi
  1c6b12:	e9 5f ff ff ff       	jmp    1c6a76 <ED_Alloc(int)+0x36>
  1c6b17:	89 f6                	mov    esi,esi
  1c6b19:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]
  1c6b20:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6b27:	f3 0f 11 55 e0       	movss  DWORD PTR [ebp-0x20],xmm2
  1c6b2c:	e8 2f 03 f3 ff       	call   f6e60 <CBaseServer::GetTime() const>
  1c6b31:	f3 0f 10 55 e0       	movss  xmm2,DWORD PTR [ebp-0x20]
  1c6b36:	f3 0f 10 04 9d c0 e4 39 00 	movss  xmm0,DWORD PTR [ebx*4+0x39e4c0]
  1c6b3f:	d9 5d e4             	fstp   DWORD PTR [ebp-0x1c]
  1c6b42:	f3 0f 10 4d e4       	movss  xmm1,DWORD PTR [ebp-0x1c]
  1c6b47:	f3 0f 5c c8          	subss  xmm1,xmm0
  1c6b4b:	0f 2f 0d fc 27 29 00 	comiss xmm1,DWORD PTR ds:0x2927fc
  1c6b52:	73 8b                	jae    1c6adf <ED_Alloc(int)+0x9f>
  1c6b54:	a1 6c 81 3a 00       	mov    eax,ds:0x3a816c
  1c6b59:	89 df                	mov    edi,ebx
  1c6b5b:	90                   	nop
  1c6b5c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1c6b60:	83 c3 01             	add    ebx,0x1
  1c6b63:	83 c6 10             	add    esi,0x10
  1c6b66:	89 c2                	mov    edx,eax
  1c6b68:	39 d8                	cmp    eax,ebx
  1c6b6a:	0f 8f 58 ff ff ff    	jg     1c6ac8 <ED_Alloc(int)+0x88>
  1c6b70:	8b 0d 70 81 3a 00    	mov    ecx,DWORD PTR ds:0x3a8170
  1c6b76:	39 c8                	cmp    eax,ecx
  1c6b78:	7c 5e                	jl     1c6bd8 <ED_Alloc(int)+0x198>
  1c6b7a:	85 ff                	test   edi,edi
  1c6b7c:	78 44                	js     1c6bc2 <ED_Alloc(int)+0x182>
  1c6b7e:	0f 57 c0             	xorps  xmm0,xmm0
  1c6b81:	0f 2f 04 bd c0 e4 39 00 	comiss xmm0,DWORD PTR [edi*4+0x39e4c0]
  1c6b89:	75 1d                	jne    1c6ba8 <ED_Alloc(int)+0x168>
  1c6b8b:	a1 dc 04 3a 00       	mov    eax,ds:0x3a04dc
  1c6b90:	8b 40 30             	mov    eax,DWORD PTR [eax+0x30]
  1c6b93:	85 c0                	test   eax,eax
  1c6b95:	74 11                	je     1c6ba8 <ED_Alloc(int)+0x168>
  1c6b97:	a1 f4 17 33 00       	mov    eax,ds:0x3317f4
  1c6b9c:	89 7c 24 04          	mov    DWORD PTR [esp+0x4],edi
  1c6ba0:	89 04 24             	mov    DWORD PTR [esp],eax
  1c6ba3:	e8 e8 b6 01 00       	call   1e2290 <CFrameSnapshotManager::AddExplicitDelete(int)>
  1c6ba8:	8b 35 74 81 3a 00    	mov    esi,DWORD PTR ds:0x3a8174
  1c6bae:	c1 e7 04             	shl    edi,0x4
  1c6bb1:	01 fe                	add    esi,edi
  1c6bb3:	e9 50 ff ff ff       	jmp    1c6b08 <ED_Alloc(int)+0xc8>
  1c6bb8:	8b 0d 70 81 3a 00    	mov    ecx,DWORD PTR ds:0x3a8170
  1c6bbe:	39 c1                	cmp    ecx,eax
  1c6bc0:	7f 16                	jg     1c6bd8 <ED_Alloc(int)+0x198>
  1c6bc2:	85 c9                	test   ecx,ecx
  1c6bc4:	74 41                	je     1c6c07 <ED_Alloc(int)+0x1c7>
  1c6bc6:	c7 04 24 9c db 2a 00 	mov    DWORD PTR [esp],0x2adb9c
  1c6bcd:	e8 de e5 03 00       	call   2051b0 <Sys_Error(char const*, ...)>
  1c6bd2:	8b 15 6c 81 3a 00    	mov    edx,DWORD PTR ds:0x3a816c
  1c6bd8:	83 c2 01             	add    edx,0x1
  1c6bdb:	89 34 24             	mov    DWORD PTR [esp],esi
  1c6bde:	89 15 6c 81 3a 00    	mov    DWORD PTR ds:0x3a816c,edx
  1c6be4:	e8 47 fd ff ff       	call   1c6930 <ED_ClearEdict(edict_t*)>
  1c6be9:	89 f0                	mov    eax,esi
  1c6beb:	e9 86 fe ff ff       	jmp    1c6a76 <ED_Alloc(int)+0x36>
  1c6bf0:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c6bf4:	c7 04 24 24 dc 2a 00 	mov    DWORD PTR [esp],0x2adc24
  1c6bfb:	e8 fc ff ff ff       	call   1c6bfc <ED_Alloc(int)+0x1bc>
  1c6c00:	31 c0                	xor    eax,eax
  1c6c02:	e9 6f fe ff ff       	jmp    1c6a76 <ED_Alloc(int)+0x36>
  1c6c07:	c7 04 24 84 db 2a 00 	mov    DWORD PTR [esp],0x2adb84
  1c6c0e:	e8 9d e5 03 00       	call   2051b0 <Sys_Error(char const*, ...)>
  1c6c13:	eb b1                	jmp    1c6bc6 <ED_Alloc(int)+0x186>
  1c6c15:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1c6c19:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]

001c6c20 <ED_Free(edict_t*)>:
  1c6c20:	55                   	push   ebp
  1c6c21:	89 e5                	mov    ebp,esp
  1c6c23:	56                   	push   esi
  1c6c24:	53                   	push   ebx
  1c6c25:	83 ec 10             	sub    esp,0x10
  1c6c28:	a1 74 81 3a 00       	mov    eax,ds:0x3a8174
  1c6c2d:	8b 5d 08             	mov    ebx,DWORD PTR [ebp+0x8]
  1c6c30:	85 c0                	test   eax,eax
  1c6c32:	74 6c                	je     1c6ca0 <ED_Free(edict_t*)+0x80>
  1c6c34:	f6 03 02             	test   BYTE PTR [ebx],0x2
  1c6c37:	75 1b                	jne    1c6c54 <ED_Free(edict_t*)+0x34>
  1c6c39:	89 de                	mov    esi,ebx
  1c6c3b:	29 c6                	sub    esi,eax
  1c6c3d:	c1 fe 04             	sar    esi,0x4
  1c6c40:	85 f6                	test   esi,esi
  1c6c42:	7e 1c                	jle    1c6c60 <ED_Free(edict_t*)+0x40>
  1c6c44:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6c4b:	e8 d0 02 f3 ff       	call   f6f20 <CBaseServer::GetMaxClients() const>
  1c6c50:	39 c6                	cmp    esi,eax
  1c6c52:	7f 0c                	jg     1c6c60 <ED_Free(edict_t*)+0x40>
  1c6c54:	83 c4 10             	add    esp,0x10
  1c6c57:	5b                   	pop    ebx
  1c6c58:	5e                   	pop    esi
  1c6c59:	5d                   	pop    ebp
  1c6c5a:	c3                   	ret
  1c6c5b:	90                   	nop
  1c6c5c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1c6c60:	a1 78 c3 3d 00       	mov    eax,ds:0x3dc378
  1c6c65:	8b 10                	mov    edx,DWORD PTR [eax]
  1c6c67:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c6c6b:	89 04 24             	mov    DWORD PTR [esp],eax
  1c6c6e:	ff 52 0c             	call   DWORD PTR [edx+0xc]
  1c6c71:	83 0b 02             	or     DWORD PTR [ebx],0x2
  1c6c74:	c7 04 24 60 7f 3a 00 	mov    DWORD PTR [esp],0x3a7f60
  1c6c7b:	e8 e0 01 f3 ff       	call   f6e60 <CBaseServer::GetTime() const>
  1c6c80:	d9 5d f4             	fstp   DWORD PTR [ebp-0xc]
  1c6c83:	f3 0f 10 45 f4       	movss  xmm0,DWORD PTR [ebp-0xc]
  1c6c88:	f3 0f 11 04 b5 c0 e4 39 00 	movss  DWORD PTR [esi*4+0x39e4c0],xmm0
  1c6c91:	83 43 04 01          	add    DWORD PTR [ebx+0x4],0x1
  1c6c95:	83 c4 10             	add    esp,0x10
  1c6c98:	5b                   	pop    ebx
  1c6c99:	5e                   	pop    esi
  1c6c9a:	5d                   	pop    ebp
  1c6c9b:	c3                   	ret
  1c6c9c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
  1c6ca0:	89 5c 24 04          	mov    DWORD PTR [esp+0x4],ebx
  1c6ca4:	c7 04 24 54 dc 2a 00 	mov    DWORD PTR [esp],0x2adc54
  1c6cab:	e8 fc ff ff ff       	call   1c6cac <ED_Free(edict_t*)+0x8c>
  1c6cb0:	c7 45 08 05 00 00 00 	mov    DWORD PTR [ebp+0x8],0x5
  1c6cb7:	83 c4 10             	add    esp,0x10
  1c6cba:	5b                   	pop    ebx
  1c6cbb:	5e                   	pop    esi
  1c6cbc:	5d                   	pop    ebp
  1c6cbd:	e9 fc ff ff ff       	jmp    1c6cbe <ED_Free(edict_t*)+0x9e>
  1c6cc2:	90                   	nop
  1c6cc3:	90                   	nop
  1c6cc4:	90                   	nop
  1c6cc5:	90                   	nop
  1c6cc6:	90                   	nop
  1c6cc7:	90                   	nop
  1c6cc8:	90                   	nop
  1c6cc9:	90                   	nop
  1c6cca:	90                   	nop
  1c6ccb:	90                   	nop
  1c6ccc:	90                   	nop
  1c6ccd:	90                   	nop
  1c6cce:	90                   	nop
  1c6ccf:	90                   	nop

001c6cd0 <IsProtectedBySvPure2(char const*)>:
  1c6cd0:	55                   	push   ebp
  1c6cd1:	89 e5                	mov    ebp,esp
  1c6cd3:	57                   	push   edi
  1c6cd4:	56                   	push   esi
  1c6cd5:	31 f6                	xor    esi,esi
  1c6cd7:	53                   	push   ebx
  1c6cd8:	81 ec 2c 02 00 00    	sub    esp,0x22c
  1c6cde:	89 85 d4 fd ff ff    	mov    DWORD PTR [ebp-0x22c],eax
  1c6ce4:	65 a1 14 00 00 00    	mov    eax,gs:0x14
  1c6cea:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
  1c6ced:	31 c0                	xor    eax,eax
  1c6cef:	8b 3c b5 28 de 2a 00 	mov    edi,DWORD PTR [esi*4+0x2ade28]
  1c6cf6:	89 3c 24             	mov    DWORD PTR [esp],edi
  1c6cf9:	e8 f2 5a 08 00       	call   24c7f0 <_V_strlen(char const*)>
  1c6cfe:	89 c3                	mov    ebx,eax
