
/home/void0312/l4d2_server/bin/engine_srv.so:     file format elf32-i386


Disassembly of section .text:

000a5170 <SVC_PacketEntities::ReadFromBuffer(bf_read&)>:
   a5170:	55                   	push   ebp
   a5171:	89 e5                	mov    ebp,esp
   a5173:	57                   	push   edi
   a5174:	56                   	push   esi
   a5175:	53                   	push   ebx
   a5176:	83 ec 6c             	sub    esp,0x6c
   a5179:	c7 45 d0 00 00 00 00 	mov    DWORD PTR [ebp-0x30],0x0
   a5180:	a1 0c 00 00 00       	mov    eax,ds:0xc
   a5185:	c7 45 d4 00 00 00 00 	mov    DWORD PTR [ebp-0x2c],0x0
   a518c:	8b 75 08             	mov    esi,DWORD PTR [ebp+0x8]
   a518f:	8b 5d 0c             	mov    ebx,DWORD PTR [ebp+0xc]
   a5192:	85 c0                	test   eax,eax
   a5194:	0f 84 7e 04 00 00    	je     a5618 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x4a8>
   a519a:	8d 55 d0             	lea    edx,[ebp-0x30]
   a519d:	89 04 24             	mov    DWORD PTR [esp],eax
   a51a0:	89 54 24 04          	mov    DWORD PTR [esp+0x4],edx
   a51a4:	c7 44 24 2c e4 0a 29 00 	mov    DWORD PTR [esp+0x2c],0x290ae4
   a51ac:	c7 44 24 28 4b 05 29 00 	mov    DWORD PTR [esp+0x28],0x29054b
   a51b4:	c7 44 24 24 57 05 29 00 	mov    DWORD PTR [esp+0x24],0x290557
   a51bc:	c7 44 24 20 70 2d 33 00 	mov    DWORD PTR [esp+0x20],0x332d70
   a51c4:	c7 44 24 1c 68 06 00 00 	mov    DWORD PTR [esp+0x1c],0x668
   a51cc:	c7 44 24 18 e8 08 29 00 	mov    DWORD PTR [esp+0x18],0x2908e8
   a51d4:	c7 44 24 14 00 00 00 00 	mov    DWORD PTR [esp+0x14],0x0
   a51dc:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [esp+0xc],0x0
   a51e4:	c7 44 24 10 00 00 00 00 	mov    DWORD PTR [esp+0x10],0x0
   a51ec:	c7 44 24 08 00 00 00 00 	mov    DWORD PTR [esp+0x8],0x0
   a51f4:	ff 50 50             	call   DWORD PTR [eax+0x50]
   a51f7:	8b 45 d0             	mov    eax,DWORD PTR [ebp-0x30]
   a51fa:	8b 55 d4             	mov    edx,DWORD PTR [ebp-0x2c]
   a51fd:	8b 0d 0c 00 00 00    	mov    ecx,DWORD PTR ds:0xc
   a5203:	89 55 e0             	mov    DWORD PTR [ebp-0x20],edx
   a5206:	8b 15 0c 10 00 00    	mov    edx,DWORD PTR ds:0x100c
   a520c:	89 4d e4             	mov    DWORD PTR [ebp-0x1c],ecx
   a520f:	89 45 dc             	mov    DWORD PTR [ebp-0x24],eax
   a5212:	85 d2                	test   edx,edx
   a5214:	75 09                	jne    a521f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xaf>
   a5216:	80 3d 10 10 00 00 00 	cmp    BYTE PTR ds:0x1010,0x0
   a521d:	75 13                	jne    a5232 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xc2>
   a521f:	8b 3d b8 19 00 00    	mov    edi,DWORD PTR ds:0x19b8
   a5225:	e8 fc ff ff ff       	call   a5226 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xb6>
   a522a:	39 c7                	cmp    edi,eax
   a522c:	0f 84 8e 05 00 00    	je     a57c0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x650>
   a5232:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a5235:	83 f9 0a             	cmp    ecx,0xa
   a5238:	0f 8e 82 01 00 00    	jle    a53c0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x250>
   a523e:	8b 53 10             	mov    edx,DWORD PTR [ebx+0x10]
   a5241:	83 e9 0b             	sub    ecx,0xb
   a5244:	a1 ec c8 2b 00       	mov    eax,ds:0x2bc8ec
   a5249:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a524c:	21 d0                	and    eax,edx
   a524e:	85 c9                	test   ecx,ecx
   a5250:	0f 84 9a 01 00 00    	je     a53f0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x280>
   a5256:	c1 ea 0b             	shr    edx,0xb
   a5259:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a525c:	89 46 4c             	mov    DWORD PTR [esi+0x4c],eax
   a525f:	8b 7b 14             	mov    edi,DWORD PTR [ebx+0x14]
   a5262:	8b 4b 10             	mov    ecx,DWORD PTR [ebx+0x10]
   a5265:	8d 57 ff             	lea    edx,[edi-0x1]
   a5268:	89 c8                	mov    eax,ecx
   a526a:	89 53 14             	mov    DWORD PTR [ebx+0x14],edx
   a526d:	83 e0 01             	and    eax,0x1
   a5270:	85 d2                	test   edx,edx
   a5272:	0f 85 60 03 00 00    	jne    a55d8 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x468>
   a5278:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a527b:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a5282:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a5285:	0f 84 b5 06 00 00    	je     a5940 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x7d0>
   a528b:	0f 86 1f 05 00 00    	jbe    a57b0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x640>
   a5291:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5295:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a529c:	83 e0 01             	and    eax,0x1
   a529f:	84 c0                	test   al,al
   a52a1:	88 46 54             	mov    BYTE PTR [esi+0x54],al
   a52a4:	0f 84 76 01 00 00    	je     a5420 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2b0>
   a52aa:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a52ad:	83 f9 1f             	cmp    ecx,0x1f
   a52b0:	0f 8e d2 03 00 00    	jle    a5688 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x518>
   a52b6:	a1 40 c9 2b 00       	mov    eax,ds:0x2bc940
   a52bb:	83 e9 20             	sub    ecx,0x20
   a52be:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a52c1:	23 43 10             	and    eax,DWORD PTR [ebx+0x10]
   a52c4:	85 c9                	test   ecx,ecx
   a52c6:	75 1d                	jne    a52e5 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x175>
   a52c8:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a52cb:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a52d2:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a52d5:	0f 84 4e 07 00 00    	je     a5a29 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x8b9>
   a52db:	0f 86 9f 06 00 00    	jbe    a5980 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x810>
   a52e1:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a52e5:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a52ec:	89 46 5c             	mov    DWORD PTR [esi+0x5c],eax
   a52ef:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a52f2:	85 c9                	test   ecx,ecx
   a52f4:	0f 8f 38 01 00 00    	jg     a5432 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2c2>
   a52fa:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a52fd:	89 45 c4             	mov    DWORD PTR [ebp-0x3c],eax
   a5300:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a5303:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a5306:	0f 84 84 06 00 00    	je     a5990 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x820>
   a530c:	0f 87 0e 05 00 00    	ja     a5820 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6b0>
   a5312:	8d 50 04             	lea    edx,[eax+0x4]
   a5315:	80 7b 04 00          	cmp    BYTE PTR [ebx+0x4],0x0
   a5319:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a531c:	8b 38                	mov    edi,DWORD PTR [eax]
   a531e:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a5321:	0f 85 04 05 00 00    	jne    a582b <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6bb>
   a5327:	ba 01 00 00 00       	mov    edx,0x1
   a532c:	29 ca                	sub    edx,ecx
   a532e:	8b 04 95 c0 c8 2b 00 	mov    eax,DWORD PTR [edx*4+0x2bc8c0]
   a5335:	21 f8                	and    eax,edi
   a5337:	d3 e0                	shl    eax,cl
   a5339:	83 c1 1f             	add    ecx,0x1f
   a533c:	0b 45 c4             	or     eax,DWORD PTR [ebp-0x3c]
   a533f:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a5342:	89 d1                	mov    ecx,edx
   a5344:	d3 ef                	shr    edi,cl
   a5346:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a5349:	89 46 58             	mov    DWORD PTR [esi+0x58],eax
   a534c:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a534f:	83 f9 0a             	cmp    ecx,0xa
   a5352:	0f 8f 06 01 00 00    	jg     a545e <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2ee>
   a5358:	90                   	nop
   a5359:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5360:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a5363:	89 45 c4             	mov    DWORD PTR [ebp-0x3c],eax
   a5366:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a5369:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a536c:	0f 84 ae 05 00 00    	je     a5920 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x7b0>
   a5372:	0f 86 f8 03 00 00    	jbe    a5770 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x600>
   a5378:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a537c:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5383:	31 c0                	xor    eax,eax
   a5385:	89 46 50             	mov    DWORD PTR [esi+0x50],eax
   a5388:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a538b:	83 f9 13             	cmp    ecx,0x13
   a538e:	0f 8f f7 00 00 00    	jg     a548b <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x31b>
   a5394:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a5397:	89 45 c4             	mov    DWORD PTR [ebp-0x3c],eax
   a539a:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a539d:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a53a0:	0f 84 5a 05 00 00    	je     a5900 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x790>
   a53a6:	0f 86 34 03 00 00    	jbe    a56e0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x570>
   a53ac:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a53b0:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a53b7:	31 c0                	xor    eax,eax
   a53b9:	e9 eb 00 00 00       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a53be:	66 90                	xchg   ax,ax
   a53c0:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a53c3:	89 45 c4             	mov    DWORD PTR [ebp-0x3c],eax
   a53c6:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a53c9:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a53cc:	0f 84 ae 04 00 00    	je     a5880 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x710>
   a53d2:	0f 86 58 03 00 00    	jbe    a5730 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x5c0>
   a53d8:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a53dc:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a53e3:	31 c0                	xor    eax,eax
   a53e5:	e9 72 fe ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a53ea:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
   a53f0:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a53f3:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a53fa:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a53fd:	0f 84 ad 05 00 00    	je     a59b0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x840>
   a5403:	0f 86 67 04 00 00    	jbe    a5870 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x700>
   a5409:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a540d:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5414:	e9 43 fe ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a5419:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5420:	c7 46 5c ff ff ff ff 	mov    DWORD PTR [esi+0x5c],0xffffffff
   a5427:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a542a:	85 c9                	test   ecx,ecx
   a542c:	0f 8e c8 fe ff ff    	jle    a52fa <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x18a>
   a5432:	8b 53 10             	mov    edx,DWORD PTR [ebx+0x10]
   a5435:	83 e9 01             	sub    ecx,0x1
   a5438:	a1 c4 c8 2b 00       	mov    eax,ds:0x2bc8c4
   a543d:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a5440:	21 d0                	and    eax,edx
   a5442:	85 c9                	test   ecx,ecx
   a5444:	0f 84 9e 01 00 00    	je     a55e8 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x478>
   a544a:	d1 ea                	shr    edx,1
   a544c:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a544f:	89 46 58             	mov    DWORD PTR [esi+0x58],eax
   a5452:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a5455:	83 f9 0a             	cmp    ecx,0xa
   a5458:	0f 8e 02 ff ff ff    	jle    a5360 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x1f0>
   a545e:	8b 53 10             	mov    edx,DWORD PTR [ebx+0x10]
   a5461:	83 e9 0b             	sub    ecx,0xb
   a5464:	a1 ec c8 2b 00       	mov    eax,ds:0x2bc8ec
   a5469:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a546c:	21 d0                	and    eax,edx
   a546e:	85 c9                	test   ecx,ecx
   a5470:	0f 84 e2 01 00 00    	je     a5658 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x4e8>
   a5476:	c1 ea 0b             	shr    edx,0xb
   a5479:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a547c:	89 46 50             	mov    DWORD PTR [esi+0x50],eax
   a547f:	8b 4b 14             	mov    ecx,DWORD PTR [ebx+0x14]
   a5482:	83 f9 13             	cmp    ecx,0x13
   a5485:	0f 8e 09 ff ff ff    	jle    a5394 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x224>
   a548b:	8b 53 10             	mov    edx,DWORD PTR [ebx+0x10]
   a548e:	83 e9 14             	sub    ecx,0x14
   a5491:	a1 10 c9 2b 00       	mov    eax,ds:0x2bc910
   a5496:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a5499:	21 d0                	and    eax,edx
   a549b:	85 c9                	test   ecx,ecx
   a549d:	0f 84 85 01 00 00    	je     a5628 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x4b8>
   a54a3:	c1 ea 14             	shr    edx,0x14
   a54a6:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a54a9:	89 46 60             	mov    DWORD PTR [esi+0x60],eax
   a54ac:	8b 53 10             	mov    edx,DWORD PTR [ebx+0x10]
   a54af:	89 d1                	mov    ecx,edx
   a54b1:	83 e1 01             	and    ecx,0x1
   a54b4:	83 6b 14 01          	sub    DWORD PTR [ebx+0x14],0x1
   a54b8:	0f 85 0a 01 00 00    	jne    a55c8 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x458>
   a54be:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a54c1:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a54c8:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a54cb:	0f 84 0f 04 00 00    	je     a58e0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x770>
   a54d1:	0f 86 49 02 00 00    	jbe    a5720 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x5b0>
   a54d7:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a54db:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a54e2:	88 4e 55             	mov    BYTE PTR [esi+0x55],cl
   a54e5:	8b 4e 60             	mov    ecx,DWORD PTR [esi+0x60]
   a54e8:	80 66 55 01          	and    BYTE PTR [esi+0x55],0x1
   a54ec:	8b 03                	mov    eax,DWORD PTR [ebx]
   a54ee:	89 46 64             	mov    DWORD PTR [esi+0x64],eax
   a54f1:	8b 43 04             	mov    eax,DWORD PTR [ebx+0x4]
   a54f4:	89 46 68             	mov    DWORD PTR [esi+0x68],eax
   a54f7:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
   a54fa:	89 46 6c             	mov    DWORD PTR [esi+0x6c],eax
   a54fd:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   a5500:	89 46 70             	mov    DWORD PTR [esi+0x70],eax
   a5503:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a5506:	89 46 74             	mov    DWORD PTR [esi+0x74],eax
   a5509:	8b 43 14             	mov    eax,DWORD PTR [ebx+0x14]
   a550c:	89 46 78             	mov    DWORD PTR [esi+0x78],eax
   a550f:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a5512:	89 46 7c             	mov    DWORD PTR [esi+0x7c],eax
   a5515:	8b 43 1c             	mov    eax,DWORD PTR [ebx+0x1c]
   a5518:	89 86 80 00 00 00    	mov    DWORD PTR [esi+0x80],eax
   a551e:	8b 43 20             	mov    eax,DWORD PTR [ebx+0x20]
   a5521:	89 86 84 00 00 00    	mov    DWORD PTR [esi+0x84],eax
   a5527:	8b 53 20             	mov    edx,DWORD PTR [ebx+0x20]
   a552a:	85 d2                	test   edx,edx
   a552c:	0f 84 9e 03 00 00    	je     a58d0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x760>
   a5532:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a5535:	29 d0                	sub    eax,edx
   a5537:	8b 53 0c             	mov    edx,DWORD PTR [ebx+0xc]
   a553a:	c1 e8 02             	shr    eax,0x2
   a553d:	c1 e0 05             	shl    eax,0x5
   a5540:	2b 43 14             	sub    eax,DWORD PTR [ebx+0x14]
   a5543:	83 e2 03             	and    edx,0x3
   a5546:	8d 14 d0             	lea    edx,[eax+edx*8]
   a5549:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
   a554c:	39 c2                	cmp    edx,eax
   a554e:	0f 4e c2             	cmovle eax,edx
   a5551:	01 c1                	add    ecx,eax
   a5553:	89 1c 24             	mov    DWORD PTR [esp],ebx
   a5556:	89 4c 24 04          	mov    DWORD PTR [esp+0x4],ecx
   a555a:	e8 c1 1e 1a 00       	call   247420 <CBitRead::Seek(int)>
   a555f:	80 3d 10 10 00 00 00 	cmp    BYTE PTR ds:0x1010,0x0
   a5566:	89 c6                	mov    esi,eax
   a5568:	74 09                	je     a5573 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x403>
   a556a:	a1 0c 10 00 00       	mov    eax,ds:0x100c
   a556f:	85 c0                	test   eax,eax
   a5571:	74 13                	je     a5586 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x416>
   a5573:	8b 1d b8 19 00 00    	mov    ebx,DWORD PTR ds:0x19b8
   a5579:	e8 fc ff ff ff       	call   a557a <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x40a>
   a557e:	39 c3                	cmp    ebx,eax
   a5580:	0f 84 1a 03 00 00    	je     a58a0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x730>
   a5586:	8b 45 e4             	mov    eax,DWORD PTR [ebp-0x1c]
   a5589:	85 c0                	test   eax,eax
   a558b:	74 2c                	je     a55b9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x449>
   a558d:	8b 4d dc             	mov    ecx,DWORD PTR [ebp-0x24]
   a5590:	c7 44 24 14 00 00 00 00 	mov    DWORD PTR [esp+0x14],0x0
   a5598:	8b 5d e0             	mov    ebx,DWORD PTR [ebp-0x20]
   a559b:	c7 44 24 10 00 00 00 00 	mov    DWORD PTR [esp+0x10],0x0
   a55a3:	c7 44 24 0c 00 00 00 00 	mov    DWORD PTR [esp+0xc],0x0
   a55ab:	89 04 24             	mov    DWORD PTR [esp],eax
   a55ae:	89 4c 24 04          	mov    DWORD PTR [esp+0x4],ecx
   a55b2:	89 5c 24 08          	mov    DWORD PTR [esp+0x8],ebx
   a55b6:	ff 50 54             	call   DWORD PTR [eax+0x54]
   a55b9:	83 c4 6c             	add    esp,0x6c
   a55bc:	89 f0                	mov    eax,esi
   a55be:	5b                   	pop    ebx
   a55bf:	5e                   	pop    esi
   a55c0:	5f                   	pop    edi
   a55c1:	5d                   	pop    ebp
   a55c2:	c3                   	ret
   a55c3:	90                   	nop
   a55c4:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   a55c8:	d1 ea                	shr    edx,1
   a55ca:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a55cd:	e9 10 ff ff ff       	jmp    a54e2 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x372>
   a55d2:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
   a55d8:	d1 e9                	shr    ecx,1
   a55da:	89 4b 10             	mov    DWORD PTR [ebx+0x10],ecx
   a55dd:	e9 ba fc ff ff       	jmp    a529c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x12c>
   a55e2:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
   a55e8:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a55eb:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a55f2:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a55f5:	0f 84 65 03 00 00    	je     a5960 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x7f0>
   a55fb:	0f 86 0f 02 00 00    	jbe    a5810 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6a0>
   a5601:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5605:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a560c:	e9 3e fe ff ff       	jmp    a544f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2df>
   a5611:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5618:	31 c9                	xor    ecx,ecx
   a561a:	31 c0                	xor    eax,eax
   a561c:	31 d2                	xor    edx,edx
   a561e:	e9 e0 fb ff ff       	jmp    a5203 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x93>
   a5623:	90                   	nop
   a5624:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   a5628:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a562b:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a5632:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a5635:	0f 84 d5 03 00 00    	je     a5a10 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x8a0>
   a563b:	0f 86 1f 02 00 00    	jbe    a5860 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6f0>
   a5641:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5645:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a564c:	e9 58 fe ff ff       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a5651:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5658:	8b 53 18             	mov    edx,DWORD PTR [ebx+0x18]
   a565b:	c7 43 14 20 00 00 00 	mov    DWORD PTR [ebx+0x14],0x20
   a5662:	3b 53 1c             	cmp    edx,DWORD PTR [ebx+0x1c]
   a5665:	0f 84 65 03 00 00    	je     a59d0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x860>
   a566b:	0f 86 df 01 00 00    	jbe    a5850 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6e0>
   a5671:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5675:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a567c:	e9 fb fd ff ff       	jmp    a547c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x30c>
   a5681:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5688:	8b 43 10             	mov    eax,DWORD PTR [ebx+0x10]
   a568b:	89 45 c4             	mov    DWORD PTR [ebp-0x3c],eax
   a568e:	8b 43 18             	mov    eax,DWORD PTR [ebx+0x18]
   a5691:	3b 43 1c             	cmp    eax,DWORD PTR [ebx+0x1c]
   a5694:	0f 84 56 03 00 00    	je     a59f0 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x880>
   a569a:	0f 87 98 01 00 00    	ja     a5838 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6c8>
   a56a0:	8d 50 04             	lea    edx,[eax+0x4]
   a56a3:	80 7b 04 00          	cmp    BYTE PTR [ebx+0x4],0x0
   a56a7:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a56aa:	8b 38                	mov    edi,DWORD PTR [eax]
   a56ac:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a56af:	0f 85 8e 01 00 00    	jne    a5843 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x6d3>
   a56b5:	ba 20 00 00 00       	mov    edx,0x20
   a56ba:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a56bd:	29 ca                	sub    edx,ecx
   a56bf:	8b 04 95 c0 c8 2b 00 	mov    eax,DWORD PTR [edx*4+0x2bc8c0]
   a56c6:	21 f8                	and    eax,edi
   a56c8:	d3 e0                	shl    eax,cl
   a56ca:	89 d1                	mov    ecx,edx
   a56cc:	d3 ef                	shr    edi,cl
   a56ce:	0b 45 c4             	or     eax,DWORD PTR [ebp-0x3c]
   a56d1:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a56d4:	e9 13 fc ff ff       	jmp    a52ec <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x17c>
   a56d9:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a56e0:	8d 50 04             	lea    edx,[eax+0x4]
   a56e3:	80 7b 04 00          	cmp    BYTE PTR [ebx+0x4],0x0
   a56e7:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a56ea:	8b 38                	mov    edi,DWORD PTR [eax]
   a56ec:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a56ef:	0f 85 c2 fc ff ff    	jne    a53b7 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x247>
   a56f5:	ba 14 00 00 00       	mov    edx,0x14
   a56fa:	29 ca                	sub    edx,ecx
   a56fc:	8b 04 95 c0 c8 2b 00 	mov    eax,DWORD PTR [edx*4+0x2bc8c0]
   a5703:	21 f8                	and    eax,edi
   a5705:	d3 e0                	shl    eax,cl
   a5707:	83 c1 0c             	add    ecx,0xc
   a570a:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a570d:	89 d1                	mov    ecx,edx
   a570f:	0b 45 c4             	or     eax,DWORD PTR [ebp-0x3c]
   a5712:	d3 ef                	shr    edi,cl
   a5714:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a5717:	e9 8d fd ff ff       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a571c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   a5720:	8d 50 04             	lea    edx,[eax+0x4]
   a5723:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a5726:	8b 00                	mov    eax,DWORD PTR [eax]
   a5728:	89 43 10             	mov    DWORD PTR [ebx+0x10],eax
   a572b:	e9 b2 fd ff ff       	jmp    a54e2 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x372>
   a5730:	8d 50 04             	lea    edx,[eax+0x4]
   a5733:	80 7b 04 00          	cmp    BYTE PTR [ebx+0x4],0x0
   a5737:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a573a:	8b 38                	mov    edi,DWORD PTR [eax]
   a573c:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a573f:	0f 85 9e fc ff ff    	jne    a53e3 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x273>
   a5745:	ba 0b 00 00 00       	mov    edx,0xb
   a574a:	29 ca                	sub    edx,ecx
   a574c:	8b 04 95 c0 c8 2b 00 	mov    eax,DWORD PTR [edx*4+0x2bc8c0]
   a5753:	21 f8                	and    eax,edi
   a5755:	d3 e0                	shl    eax,cl
   a5757:	83 c1 15             	add    ecx,0x15
   a575a:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a575d:	89 d1                	mov    ecx,edx
   a575f:	0b 45 c4             	or     eax,DWORD PTR [ebp-0x3c]
   a5762:	d3 ef                	shr    edi,cl
   a5764:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a5767:	e9 f0 fa ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a576c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   a5770:	8d 50 04             	lea    edx,[eax+0x4]
   a5773:	80 7b 04 00          	cmp    BYTE PTR [ebx+0x4],0x0
   a5777:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a577a:	8b 38                	mov    edi,DWORD PTR [eax]
   a577c:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a577f:	0f 85 fe fb ff ff    	jne    a5383 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x213>
   a5785:	ba 0b 00 00 00       	mov    edx,0xb
   a578a:	29 ca                	sub    edx,ecx
   a578c:	8b 04 95 c0 c8 2b 00 	mov    eax,DWORD PTR [edx*4+0x2bc8c0]
   a5793:	21 f8                	and    eax,edi
   a5795:	d3 e0                	shl    eax,cl
   a5797:	83 c1 15             	add    ecx,0x15
   a579a:	89 4b 14             	mov    DWORD PTR [ebx+0x14],ecx
   a579d:	89 d1                	mov    ecx,edx
   a579f:	0b 45 c4             	or     eax,DWORD PTR [ebp-0x3c]
   a57a2:	d3 ef                	shr    edi,cl
   a57a4:	89 7b 10             	mov    DWORD PTR [ebx+0x10],edi
   a57a7:	e9 d0 fc ff ff       	jmp    a547c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x30c>
   a57ac:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   a57b0:	8d 4a 04             	lea    ecx,[edx+0x4]
   a57b3:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a57b6:	8b 12                	mov    edx,DWORD PTR [edx]
   a57b8:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a57bb:	e9 dc fa ff ff       	jmp    a529c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x12c>
   a57c0:	a1 14 10 00 00       	mov    eax,ds:0x1014
   a57c5:	81 38 e4 0a 29 00    	cmp    DWORD PTR [eax],0x290ae4
   a57cb:	74 2d                	je     a57fa <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x68a>
   a57cd:	c7 44 24 10 00 00 00 00 	mov    DWORD PTR [esp+0x10],0x0
   a57d5:	c7 44 24 0c 4b 05 29 00 	mov    DWORD PTR [esp+0xc],0x29054b
   a57dd:	c7 44 24 08 01 00 00 00 	mov    DWORD PTR [esp+0x8],0x1
   a57e5:	c7 44 24 04 e4 0a 29 00 	mov    DWORD PTR [esp+0x4],0x290ae4
   a57ed:	89 04 24             	mov    DWORD PTR [esp],eax
   a57f0:	e8 fc ff ff ff       	call   a57f1 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x681>
   a57f5:	a3 14 10 00 00       	mov    ds:0x1014,eax
   a57fa:	89 04 24             	mov    DWORD PTR [esp],eax
   a57fd:	e8 fc ff ff ff       	call   a57fe <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x68e>
   a5802:	c6 05 10 10 00 00 00 	mov    BYTE PTR ds:0x1010,0x0
   a5809:	e9 24 fa ff ff       	jmp    a5232 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xc2>
   a580e:	66 90                	xchg   ax,ax
   a5810:	8d 4a 04             	lea    ecx,[edx+0x4]
   a5813:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a5816:	8b 12                	mov    edx,DWORD PTR [edx]
   a5818:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a581b:	e9 2f fc ff ff       	jmp    a544f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2df>
   a5820:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5824:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a582b:	31 c0                	xor    eax,eax
   a582d:	e9 1d fc ff ff       	jmp    a544f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2df>
   a5832:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
   a5838:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a583c:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5843:	31 c0                	xor    eax,eax
   a5845:	e9 a2 fa ff ff       	jmp    a52ec <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x17c>
   a584a:	8d b6 00 00 00 00    	lea    esi,[esi+0x0]
   a5850:	8d 4a 04             	lea    ecx,[edx+0x4]
   a5853:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a5856:	8b 12                	mov    edx,DWORD PTR [edx]
   a5858:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a585b:	e9 1c fc ff ff       	jmp    a547c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x30c>
   a5860:	8d 4a 04             	lea    ecx,[edx+0x4]
   a5863:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a5866:	8b 12                	mov    edx,DWORD PTR [edx]
   a5868:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a586b:	e9 39 fc ff ff       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a5870:	8d 4a 04             	lea    ecx,[edx+0x4]
   a5873:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a5876:	8b 12                	mov    edx,DWORD PTR [edx]
   a5878:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a587b:	e9 dc f9 ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a5880:	83 c0 04             	add    eax,0x4
   a5883:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a588a:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a588d:	31 c0                	xor    eax,eax
   a588f:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5896:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a589a:	e9 bd f9 ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a589f:	90                   	nop
   a58a0:	a1 14 10 00 00       	mov    eax,ds:0x1014
   a58a5:	89 04 24             	mov    DWORD PTR [esp],eax
   a58a8:	e8 fc ff ff ff       	call   a58a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x739>
   a58ad:	84 c0                	test   al,al
   a58af:	a1 14 10 00 00       	mov    eax,ds:0x1014
   a58b4:	74 08                	je     a58be <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x74e>
   a58b6:	8b 40 64             	mov    eax,DWORD PTR [eax+0x64]
   a58b9:	a3 14 10 00 00       	mov    ds:0x1014,eax
   a58be:	3d 18 10 00 00       	cmp    eax,0x1018
   a58c3:	0f 94 05 10 10 00 00 	sete   BYTE PTR ds:0x1010
   a58ca:	e9 b7 fc ff ff       	jmp    a5586 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x416>
   a58cf:	90                   	nop
   a58d0:	31 c0                	xor    eax,eax
   a58d2:	e9 7a fc ff ff       	jmp    a5551 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x3e1>
   a58d7:	89 f6                	mov    esi,esi
   a58d9:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]
   a58e0:	83 c0 04             	add    eax,0x4
   a58e3:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a58ea:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a58f1:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a58f4:	e9 e9 fb ff ff       	jmp    a54e2 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x372>
   a58f9:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5900:	83 c0 04             	add    eax,0x4
   a5903:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a590a:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a590d:	31 c0                	xor    eax,eax
   a590f:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5916:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a591a:	e9 8a fb ff ff       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a591f:	90                   	nop
   a5920:	83 c0 04             	add    eax,0x4
   a5923:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a592a:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a592d:	31 c0                	xor    eax,eax
   a592f:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5936:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a593a:	e9 46 fa ff ff       	jmp    a5385 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x215>
   a593f:	90                   	nop
   a5940:	83 c2 04             	add    edx,0x4
   a5943:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a594a:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5951:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a5954:	e9 43 f9 ff ff       	jmp    a529c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x12c>
   a5959:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5960:	83 c2 04             	add    edx,0x4
   a5963:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a596a:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5971:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a5974:	e9 d6 fa ff ff       	jmp    a544f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2df>
   a5979:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a5980:	8d 4a 04             	lea    ecx,[edx+0x4]
   a5983:	89 4b 18             	mov    DWORD PTR [ebx+0x18],ecx
   a5986:	8b 12                	mov    edx,DWORD PTR [edx]
   a5988:	89 53 10             	mov    DWORD PTR [ebx+0x10],edx
   a598b:	e9 5c f9 ff ff       	jmp    a52ec <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x17c>
   a5990:	83 c0 04             	add    eax,0x4
   a5993:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a599a:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a599d:	31 c0                	xor    eax,eax
   a599f:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a59a6:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a59aa:	e9 a0 fa ff ff       	jmp    a544f <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x2df>
   a59af:	90                   	nop
   a59b0:	83 c2 04             	add    edx,0x4
   a59b3:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a59ba:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a59c1:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a59c4:	e9 93 f8 ff ff       	jmp    a525c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0xec>
   a59c9:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a59d0:	83 c2 04             	add    edx,0x4
   a59d3:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a59da:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a59e1:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a59e4:	e9 93 fa ff ff       	jmp    a547c <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x30c>
   a59e9:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   a59f0:	83 c0 04             	add    eax,0x4
   a59f3:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a59fa:	89 43 18             	mov    DWORD PTR [ebx+0x18],eax
   a59fd:	31 c0                	xor    eax,eax
   a59ff:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5a06:	c6 43 04 01          	mov    BYTE PTR [ebx+0x4],0x1
   a5a0a:	e9 dd f8 ff ff       	jmp    a52ec <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x17c>
   a5a0f:	90                   	nop
   a5a10:	83 c2 04             	add    edx,0x4
   a5a13:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a5a1a:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5a21:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a5a24:	e9 80 fa ff ff       	jmp    a54a9 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x339>
   a5a29:	83 c2 04             	add    edx,0x4
   a5a2c:	c7 43 14 01 00 00 00 	mov    DWORD PTR [ebx+0x14],0x1
   a5a33:	c7 43 10 00 00 00 00 	mov    DWORD PTR [ebx+0x10],0x0
   a5a3a:	89 53 18             	mov    DWORD PTR [ebx+0x18],edx
   a5a3d:	e9 aa f8 ff ff       	jmp    a52ec <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x17c>
   a5a42:	89 c3                	mov    ebx,eax
   a5a44:	8d 45 dc             	lea    eax,[ebp-0x24]
   a5a47:	89 04 24             	mov    DWORD PTR [esp],eax
   a5a4a:	e8 a1 45 00 00       	call   a9ff0 <Tm_Zone::~Tm_Zone()>
   a5a4f:	89 1c 24             	mov    DWORD PTR [esp],ebx
   a5a52:	e8 49 82 1e 00       	call   28dca0 <_Unwind_Resume>
   a5a57:	c7 04 24 00 00 00 00 	mov    DWORD PTR [esp],0x0
   a5a5e:	89 c3                	mov    ebx,eax
   a5a60:	e8 cb 45 00 00       	call   aa030 <CVProfile::ExitScope()>
   a5a65:	eb dd                	jmp    a5a44 <SVC_PacketEntities::ReadFromBuffer(bf_read&)+0x8d4>
