
/home/void0312/l4d2_server/bin/engine_srv.so:     file format elf32-i386


Disassembly of section .text:

0009a300 <SVC_PacketEntities::WriteToBuffer(bf_write&)>:
   9a300:	55                   	push   ebp
   9a301:	89 e5                	mov    ebp,esp
   9a303:	57                   	push   edi
   9a304:	56                   	push   esi
   9a305:	53                   	push   ebx
   9a306:	83 ec 2c             	sub    esp,0x2c
   9a309:	8b 7d 08             	mov    edi,DWORD PTR [ebp+0x8]
   9a30c:	8b 5d 0c             	mov    ebx,DWORD PTR [ebp+0xc]
   9a30f:	8b 07                	mov    eax,DWORD PTR [edi]
   9a311:	89 3c 24             	mov    DWORD PTR [esp],edi
   9a314:	ff 50 24             	call   DWORD PTR [eax+0x24]
   9a317:	8b 73 0c             	mov    esi,DWORD PTR [ebx+0xc]
   9a31a:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
   9a31d:	8d 4e 06             	lea    ecx,[esi+0x6]
   9a320:	39 d1                	cmp    ecx,edx
   9a322:	0f 8f 58 03 00 00    	jg     9a680 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x380>
   9a328:	89 f1                	mov    ecx,esi
   9a32a:	c1 fe 05             	sar    esi,0x5
   9a32d:	c1 e6 02             	shl    esi,0x2
   9a330:	83 e1 1f             	and    ecx,0x1f
   9a333:	89 75 e0             	mov    DWORD PTR [ebp-0x20],esi
   9a336:	03 33                	add    esi,DWORD PTR [ebx]
   9a338:	89 f2                	mov    edx,esi
   9a33a:	89 ce                	mov    esi,ecx
   9a33c:	89 55 e4             	mov    DWORD PTR [ebp-0x1c],edx
   9a33f:	8b 12                	mov    edx,DWORD PTR [edx]
   9a341:	c1 e6 07             	shl    esi,0x7
   9a344:	23 94 8e b8 2d 3e 00 	and    edx,DWORD PTR [esi+ecx*4+0x3e2db8]
   9a34b:	89 c6                	mov    esi,eax
   9a34d:	d3 e6                	shl    esi,cl
   9a34f:	09 d6                	or     esi,edx
   9a351:	8b 55 e4             	mov    edx,DWORD PTR [ebp-0x1c]
   9a354:	89 32                	mov    DWORD PTR [edx],esi
   9a356:	be 20 00 00 00       	mov    esi,0x20
   9a35b:	29 ce                	sub    esi,ecx
   9a35d:	83 fe 05             	cmp    esi,0x5
   9a360:	0f 8e ea 02 00 00    	jle    9a650 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x350>
   9a366:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   9a369:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
   9a36c:	83 c0 06             	add    eax,0x6
   9a36f:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
   9a372:	8b 77 4c             	mov    esi,DWORD PTR [edi+0x4c]
   9a375:	8d 48 0b             	lea    ecx,[eax+0xb]
   9a378:	39 d1                	cmp    ecx,edx
   9a37a:	89 75 e4             	mov    DWORD PTR [ebp-0x1c],esi
   9a37d:	0f 8f dd 01 00 00    	jg     9a560 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x260>
   9a383:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a385:	89 c1                	mov    ecx,eax
   9a387:	c1 f8 05             	sar    eax,0x5
   9a38a:	c1 e0 02             	shl    eax,0x2
   9a38d:	83 e1 1f             	and    ecx,0x1f
   9a390:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
   9a393:	89 ce                	mov    esi,ecx
   9a395:	c1 e6 07             	shl    esi,0x7
   9a398:	01 c2                	add    edx,eax
   9a39a:	8b 02                	mov    eax,DWORD PTR [edx]
   9a39c:	23 84 8e cc 2d 3e 00 	and    eax,DWORD PTR [esi+ecx*4+0x3e2dcc]
   9a3a3:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a3a6:	d3 e6                	shl    esi,cl
   9a3a8:	09 f0                	or     eax,esi
   9a3aa:	89 02                	mov    DWORD PTR [edx],eax
   9a3ac:	b8 20 00 00 00       	mov    eax,0x20
   9a3b1:	29 c8                	sub    eax,ecx
   9a3b3:	83 f8 0a             	cmp    eax,0xa
   9a3b6:	0f 8e 64 02 00 00    	jle    9a620 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x320>
   9a3bc:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   9a3bf:	8d 48 0b             	lea    ecx,[eax+0xb]
   9a3c2:	3b 4b 08             	cmp    ecx,DWORD PTR [ebx+0x8]
   9a3c5:	89 4b 0c             	mov    DWORD PTR [ebx+0xc],ecx
   9a3c8:	0f b6 57 54          	movzx  edx,BYTE PTR [edi+0x54]
   9a3cc:	0f 8d 91 01 00 00    	jge    9a563 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x263>
   9a3d2:	80 7b 10 00          	cmp    BYTE PTR [ebx+0x10],0x0
   9a3d6:	75 24                	jne    9a3fc <SVC_PacketEntities::WriteToBuffer(bf_write&)+0xfc>
   9a3d8:	84 d2                	test   dl,dl
   9a3da:	8b 03                	mov    eax,DWORD PTR [ebx]
   9a3dc:	89 ca                	mov    edx,ecx
   9a3de:	0f 85 cc 02 00 00    	jne    9a6b0 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x3b0>
   9a3e4:	83 e1 07             	and    ecx,0x7
   9a3e7:	be 01 00 00 00       	mov    esi,0x1
   9a3ec:	c1 fa 03             	sar    edx,0x3
   9a3ef:	d3 e6                	shl    esi,cl
   9a3f1:	89 f1                	mov    ecx,esi
   9a3f3:	f7 d1                	not    ecx
   9a3f5:	20 0c 10             	and    BYTE PTR [eax+edx*1],cl
   9a3f8:	83 43 0c 01          	add    DWORD PTR [ebx+0xc],0x1
   9a3fc:	80 7f 54 00          	cmp    BYTE PTR [edi+0x54],0x0
   9a400:	0f 85 6b 01 00 00    	jne    9a571 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x271>
   9a406:	8b 47 58             	mov    eax,DWORD PTR [edi+0x58]
   9a409:	8b 53 0c             	mov    edx,DWORD PTR [ebx+0xc]
   9a40c:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
   9a40f:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
   9a412:	39 c2                	cmp    edx,eax
   9a414:	0f 8d 7a 01 00 00    	jge    9a594 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x294>
   9a41a:	8b 03                	mov    eax,DWORD PTR [ebx]
   9a41c:	89 d1                	mov    ecx,edx
   9a41e:	c1 fa 05             	sar    edx,0x5
   9a421:	83 e1 1f             	and    ecx,0x1f
   9a424:	8d 14 90             	lea    edx,[eax+edx*4]
   9a427:	89 c8                	mov    eax,ecx
   9a429:	c1 e0 07             	shl    eax,0x7
   9a42c:	89 c6                	mov    esi,eax
   9a42e:	8b 02                	mov    eax,DWORD PTR [edx]
   9a430:	23 84 8e a4 2d 3e 00 	and    eax,DWORD PTR [esi+ecx*4+0x3e2da4]
   9a437:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a43a:	d3 e6                	shl    esi,cl
   9a43c:	09 f0                	or     eax,esi
   9a43e:	89 02                	mov    DWORD PTR [edx],eax
   9a440:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   9a443:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
   9a446:	83 c0 01             	add    eax,0x1
   9a449:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
   9a44c:	8d 48 0b             	lea    ecx,[eax+0xb]
   9a44f:	8b 77 50             	mov    esi,DWORD PTR [edi+0x50]
   9a452:	39 d1                	cmp    ecx,edx
   9a454:	89 75 e4             	mov    DWORD PTR [ebp-0x1c],esi
   9a457:	0f 8f 51 01 00 00    	jg     9a5ae <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x2ae>
   9a45d:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a45f:	89 c1                	mov    ecx,eax
   9a461:	c1 f8 05             	sar    eax,0x5
   9a464:	c1 e0 02             	shl    eax,0x2
   9a467:	83 e1 1f             	and    ecx,0x1f
   9a46a:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
   9a46d:	89 ce                	mov    esi,ecx
   9a46f:	c1 e6 07             	shl    esi,0x7
   9a472:	01 c2                	add    edx,eax
   9a474:	8b 02                	mov    eax,DWORD PTR [edx]
   9a476:	23 84 8e cc 2d 3e 00 	and    eax,DWORD PTR [esi+ecx*4+0x3e2dcc]
   9a47d:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a480:	d3 e6                	shl    esi,cl
   9a482:	09 f0                	or     eax,esi
   9a484:	89 02                	mov    DWORD PTR [edx],eax
   9a486:	b8 20 00 00 00       	mov    eax,0x20
   9a48b:	29 c8                	sub    eax,ecx
   9a48d:	83 f8 0a             	cmp    eax,0xa
   9a490:	0f 8e 2a 01 00 00    	jle    9a5c0 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x2c0>
   9a496:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   9a499:	8b 53 08             	mov    edx,DWORD PTR [ebx+0x8]
   9a49c:	83 c0 0b             	add    eax,0xb
   9a49f:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
   9a4a2:	8b 77 60             	mov    esi,DWORD PTR [edi+0x60]
   9a4a5:	8d 48 14             	lea    ecx,[eax+0x14]
   9a4a8:	39 d1                	cmp    ecx,edx
   9a4aa:	89 75 e4             	mov    DWORD PTR [ebp-0x1c],esi
   9a4ad:	0f 8f 9d 00 00 00    	jg     9a550 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x250>
   9a4b3:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a4b5:	89 c1                	mov    ecx,eax
   9a4b7:	c1 f8 05             	sar    eax,0x5
   9a4ba:	c1 e0 02             	shl    eax,0x2
   9a4bd:	83 e1 1f             	and    ecx,0x1f
   9a4c0:	89 45 e0             	mov    DWORD PTR [ebp-0x20],eax
   9a4c3:	89 ce                	mov    esi,ecx
   9a4c5:	c1 e6 07             	shl    esi,0x7
   9a4c8:	01 c2                	add    edx,eax
   9a4ca:	8b 02                	mov    eax,DWORD PTR [edx]
   9a4cc:	23 84 8e f0 2d 3e 00 	and    eax,DWORD PTR [esi+ecx*4+0x3e2df0]
   9a4d3:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a4d6:	d3 e6                	shl    esi,cl
   9a4d8:	09 f0                	or     eax,esi
   9a4da:	89 02                	mov    DWORD PTR [edx],eax
   9a4dc:	b8 20 00 00 00       	mov    eax,0x20
   9a4e1:	29 c8                	sub    eax,ecx
   9a4e3:	83 f8 13             	cmp    eax,0x13
   9a4e6:	0f 8e 04 01 00 00    	jle    9a5f0 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x2f0>
   9a4ec:	8b 43 0c             	mov    eax,DWORD PTR [ebx+0xc]
   9a4ef:	8d 48 14             	lea    ecx,[eax+0x14]
   9a4f2:	3b 4b 08             	cmp    ecx,DWORD PTR [ebx+0x8]
   9a4f5:	89 4b 0c             	mov    DWORD PTR [ebx+0xc],ecx
   9a4f8:	0f b6 57 55          	movzx  edx,BYTE PTR [edi+0x55]
   9a4fc:	7d 55                	jge    9a553 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x253>
   9a4fe:	80 7b 10 00          	cmp    BYTE PTR [ebx+0x10],0x0
   9a502:	75 24                	jne    9a528 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x228>
   9a504:	84 d2                	test   dl,dl
   9a506:	8b 03                	mov    eax,DWORD PTR [ebx]
   9a508:	89 ca                	mov    edx,ecx
   9a50a:	0f 85 80 01 00 00    	jne    9a690 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x390>
   9a510:	83 e1 07             	and    ecx,0x7
   9a513:	be 01 00 00 00       	mov    esi,0x1
   9a518:	c1 fa 03             	sar    edx,0x3
   9a51b:	d3 e6                	shl    esi,cl
   9a51d:	89 f1                	mov    ecx,esi
   9a51f:	f7 d1                	not    ecx
   9a521:	20 0c 10             	and    BYTE PTR [eax+edx*1],cl
   9a524:	83 43 0c 01          	add    DWORD PTR [ebx+0xc],0x1
   9a528:	8b 47 60             	mov    eax,DWORD PTR [edi+0x60]
   9a52b:	89 44 24 08          	mov    DWORD PTR [esp+0x8],eax
   9a52f:	8b 87 88 00 00 00    	mov    eax,DWORD PTR [edi+0x88]
   9a535:	89 1c 24             	mov    DWORD PTR [esp],ebx
   9a538:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
   9a53c:	e8 df 6d 19 00       	call   231320 <bf_write::WriteBits(void const*, int)>
   9a541:	0f b6 43 10          	movzx  eax,BYTE PTR [ebx+0x10]
   9a545:	83 c4 2c             	add    esp,0x2c
   9a548:	5b                   	pop    ebx
   9a549:	83 f0 01             	xor    eax,0x1
   9a54c:	5e                   	pop    esi
   9a54d:	5f                   	pop    edi
   9a54e:	5d                   	pop    ebp
   9a54f:	c3                   	ret
   9a550:	89 53 0c             	mov    DWORD PTR [ebx+0xc],edx
   9a553:	c6 43 10 01          	mov    BYTE PTR [ebx+0x10],0x1
   9a557:	eb cf                	jmp    9a528 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x228>
   9a559:	8d b4 26 00 00 00 00 	lea    esi,[esi+eiz*1+0x0]
   9a560:	89 53 0c             	mov    DWORD PTR [ebx+0xc],edx
   9a563:	c6 43 10 01          	mov    BYTE PTR [ebx+0x10],0x1
   9a567:	80 7f 54 00          	cmp    BYTE PTR [edi+0x54],0x0
   9a56b:	0f 84 95 fe ff ff    	je     9a406 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x106>
   9a571:	8b 47 5c             	mov    eax,DWORD PTR [edi+0x5c]
   9a574:	89 1c 24             	mov    DWORD PTR [esp],ebx
   9a577:	89 44 24 04          	mov    DWORD PTR [esp+0x4],eax
   9a57b:	e8 20 84 19 00       	call   2329a0 <bf_write::WriteLong(long)>
   9a580:	8b 47 58             	mov    eax,DWORD PTR [edi+0x58]
   9a583:	8b 53 0c             	mov    edx,DWORD PTR [ebx+0xc]
   9a586:	89 45 e4             	mov    DWORD PTR [ebp-0x1c],eax
   9a589:	8b 43 08             	mov    eax,DWORD PTR [ebx+0x8]
   9a58c:	39 c2                	cmp    edx,eax
   9a58e:	0f 8c 86 fe ff ff    	jl     9a41a <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x11a>
   9a594:	89 43 0c             	mov    DWORD PTR [ebx+0xc],eax
   9a597:	8d 48 0b             	lea    ecx,[eax+0xb]
   9a59a:	89 c2                	mov    edx,eax
   9a59c:	c6 43 10 01          	mov    BYTE PTR [ebx+0x10],0x1
   9a5a0:	39 d1                	cmp    ecx,edx
   9a5a2:	8b 77 50             	mov    esi,DWORD PTR [edi+0x50]
   9a5a5:	89 75 e4             	mov    DWORD PTR [ebp-0x1c],esi
   9a5a8:	0f 8e af fe ff ff    	jle    9a45d <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x15d>
   9a5ae:	89 53 0c             	mov    DWORD PTR [ebx+0xc],edx
   9a5b1:	89 d0                	mov    eax,edx
   9a5b3:	c6 43 10 01          	mov    BYTE PTR [ebx+0x10],0x1
   9a5b7:	e9 e6 fe ff ff       	jmp    9a4a2 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x1a2>
   9a5bc:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   9a5c0:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a5c2:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
   9a5c5:	8d 74 0a 04          	lea    esi,[edx+ecx*1+0x4]
   9a5c9:	ba 0b 00 00 00       	mov    edx,0xb
   9a5ce:	89 c1                	mov    ecx,eax
   9a5d0:	29 c2                	sub    edx,eax
   9a5d2:	89 75 e0             	mov    DWORD PTR [ebp-0x20],esi
   9a5d5:	8b 14 95 a0 2d 3e 00 	mov    edx,DWORD PTR [edx*4+0x3e2da0]
   9a5dc:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
   9a5df:	23 16                	and    edx,DWORD PTR [esi]
   9a5e1:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a5e4:	d3 ee                	shr    esi,cl
   9a5e6:	09 f2                	or     edx,esi
   9a5e8:	89 10                	mov    DWORD PTR [eax],edx
   9a5ea:	e9 a7 fe ff ff       	jmp    9a496 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x196>
   9a5ef:	90                   	nop
   9a5f0:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a5f2:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
   9a5f5:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a5f8:	8d 4c 0a 04          	lea    ecx,[edx+ecx*1+0x4]
   9a5fc:	ba 14 00 00 00       	mov    edx,0x14
   9a601:	29 c2                	sub    edx,eax
   9a603:	89 4d e0             	mov    DWORD PTR [ebp-0x20],ecx
   9a606:	8b 14 95 a0 2d 3e 00 	mov    edx,DWORD PTR [edx*4+0x3e2da0]
   9a60d:	23 11                	and    edx,DWORD PTR [ecx]
   9a60f:	89 c1                	mov    ecx,eax
   9a611:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
   9a614:	d3 ee                	shr    esi,cl
   9a616:	09 f2                	or     edx,esi
   9a618:	89 10                	mov    DWORD PTR [eax],edx
   9a61a:	e9 cd fe ff ff       	jmp    9a4ec <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x1ec>
   9a61f:	90                   	nop
   9a620:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a622:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
   9a625:	8b 75 e4             	mov    esi,DWORD PTR [ebp-0x1c]
   9a628:	8d 4c 0a 04          	lea    ecx,[edx+ecx*1+0x4]
   9a62c:	ba 0b 00 00 00       	mov    edx,0xb
   9a631:	29 c2                	sub    edx,eax
   9a633:	89 4d e0             	mov    DWORD PTR [ebp-0x20],ecx
   9a636:	8b 14 95 a0 2d 3e 00 	mov    edx,DWORD PTR [edx*4+0x3e2da0]
   9a63d:	23 11                	and    edx,DWORD PTR [ecx]
   9a63f:	89 c1                	mov    ecx,eax
   9a641:	8b 45 e0             	mov    eax,DWORD PTR [ebp-0x20]
   9a644:	d3 ee                	shr    esi,cl
   9a646:	09 f2                	or     edx,esi
   9a648:	89 10                	mov    DWORD PTR [eax],edx
   9a64a:	e9 6d fd ff ff       	jmp    9a3bc <SVC_PacketEntities::WriteToBuffer(bf_write&)+0xbc>
   9a64f:	90                   	nop
   9a650:	8b 13                	mov    edx,DWORD PTR [ebx]
   9a652:	8b 4d e0             	mov    ecx,DWORD PTR [ebp-0x20]
   9a655:	8d 4c 0a 04          	lea    ecx,[edx+ecx*1+0x4]
   9a659:	ba 06 00 00 00       	mov    edx,0x6
   9a65e:	29 f2                	sub    edx,esi
   9a660:	89 4d e4             	mov    DWORD PTR [ebp-0x1c],ecx
   9a663:	8b 14 95 a0 2d 3e 00 	mov    edx,DWORD PTR [edx*4+0x3e2da0]
   9a66a:	23 11                	and    edx,DWORD PTR [ecx]
   9a66c:	89 f1                	mov    ecx,esi
   9a66e:	d3 e8                	shr    eax,cl
   9a670:	8b 4d e4             	mov    ecx,DWORD PTR [ebp-0x1c]
   9a673:	09 d0                	or     eax,edx
   9a675:	89 01                	mov    DWORD PTR [ecx],eax
   9a677:	e9 ea fc ff ff       	jmp    9a366 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x66>
   9a67c:	8d 74 26 00          	lea    esi,[esi+eiz*1+0x0]
   9a680:	89 53 0c             	mov    DWORD PTR [ebx+0xc],edx
   9a683:	89 d0                	mov    eax,edx
   9a685:	c6 43 10 01          	mov    BYTE PTR [ebx+0x10],0x1
   9a689:	e9 e4 fc ff ff       	jmp    9a372 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x72>
   9a68e:	66 90                	xchg   ax,ax
   9a690:	83 e1 07             	and    ecx,0x7
   9a693:	be 01 00 00 00       	mov    esi,0x1
   9a698:	c1 fa 03             	sar    edx,0x3
   9a69b:	d3 e6                	shl    esi,cl
   9a69d:	89 f1                	mov    ecx,esi
   9a69f:	08 0c 10             	or     BYTE PTR [eax+edx*1],cl
   9a6a2:	e9 7d fe ff ff       	jmp    9a524 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0x224>
   9a6a7:	89 f6                	mov    esi,esi
   9a6a9:	8d bc 27 00 00 00 00 	lea    edi,[edi+eiz*1+0x0]
   9a6b0:	83 e1 07             	and    ecx,0x7
   9a6b3:	be 01 00 00 00       	mov    esi,0x1
   9a6b8:	c1 fa 03             	sar    edx,0x3
   9a6bb:	d3 e6                	shl    esi,cl
   9a6bd:	89 f1                	mov    ecx,esi
   9a6bf:	08 0c 10             	or     BYTE PTR [eax+edx*1],cl
   9a6c2:	e9 31 fd ff ff       	jmp    9a3f8 <SVC_PacketEntities::WriteToBuffer(bf_write&)+0xf8>
