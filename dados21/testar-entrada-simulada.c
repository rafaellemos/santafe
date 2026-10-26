/* Fronteiras/adversários da leitura UTF16; não substitui console Windows real. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef void *HANDLE;
typedef uint32_t DWORD;
typedef uint16_t WCHAR;
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define ERROR_OPERATION_ABORTED 995
#define ENABLE_LINE_INPUT 2
#define LUA_USE_WINDOWS
#define LUALIB_API
#define SF_WININPUT_IMPLEMENTATION
#define SF_WININPUT_TEST
#define _get_osfhandle mock_osfhandle
#define _fileno mock_fileno
#define _lock_file mock_lock
#define _unlock_file mock_unlock
static WCHAR input[20000];
static size_t input_size, input_pos, chunk;
static int calls, fail_call, lock_depth, consoles, handle_id = 42, line_mode = 2;
static DWORD api_error, last_error;
static int true_cancelled, invalid_count;
static intptr_t _get_osfhandle(int fd) { (void)fd; return handle_id; }
static int _fileno(FILE *f) { (void)f; return 0; }
static void _lock_file(FILE *f) { (void)f; lock_depth++; }
static void _unlock_file(FILE *f) { (void)f; assert(lock_depth>0); lock_depth--; }
static int GetConsoleMode(HANDLE h, DWORD *mode) {
  (void)h; *mode=line_mode; return consoles;
}
static DWORD GetLastError(void) { return last_error; }
static void SetLastError(DWORD error) { last_error=error; }
static int ReadConsoleW(HANDLE h, void *b, DWORD max, DWORD *n, void *ctl) {
  size_t count = input_size-input_pos;
  (void)h; (void)ctl; calls++;
  assert(lock_depth>0);
  if(calls==fail_call) { last_error=api_error; return 0; }
  if(true_cancelled) { last_error=ERROR_OPERATION_ABORTED; *n=(DWORD)-1; return 1; }
  if(invalid_count) { *n=20000; return 1; }
  if(count>chunk) count=chunk;
  if(count>max) count=max;
  memcpy(b,input+input_pos,count*sizeof(WCHAR)); input_pos+=count; *n=(DWORD)count;
  return 1;
}
#include "overlay/src/lwininput.h"

static void prepare(const WCHAR *s,size_t n,size_t max) {
  assert(lock_depth==0);
  memset(&sf_input_console,0,sizeof(sf_input_console));
  memcpy(input,s,n*sizeof(WCHAR)); input_size=n; input_pos=0; chunk=max;
  calls=fail_call=true_cancelled=invalid_count=0; consoles=1; api_error=5; errno=0;
}
static void bytes(const WCHAR *s,size_t n,size_t max,const char *expected,size_t len) {
  char b[15000]; size_t got;
  prepare(s,n,max); got=sf_input_read(b,sizeof(b),stdin);
  if(got!=len || memcmp(b,expected,len)) {
    fprintf(stderr,"unidades=%zu bloco=%zu obtidos=%zu esperados=%zu\n",n,max,got,len);
    for(size_t j=0;j<got;j++) fprintf(stderr,"%02x ",(unsigned char)b[j]);
    fputc('\n',stderr);
  }
  assert(got==len && memcmp(b,expected,len)==0);
  assert(sf_input_eof(stdin) && !sf_input_error(stdin));
  assert(sf_input_getc(stdin)==EOF && lock_depth==0);
}
int main(void) {
  const WCHAR sample[]={0xe3,' ','c','a','f','e',0x301,' ',0xd83d,0xdfe2,'\r','\n'};
  const char expected[]="\xc3\xa3 cafe\xcc\x81 \xf0\x9f\x9f\xa2\n";
  const WCHAR lonehi[]={0xd800}, lonelo[]={0xdc00}, invalidpair[]={0xd800,'a'};
  const WCHAR cr[]={'a','\r','\n','b','\r','c','\n'}, nul[]={'a',0,'b'};
  const WCHAR eof[]={'a',26,'\r','\n'}, accent[]={0xe3,'\n'};
  const WCHAR number[]={'4','2',0xe3,'\n'};
  char b[64]; size_t n,i;
  for(i=1;i<=12;i++) bytes(sample,12,i,expected,sizeof(expected)-1);
  bytes(cr,7,1,"a\nb\nc\n",6);
  bytes(nul,3,1,"a\0b",3);
  bytes(eof,4,256,"a",1);
  prepare(accent,2,1);
  assert(sf_input_getc(stdin)==0xc3);
  assert(sf_input_ungetc(0xc3,stdin)==0xc3);
  assert(sf_input_ungetc('x',stdin)==EOF);
  assert(sf_input_getc(stdin)==0xc3 && sf_input_getc(stdin)==0xa3);
  assert(sf_input_getc(stdin)=='\n' && sf_input_getc(stdin)==EOF);
  assert(sf_input_ungetc(EOF,stdin)==EOF && sf_input_eof(stdin));
  assert(sf_input_ungetc('z',stdin)=='z' && !sf_input_eof(stdin));
  assert(sf_input_getc(stdin)=='z');
  prepare(accent,2,1);
  assert(sf_input_read(b,1,stdin)==1 && (unsigned char)b[0]==0xc3);
  assert(sf_input_read(b,1,stdin)==1 && (unsigned char)b[0]==0xa3);
  assert(sf_input_read(b,0,stdin)==0 && calls==1);
  prepare(number,4,256);
  assert(sf_input_getc(stdin)=='4' && sf_input_getc(stdin)=='2');
  assert(sf_input_ungetc(sf_input_getc(stdin),stdin)==0xc3);
  assert(sf_input_read(b,3,stdin)==3 && !memcmp(b,"\xc3\xa3\n",3));
  prepare(lonehi,1,1); assert(sf_input_getc(stdin)==EOF);
  assert(sf_input_error(stdin)==EILSEQ && errno==EILSEQ);
  prepare(lonelo,1,1); assert(sf_input_getc(stdin)==EOF);
  assert(sf_input_error(stdin)==EILSEQ);
  prepare(invalidpair,2,1); assert(sf_input_getc(stdin)==EOF);
  assert(sf_input_error(stdin)==EILSEQ);
  prepare(accent,2,1); fail_call=1; api_error=ERROR_OPERATION_ABORTED;
  assert(sf_input_getc(stdin)==EOF && sf_input_error(stdin)==EINTR && !sf_input_eof(stdin));
  sf_input_clear(stdin); assert(!sf_input_error(stdin));
  assert(sf_input_getc(stdin)==0xc3 && sf_input_getc(stdin)==0xa3);
  prepare(accent,2,1); fail_call=1;
  assert(sf_input_read(b,sizeof(b),stdin)==0 && sf_input_error(stdin)==EIO);
  prepare(accent,2,1); true_cancelled=1;
  assert(sf_input_getc(stdin)==EOF && sf_input_error(stdin)==EINTR && !sf_input_eof(stdin));
  prepare(accent,2,1); invalid_count=1;
  assert(sf_input_getc(stdin)==EOF && sf_input_error(stdin)==EIO);
  prepare(sample,12,256); fail_call=2;
  n=sf_input_read(b,sizeof(b),stdin);
  assert(n==sizeof(expected)-1 && !memcmp(b,expected,n) && sf_input_error(stdin)==EIO);
  prepare(accent,0,1); assert(sf_input_getc(stdin)==EOF && sf_input_eof(stdin));
  sf_input_clear(stdin); input_size=2;
  assert(sf_input_getc(stdin)==0xc3);
  handle_id++; input_pos=0;
  assert(sf_input_getc(stdin)==0xc3); /* handle novo não herda byte UTF8 pendente */
  {
    WCHAR long_input[4099]; char long_expected[4105];
    for(i=0;i<4095;i++) long_input[i]=long_expected[i]='x';
    long_input[4095]=0xd83d;long_input[4096]=0xdfe2;
    long_input[4097]='\r';long_input[4098]='\n';
    memcpy(long_expected+4095,"\xf0\x9f\x9f\xa2\n",5);
    bytes(long_input,4099,256,long_expected,4100);
  }
  {
    WCHAR long_input[16384];
    for(i=0;i<16384;i++)long_input[i]='x';
    prepare(long_input,16384,16384);
    assert(sf_input_getc(stdin)==EOF && sf_input_error(stdin)==EOVERFLOW);
    prepare(long_input,16384,16384); line_mode=0;
    assert(sf_input_getc(stdin)=='x' && !sf_input_error(stdin)); line_mode=2;
  }
  {
    FILE *f=tmpfile(); assert(f);
    assert(fwrite("\xc3\xa3\0\r\n",1,5,f)==5); rewind(f);
    assert(!sf_input_is_console(f));
    assert(sf_input_read(b,sizeof(b),f)==5 && !memcmp(b,"\xc3\xa3\0\r\n",5));
    assert(sf_input_eof(f)); sf_input_clear(f); assert(!sf_input_eof(f));
    assert(sf_input_ungetc('z',f)=='z' && sf_input_getc(f)=='z'); fclose(f);
  }
  assert(lock_depth==0);
  puts("ENTRADA_SIMULADA_OK fronteirasUTF16/UTF8,retorno,CRLF,NUL,EOF,erros,interrupcao,handle,arquivos");
  return 0;
}
